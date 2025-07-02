import datetime, hashlib, hmac, json
import requests, urllib

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(key.encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'request')
    return kSigning
def getSignHeaders(method, service, host, region, request_parameters, access_key, secret_key):
    contenttype = 'application/x-www-form-urlencoded'
    accept = 'application/json'
    t = datetime.datetime.utcnow()
    xdate = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')
    # *************  1: 拼接规范请求串*************
    canonical_uri = '/'
    canonical_querystring = request_parameters
    canonical_headers = 'content-type:'+ contenttype + '\n' +'host:' + host + '\n' + 'x-date:' + xdate + '\n'
    signed_headers = 'content-type;host;x-date'
    payload_hash = hashlib.sha256(('').encode('utf-8')).hexdigest()
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash
    # *************  2：拼接待签名字符串*************
    algorithm = 'HMAC-SHA256'
    credential_scope = datestamp + '/' + region + '/' + service + '/' + 'request'
    string_to_sign = algorithm + '\n' +  xdate + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    # *************  3：计算签名 *************
    signing_key = getSignatureKey(secret_key, datestamp, region, service)
    signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()
    # *************  4：添加签名到请求header中 *************
    authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature
    headers = {'Accept':accept, 'Content-Type':contenttype, 'X-Date':xdate, 'Authorization':authorization_header}
    return headers

def main_entrance():
    try:
        # ************* 发送请求获取临时AK/SK+Token **********************
        method = 'GET'
        service = 'sts'
        host = 'open.volcengineapi.com' #'open.volcengineapi.com'
        region = "cn-shanghai"
        endpoint = 'https://open.volcengineapi.com'#"tos-cn-shanghai.volces.com"https://console.volcengine.com/auth/login/user/2100459557
        # 填写步骤一中创建的用户的 AK/SK 信息。
        # access_key ='AKLTNjI1MjlkMzNkNTRlNDczZDlhNWVkMzZlNmU2NDFiMmU'
        access_key = 'AKLTYjAwNzNkMjM4ZDk2NDgyMDliOWNjMzEwNzg3NGMxNjM'
        # secret_key = 'TldSaVltTmpPRGN3T0RJd05EWXdPVGs0TTJJelpHVTBPV1UzWmprd01ETQ=='
        secret_key =  'TWpjME5EWXdPR1U0WXpJME5HRXpNemcyTkdSbVlUaGlNVFl4TURKbU9EQQ=='
        # 详细请求参数参考 https://www.volcengine.com/docs/6257/86374
        # 填写步骤二创建的角色名称 trn，格式为 trn:iam::{accountID}:role/{rolename}，其中 {accountID} 为角色所属的账号 ID，{roleName} 为角色名，例如本文中需填写为：trn:iam::2100xxxx4:role/tos_role。
        query_parameters = {
          'Action': 'AssumeRole',
          'RoleSessionName': 'temp_connect_tos',
          'RoleTrn': 'trn:iam::2100459557:role/temp_tos_connect',
          'Version': '2018-01-01'
          }

        request_parameters = urllib.parse.urlencode(query_parameters)
        headers = getSignHeaders(method,service,host, region, request_parameters, access_key, secret_key)
        request_url = endpoint + '?' + request_parameters
        r = requests.get(request_url, headers=headers)
        data= r.json()
        Result = data.get('Result')
        return Result
    except:
        return {}

if __name__ == '__main__':
    main_entrance()