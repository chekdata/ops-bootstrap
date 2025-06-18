from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models
import json

def is_valid_phone_number(phone: str) -> bool:
    import re
    """
    验证输入的字符串是否为有效的中国手机号

    参数:
        phone (str): 需要验证的字符串

    返回:
        bool: 如果是有效手机号返回True，否则返回False
    """
    # 去除空格和+号
    phone = phone.strip().replace(' ', '').replace('+', '')

    # 正则表达式模式：
    # 1. 以86开头（可选）
    # 2. 第二位为3-9的11位数字
    pattern = r'^(86)?(1[3-9])\d{9}$'

    return bool(re.match(pattern, phone))

def send_sms(phone_number, code):

    try:
        # 你的 "SecretId" 和 "SecretKey"
        cred = credential.Credential("AKID778JQNI2kKfx1pTu8C7nGXaQ3RZAf0F7", "nTzexAubM3Qgy84mMmywgEYjxQrDKIVf")

        # 创建 SMS 的客户端对象
        client = sms_client.SmsClient(cred, "ap-guangzhou")

        # 实例化一个请求对象
        req = models.SendSmsRequest()

        # 组装请求参数
        valid_minutes = 10
        req.SmsSdkAppId = "1400797619"  # SDK App ID
        req.SignName = "车控科技"      # 签名内容 车控北京科技
        req.TemplateId = "1970454"  # 模板 ID
        req.PhoneNumberSet = [f"+86{phone_number}"]  # 接收短信的手机号码，格式为国际电话号码格式
        req.TemplateParamSet = [code, str(valid_minutes)]  # 短信模板中的参数，例如验证码

        # 发送短信
        resp = client.SendSms(req)
        print(resp.to_json_string())
        return json.loads(resp.to_json_string())

    except TencentCloudSDKException as err:
        print(err)
        return None



def generate_verification_code():
    import random
    return random.randint(100000, 999999)
if __name__ == '__main__':

    # 测试发送短信
    response = send_sms("18847801997", "123456")
    print(response)
