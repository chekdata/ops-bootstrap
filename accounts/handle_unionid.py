import requests

#chek环境环境
# SOCIAL_AUTH_WEIXIN_appid = 'wxe24cb2373dae28a1'
# SOCIAL_AUTH_WEIXIN_secret = 'e08ac201c7fa17bb812e406e0ddbf1f0'

#汽车之家环境
SOCIAL_AUTH_WEIXIN_appid = 'wxb0b8abc1fddea5f0'
SOCIAL_AUTH_WEIXIN_secret =  'c28d31f34da8ef52532277d2b0be4418'


def get_access_token(app_id, app_secret, code):

    url = f'https://api.weixin.qq.com/sns/oauth2/access_token?appid={app_id}&secret={app_secret}&code={code}&grant_type=authorization_code'
    response = requests.get(url)
    return response.json()

def get_user_info(access_token,openid):
    url = f"https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={openid}"
    response = requests.get(url)
    if response.status_code == 200:
        response.encoding = 'utf-8'
        data = response.json()
        return data
    else:
        print(f"HTTP error {response.status_code}: {response.reason}")
        return None

def down_load_image(url):
    import requests

    # 图片URL
    # url = "https://thirdwx.qlogo.cn/mmopen/vi_32/Q0j4TwGTfTJ1eueFN7wzkicvHjfRX5WiabmWFquMUE1c62icPo2CDkp4GDpAsr9Wg9cr9psQ2Ieib2IlyTrhwjmUaQ/132"
    # 发送HTTP请求获取图片内容
    response = requests.get(url)
    return response.content

    # # 将图片内容写入到本地文件
    # with open("downloaded_image.jpg", "wb") as file:
    #     file.write(response.content)
    #
    # print("图片下载完成")


if __name__ == '__main__':
    # SOCIAL_AUTH_WEIXIN_appid = 'wxe24cb2373dae28a1'
    # SOCIAL_AUTH_WEIXIN_secret = 'e08ac201c7fa17bb812e406e0ddbf1f0'
    # code = '081poM000NEwuS1RXB000n9uMQ1poM0p'
    # union_id = 'oRZXq6OE471ZNtmca-Xgr81kKW20'
    # data = get_access_token(SOCIAL_AUTH_WEIXIN_appid, SOCIAL_AUTH_WEIXIN_secret, code)
    # print(data)
    #
    # access_token = data.get('access_token')
    # openid = data.get('openid')
    # # access_token ='82_cgg_LSaf0x15eDf2G_dn6xV5kZ6kJC0qXkkySMRixoPSfoM46FDzfZo3GwwwLKMAGpPO5tIltiNnjzM9FjsB-WyB3NBl1NutXID0DW6raLo'
    # # openid = 'oZjfE6si77HmZldOH-2vDKqtHT64'
    # print(get_user_info(access_token, openid))
    down_load_image()