# import datetime, hashlib, hmac, json
# import requests, urllib

# def sign(key, msg):
#     return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
# def getSignatureKey(key, dateStamp, regionName, serviceName):
#     kDate = sign(key.encode('utf-8'), dateStamp)
#     kRegion = sign(kDate, regionName)
#     kService = sign(kRegion, serviceName)
#     kSigning = sign(kService, 'request')
#     return kSigning
# def getSignHeaders(method, service, host, region, request_parameters, access_key, secret_key):
#     contenttype = 'application/x-www-form-urlencoded'
#     accept = 'application/json'
#     t = datetime.datetime.utcnow()
#     xdate = t.strftime('%Y%m%dT%H%M%SZ')
#     datestamp = t.strftime('%Y%m%d')
#     # *************  1: 拼接规范请求串*************
#     canonical_uri = '/'
#     canonical_querystring = request_parameters
#     canonical_headers = 'content-type:'+ contenttype + '\n' +'host:' + host + '\n' + 'x-date:' + xdate + '\n'
#     signed_headers = 'content-type;host;x-date'
#     payload_hash = hashlib.sha256(('').encode('utf-8')).hexdigest()
#     canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash
#     # *************  2：拼接待签名字符串*************
#     algorithm = 'HMAC-SHA256'
#     credential_scope = datestamp + '/' + region + '/' + service + '/' + 'request'
#     string_to_sign = algorithm + '\n' +  xdate + '\n' +  credential_scope + '\n' +  hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
#     # *************  3：计算签名 *************
#     signing_key = getSignatureKey(secret_key, datestamp, region, service)
#     signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()
#     # *************  4：添加签名到请求header中 *************
#     authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + credential_scope + ', ' +  'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature
#     headers = {'Accept':accept, 'Content-Type':contenttype, 'X-Date':xdate, 'Authorization':authorization_header}
#     return headers

# def main_entrance():
#     try:
#         # ************* 发送请求获取临时AK/SK+Token **********************
#         method = 'GET'
#         service = 'sts'
#         # host = 'open.volcengineapi.com' #'open.volcengineapi.com' '
#         host = 'sts.volcengineapi.com'
#         region = "cn-shanghai"
#         endpoint = 'https://open.volcengineapi.com'#"tos-cn-shanghai.volces.com"https://console.volcengine.com/auth/login/user/2100459557
#         # 填写步骤一中创建的用户的 AK/SK 信息。
#         # access_key ='AKLTNjI1MjlkMzNkNTRlNDczZDlhNWVkMzZlNmU2NDFiMmU'
#         access_key = 'AKLTYjAwNzNkMjM4ZDk2NDgyMDliOWNjMzEwNzg3NGMxNjM'
#         # secret_key = 'TldSaVltTmpPRGN3T0RJd05EWXdPVGs0TTJJelpHVTBPV1UzWmprd01ETQ=='
#         secret_key =  'TWpjME5EWXdPR1U0WXpJME5HRXpNemcyTkdSbVlUaGlNVFl4TURKbU9EQQ=='
#         # 详细请求参数参考 https://www.volcengine.com/docs/6257/86374
#         # 填写步骤二创建的角色名称 trn，格式为 trn:iam::{accountID}:role/{rolename}，其中 {accountID} 为角色所属的账号 ID，{roleName} 为角色名，例如本文中需填写为：trn:iam::2100xxxx4:role/tos_role。
#         query_parameters = {
#           'Action': 'AssumeRole',
#           'RoleSessionName': 'temp_connect_tos',
#           'RoleTrn': 'trn:iam::2100459557:role/temp_tos_connect',
#           'Version': '2018-01-01',

#           }

#         request_parameters = urllib.parse.urlencode(query_parameters)
#         headers = getSignHeaders(method,service,host, region, request_parameters, access_key, secret_key)
#         request_url = endpoint + '?' + request_parameters
#         print(request_url)
#         r = requests.get(request_url, headers=headers)
#         data= r.json()
#         print(data)
#         Result = data.get('Result')
#         return Result
#     except:
#         return {}

# if __name__ == '__main__':
#     print(main_entrance())


###2025 0709 启用
from __future__ import print_function
import volcenginesdkcore
import volcenginesdksts
from pprint import pprint
from volcenginesdkcore.rest import ApiException
def main_entrance():
     # 配置AK/SK
     configuration = volcenginesdkcore.Configuration()
     configuration.ak = "AKLTYjAwNzNkMjM4ZDk2NDgyMDliOWNjMzEwNzg3NGMxNjM"
     configuration.sk = "TWpjME5EWXdPR1U0WXpJME5HRXpNemcyTkdSbVlUaGlNVFl4TURKbU9EQQ=="
     configuration.region = "cn-shanghai"


     # 设置默认配置
     volcenginesdkcore.Configuration.set_default(configuration)
     try:
         # 创建STS API实例
         api_instance = volcenginesdksts.STSApi()
         # 构造AssumeRole请求
         assume_role_request = volcenginesdksts.AssumeRoleRequest(
         duration_seconds=10800, # 临时凭证有效期(秒)，范围900-43200
         role_trn="trn:iam::2100459557:role/temp_tos_connect", # 替换为实际角色TRN
         role_session_name="temp_connect_tos" # 会话名称
         )
         # 调用API获取临时凭证
         response = api_instance.assume_role(assume_role_request)
         # 提取临时凭证
         credentials = response.credentials
        #  sts_token = {
        #  "access_key": credentials.access_key_id,
        #  "secret_key": credentials.secret_access_key,
        #  "session_token": credentials.session_token,
        #  "expiration": credentials.expired_time
        #  }
         # 打印凭证信息
         
         sts_token = {"Credentials":
         {"ExpiredTime":credentials.expired_time,
         "AccessKeyId":credentials.access_key_id,
         "SecretAccessKey":credentials.secret_access_key,
         "SessionToken":credentials.session_token},
         "AssumedRoleUser":{"Trn":"trn:sts::2100459557:assumed-role/temp_tos_connect/temp_connect_tos","AssumedRoleId":"34664835:temp_connect_tos"}}
         return sts_token
     except ApiException as e:
         print("调用STS API失败:")
         print(f"状态码: {e.status}")
         print(f"原因: {e.reason}")
         print(f"响应头: {e.headers}")
         print(f"响应体: {e.body}")
         return None

# 添加执行入口 - 这是关键部分
if __name__ == '__main__':
     # 实际调用函数获取STS令牌
     sts_token = main_entrance()
     # 添加一些额外的输出信息
     if sts_token:
         print("\nSTS临时凭证获取成功！")
         print(f"Access Key: {sts_token['access_key']}")
         print(f"Secret Key: {sts_token['secret_key'][:5]}...{sts_token['secret_key'][-5:]}")
         print(f"Session Token: {sts_token['session_token'][:15]}...{sts_token['session_token'][-15:]}")
         print(f"过期时间: {sts_token['expiration']}")
     else:
         print("\n未能获取STS临时凭证，请检查错误信息")

