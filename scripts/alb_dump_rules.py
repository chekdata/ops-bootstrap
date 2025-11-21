#!/usr/bin/env python3
import os, hmac, hashlib, urllib.parse, subprocess, json
from datetime import datetime
from pathlib import Path


def h(key, msg):
    if isinstance(msg, str):
        msg = msg.encode()
    return hmac.new(key, msg, hashlib.sha256).digest()


def sign_url(ak, sk, region, service, endpoint, action, version, params):
    t = datetime.utcnow()
    amz = t.strftime("%Y%m%dT%H%M%SZ")
    dat = t.strftime("%Y%m%d")
    query = {"Action": action, "Version": version, "Region": region}
    query.update(params or {})
    qs = "&".join(
        [
            "{}={}".format(
                urllib.parse.quote_plus(k), urllib.parse.quote_plus(str(v))
            )
            for k, v in sorted(query.items())
        ]
    )
    ch = "host:{}\n".format(endpoint) + "x-volc-date:{}\n".format(amz)
    canonical = "\n".join(
        ["GET", "/", qs, ch, "host;x-volc-date", hashlib.sha256(b"").hexdigest()]
    )
    scope = "{}/{}/{}/request".format(dat, region, service)
    sts = "\n".join(
        [
            "HMAC-SHA256",
            amz,
            scope,
            hashlib.sha256(canonical.encode()).hexdigest(),
        ]
    )
    kDate = h(("VOLC" + sk).encode(), dat)
    kRegion = h(kDate, region)
    kService = h(kRegion, service)
    kSign = h(kService, "request")
    sig = hmac.new(kSign, sts.encode(), hashlib.sha256).hexdigest()
    auth = "HMAC-SHA256 Credential={}/{}, SignedHeaders=host;x-volc-date, Signature={}".format(
        ak, scope, sig
    )
    return "https://{}/?{}&X-Volc-Date={}&Authorization={}".format(
        endpoint, qs, urllib.parse.quote_plus(amz), urllib.parse.quote_plus(auth)
    )


def curl_json(url):
    out = subprocess.check_output(["curl", "-sS", url])
    try:
        return json.loads(out.decode())
    except Exception:
        return {}


def extract_listeners(doc):
    for path in (("Result", "Listeners"), ("Listeners",), ("ListenerSet",)):
        cur = doc
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, list):
            return cur
    return []


def find_rules_anywhere(d, acc=None):
    if acc is None:
        acc = []
    if isinstance(d, dict):
        for k, v in d.items():
            if k == "Rules" and isinstance(v, list):
                acc.extend(v)
            else:
                find_rules_anywhere(v, acc)
    elif isinstance(d, list):
        for it in d:
            find_rules_anywhere(it, acc)
    return acc


def pick(vals):
    for v in vals:
        if v:
            return v
    return ""


def main():
    ak = os.environ.get("AK") or os.environ.get("VOLC_AK")
    sk = os.environ.get("SK") or os.environ.get("VOLC_SK")
    region = os.environ.get("REGION", "cn-beijing")
    alb_id = os.environ.get("ALB_ID")
    if not (ak and sk and alb_id):
        raise SystemExit("missing AK/SK/ALB_ID")

    endpoint = f"alb.{region}.volcengineapi.com"
    service = "alb"

    # 1) 拿到所有监听器
    ls = []
    for ver in ("2020-04-01", "2020-11-26", "2023-01-01"):
        d = curl_json(
            sign_url(
                ak,
                sk,
                region,
                service,
                endpoint,
                "DescribeListeners",
                ver,
                {"LoadBalancerId": alb_id},
            )
        )
        ls = extract_listeners(d)
        if ls:
            break

    rows = []
    for l in ls:
        proto = str(l.get("Protocol", "")).upper()
        port = int(l.get("Port") or 0)
        if proto not in ("HTTP", "HTTPS") or port not in (80, 443):
            continue
        lid = l.get("ListenerId") or l.get("Id") or ""
        if not lid:
            continue
        # 2) 拉规则（优先 DescribeRules，再回退 DescribeListenerAttributes）
        rules = []
        for ver in ("2020-04-01", "2020-11-26", "2023-01-01"):
            rules = find_rules_anywhere(
                curl_json(
                    sign_url(
                        ak,
                        sk,
                        region,
                        service,
                        endpoint,
                        "DescribeRules",
                        ver,
                        {"ListenerId": lid},
                    )
                )
            )
            if rules:
                break
        if not rules:
            for ver in ("2020-04-01", "2020-11-26", "2023-01-01"):
                rules = find_rules_anywhere(
                    curl_json(
                        sign_url(
                            ak,
                            sk,
                            region,
                            service,
                            endpoint,
                            "DescribeListenerAttributes",
                            ver,
                            {"ListenerId": lid},
                        )
                    )
                )
                if rules:
                    break
        for r in rules:
            host = pick(
                [r.get("Domain"), r.get("Host"), r.get("HostHeader")]
            )
            path = pick(
                [r.get("Path"), r.get("Url"), r.get("PathPattern")]
            ) or "/"
            conds = r.get("RuleConditions") or []
            if not host:
                for c in conds:
                    fld = str(c.get("Field", "")).lower()
                    if fld in ("host", "host-header", "hostheader"):
                        vals = (
                            (c.get("HostHeaderConfig") or {}).get("Values")
                            or []
                        )
                        if vals:
                            host = vals[0]
                            break
            if not path:
                for c in conds:
                    fld = str(c.get("Field", "")).lower()
                    if fld in ("path", "path-pattern"):
                        cfg = (
                            c.get("PathConfig")
                            or c.get("PathPatternConfig")
                            or {}
                        )
                        vals = cfg.get("Values") or []
                        if vals:
                            path = vals[0]
                            break
            sg = pick(
                [r.get("ServerGroupId"), r.get("BackendServerGroupId")]
            )
            rows.append(
                {
                    "port": port,
                    "host": host or "-",
                    "path": path,
                    "sg": sg or "",
                }
            )

    out_path = Path("/tmp/alb_rules.tsv")
    with out_path.open("w", encoding="utf-8") as f:
        f.write("port\thost\tpath\tserver_group_id\n")
        for it in rows:
            f.write(
                f"{it['port']}\t{it['host']}\t{it['path']}\t{it['sg']}\n"
            )
    print(str(out_path))


if __name__ == "__main__":
    main()


