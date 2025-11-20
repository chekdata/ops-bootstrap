#!/usr/bin/env python3
import os, hmac, hashlib, urllib.parse, json, subprocess, sys
from datetime import datetime

def h(key,msg):
    if isinstance(msg,str): msg=msg.encode()
    return hmac.new(key,msg,hashlib.sha256).digest()

def sign_url(ak, sk, region, service, endpoint, action, version, params):
    """
    完全按卷上 Query 样例实现的预签名 URL：
    - 使用 X-Algorithm/X-Credential/X-Date/X-Expires/X-NotSignBody/X-SignedHeaders/X-SignedQueries
    - 可选携带 X-Security-Token
    - 不使用 Authorization 头与 X-Date 头，只签名 Query
    """
    t = datetime.utcnow()
    amz = t.strftime('%Y%m%dT%H%M%SZ')
    dat = t.strftime('%Y%m%d')

    security_token = os.environ.get('SECURITY_TOKEN') or os.environ.get('X_SECURITY_TOKEN') or os.environ.get('VOLC_SECURITY_TOKEN')

    algorithm = 'HMAC-SHA256'
    scope = '{}/{}/{}/request'.format(dat, region, service)
    credential = '{}/{}'.format(ak, scope)

    base = {
        'Action': action,
        'Version': version,
        'X-Algorithm': algorithm,
        'X-Credential': credential,
        'X-Date': amz,
        'X-Expires': '3600',
        'X-NotSignBody': '1',
    }
    if security_token:
        base['X-Security-Token'] = security_token

    signed_order = ['Action', 'Version', 'X-Algorithm', 'X-Credential', 'X-Date', 'X-Expires', 'X-NotSignBody']
    if security_token:
        signed_order.append('X-Security-Token')
    signed_order.extend(['X-SignedHeaders', 'X-SignedQueries'])

    base['X-SignedHeaders'] = ''
    base['X-SignedQueries'] = ';'.join(signed_order)

    # canonical_qs：仅包含被签名字段，顺序严格按照 X-SignedQueries
    canonical_items = []
    for k in signed_order:
        v = base.get(k, '')
        canonical_items.append(
            '{}={}'.format(urllib.parse.quote_plus(k), urllib.parse.quote_plus(str(v)))
        )
    canonical_qs = '&'.join(canonical_items)

    canonical = '\n'.join([
        'GET',
        '/',
        canonical_qs,
        '',
        '',
        hashlib.sha256(b'').hexdigest(),
    ])
    sts = '\n'.join([
        algorithm,
        amz,
        scope,
        hashlib.sha256(canonical.encode()).hexdigest(),
    ])
    kDate = h(('VOLC' + sk).encode(), dat)
    kRegion = h(kDate, region)
    kService = h(kRegion, service)
    kSign = h(kService, 'request')
    sig = hmac.new(kSign, sts.encode(), hashlib.sha256).hexdigest()

    all_params = {}
    all_params.update(params or {})
    all_params.update(base)
    all_params['X-Signature'] = sig

    qs = '&'.join(
        '{}={}'.format(urllib.parse.quote_plus(k), urllib.parse.quote_plus(str(v)))
        for k, v in sorted(all_params.items())
    )
    return 'https://{}/?{}'.format(endpoint, qs)

def curl_json(url):
    if isinstance(url, tuple):
        url, headers = url
    else:
        headers = {}
    cmd = ['curl', '-sS', url]
    for k, v in headers.items():
        cmd.extend(['-H', f'{k}: {v}'])
    out=subprocess.check_output(cmd)
    try: return json.loads(out.decode())
    except: return {}

def extract_listeners(doc):
    for path in (('Result','Listeners'),('Listeners',),('ListenerSet',)):
        cur=doc; ok=True
        for k in path:
            if isinstance(cur,dict) and k in cur: cur=cur[k]
            else: ok=False; break
        if ok and isinstance(cur,list): return cur
    return []

def find_rules_anywhere(d, acc=None):
    if acc is None: acc=[]
    if isinstance(d,dict):
        for k,v in d.items():
            if k in ('Rules','RuleSet') and isinstance(v,list): acc.extend(v)
            else: find_rules_anywhere(v,acc)
    elif isinstance(d,list):
        for it in d: find_rules_anywhere(it,acc)
    return acc

def pick(vals):
    for v in vals:
        if v: return v
    return ''

def main():
    ak=os.environ.get('AK') or os.environ.get('VOLC_AK')
    sk=os.environ.get('SK') or os.environ.get('VOLC_SK')
    region=os.environ.get('REGION','cn-beijing')
    alb_id=os.environ.get('ALB_ID')
    host=os.environ.get('HOST','api.chekkk.com')
    endpoint=f'alb.{region}.volcengineapi.com'
    service='alb'
    list_alb = os.environ.get('LIST_ALB') == '1'
    if not (ak and sk) or (not list_alb and not alb_id):
        print('missing AK/SK/ALB_ID', file=sys.stderr); return 2

    # 模式一：仅列出当前账号下的 ALB（用于根据名称查 ID）
    if list_alb:
        doc = {}
        for ver in ('2020-04-01','2020-11-26','2023-01-01'):
            doc = curl_json(sign_url(ak,sk,region,service,endpoint,'DescribeLoadBalancers',ver,{}))
            if doc:
                break
        print(json.dumps(doc, ensure_ascii=False))
        return 0

    # 1) list listeners
    ls=[]
    for ver in ('2020-04-01','2020-11-26','2023-01-01'):
        d=curl_json(sign_url(ak,sk,region,service,endpoint,'DescribeListeners',ver,{'LoadBalancerId':alb_id}))
        ls=extract_listeners(d)
        if ls: break

    # 只读模式：导出所有监听器及其规则（不做删除）
    dump_only = os.environ.get('DUMP_ONLY') == '1'
    if dump_only:
        rules_by_listener = {}
        for l in ls:
            lid = l.get('ListenerId') or l.get('Id')
            if not lid:
                continue
            rlist = []
            for ver in ('2020-04-01','2020-11-26','2023-01-01'):
                rlist = find_rules_anywhere(curl_json(sign_url(ak,sk,region,service,endpoint,'DescribeRules',ver,{'ListenerId':lid})))
                if rlist:
                    break
            rules_by_listener[lid] = rlist
        print(json.dumps({'listeners': ls, 'rulesByListener': rules_by_listener}, ensure_ascii=False))
        return 0

    # 2) find HTTP:80 listener（删除模式仍然只动 HTTP:80）
    http80=None
    for l in ls:
        proto=str(l.get('Protocol','')).upper(); port=int(l.get('Port') or 0)
        if proto=='HTTP' and port==80: http80=l; break
    if not http80:
        print('no HTTP:80 listener, done'); return 0
    lid=http80.get('ListenerId') or http80.get('Id')
    if not lid:
        print('no ListenerId', file=sys.stderr); return 3

    # 3) list rules
    rules=[]
    for ver in ('2020-04-01','2020-11-26','2023-01-01'):
        rules=find_rules_anywhere(curl_json(sign_url(ak,sk,region,service,endpoint,'DescribeRules',ver,{'ListenerId':lid})))
        if rules: break

    # 4) pick business rules to delete
    del_ids=[]
    for r in rules:
        rid=pick([r.get('RuleId'), r.get('Id')])
        if not rid: continue
        domain=pick([r.get('Domain'), r.get('Host'), r.get('HostHeader')])
        path=pick([r.get('Path'), r.get('Url'), r.get('PathPattern')]) or '/'
        conds=r.get('RuleConditions') or []
        if not domain:
            for c in conds:
                fld=str(c.get('Field','')).lower()
                if fld in ('host','host-header','hostheader'):
                    vals=(c.get('HostHeaderConfig') or {}).get('Values') or []
                    if vals: domain=vals[0]; break
        if not path:
            for c in conds:
                fld=str(c.get('Field','')).lower()
                if fld in ('path','path-pattern'):
                    cfg=c.get('PathConfig') or c.get('PathPatternConfig') or {}
                    vals=cfg.get('Values') or []
                    if vals: path=vals[0]; break
        if domain==host and (path=='/' or path.startswith('/api/') or path in ('/openapi','/openapi.json') or path.startswith('/osm-gateway')):
            del_ids.append(rid)

    if not del_ids:
        print('no rules to delete'); return 0

    # 4) delete rules
    params={'ListenerId':lid}
    for i, rid in enumerate(del_ids, start=1):
        params[f'RuleIds.{i}']=rid
    url=sign_url(ak,sk,region,service,endpoint,'DeleteRules','2020-04-01',params)
    out=curl_json(url)
    print(json.dumps({'deleted':del_ids, 'resp':out.get('Result') or out}, ensure_ascii=False))
    return 0

if __name__=='__main__':
    sys.exit(main())



