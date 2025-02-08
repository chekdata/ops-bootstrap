import re
import time
import random
import string
import hashlib

def getMd5(text):
    hash = hashlib.md5()
    hash.update(text.encode("utf8"))
    return hash.hexdigest()

def splitUrl(url):
    p = re.compile("^(http://|https://)?([^/?]+)(/[^?]*)?(\\?.*)?$")
    if not p:
        return None
    m = p.match(url)
    if not m:
        return "", "", "", ""
    scheme, domain, uri, args = m.groups()
    if not scheme: scheme = "http://"
    if not uri: uri = "/"
    if not args: args = ""
    return scheme, domain, uri, args

def getRandomString(n):
    x = ''.join(random.sample(string.ascii_letters + string.digits, n))
    return x

def genTypeAUrl(url, key, signName, uid, ts):
    scheme, domain, uri, args = splitUrl(url)
    rand = getRandomString(10)
    text = "%s-%d-%s-%s-%s" %(uri, ts, rand, uid, key)
    hash = getMd5(text)
    authArg = "%s=%d-%s-%s-%s" %(signName, ts, rand, uid, hash)
    if args:
        return "%s%s%s%s&%s" %(scheme, domain, uri, args, authArg)
    else:
        return "%s%s%s?%s" %(scheme, domain, uri, authArg)

def genTypeBUrl(url, key, ts):
    scheme, domain, uri, args = splitUrl(url)
    ts_str = time.strftime('%Y%m%d%H%M', time.localtime(ts))
    text = "%s%s%s" % (key, ts_str, uri)
    hash = getMd5(text)
    return "%s%s/%s/%s%s%s" %(scheme, domain, ts_str, hash, uri, args)

def genTypeCUrl(url, key, ts):
    scheme, domain, uri, args = splitUrl(url)
    ts = "%x" %(int(ts))
    text = "%s%s%s" %(key, uri, ts)
    hash = getMd5(text)
    return "%s%s/%s/%s%s%s" %(scheme, domain, hash, ts, uri, args)

def genTypeDUrl(url, key, signName, tName, ts, ts_base):
    scheme, domain, uri, args = splitUrl(url)
    ts_str = "%d" %(int(ts))
    if ts_base == 16:
        ts_str = "%x" %(int(time.time()))
    text = "%s%s%s" %(key, uri, ts_str)
    hash = getMd5(text)
    authArg = "%s=%s&%s=%s" %(signName, hash, tName, ts_str)
    if args:
        return "%s%s%s%s&%s" %(scheme, domain, uri, args, authArg)
    else:
        return "%s%s%s?%s" %(scheme, domain, uri, authArg)

def genTypeEUrl(url, key, signName, timeName, ts, ts_base):
    scheme, domain, uri, args = splitUrl(url)
    ts_str = "%d" %(int(ts))
    if ts_base == 16:
        ts_str = "%x" %(int(time.time()))
    text = "%s%s%s%s" %(key, domain, uri, ts_str)
    hash = getMd5(text)
    authArg = "%s=%s&%s=%s" %(signName, hash, timeName, ts_str)
    if args:
        return "%s%s%s%s&%s" %(scheme, domain, uri, args, authArg)
    else:
        return "%s%s%s?%s" %(scheme, domain, uri, authArg)

def get_video_play_path(file_path,ts):
    from urllib.parse import quote
    # url = 'http://bytevdn.chekkk.com/for 汽车之家/北京-上海长测/小鹏G6/20240114/加塞_2024-01-14 10:11:19.merge.mp4'
    url = file_path
    url = quote(url, ':/?#[]@!$&\'()*+,;=')
    primaryKey = 'd24d2fa36d1145919de3e1a50c0e6d39'
    signName = "auth_key"
    timeName = "t"
    uid = "0"
    # ts = time.time() + 3600 * 24 # 有效期 24h 需要设置长一点有效期

    # print("TypeA:{}".format(genTypeAUrl(url, primaryKey, signName, uid, ts)))
    res_url = genTypeAUrl(url, primaryKey, signName, uid, ts)
    # res_url = res_url.replace("http:", "https:")
    print("OriginUrl:{}".format(url))
    print("TypeA:{}".format(res_url))
    return res_url



def test(url):
    from urllib.parse import quote
    # url = 'http://bytevdn.chekkk.com/for 汽车之家/北京-上海长测/小鹏G6/20240114/加塞_2024-01-14 10:11:19.merge.mp4'
    url = quote(url, ':/?#[]@!$&\'()*+,;=')
    print(url)
    primaryKey = 'd24d2fa36d1145919de3e1a50c0e6d39'
    signName = "auth_key"
    timeName = "t"
    uid = "0"
    ts = time.time() + 3600
    new_url = genTypeAUrl(url, primaryKey, signName, uid, ts)
    new_url = new_url.replace("http:", "https:")
    print("OriginUrl:{}".format(url))
    print("TypeA:{}".format(new_url))
    # print("TypeB:{}".format(genTypeBUrl(url, primaryKey, ts)))
    # print("TypeC:{}".format(genTypeCUrl(url, primaryKey, ts)))
    # print("TypeD:{}".format(genTypeDUrl(url, primaryKey, signName, timeName, ts, 10)))
    # print("TypeE:{}".format(genTypeEUrl(url, primaryKey, signName, timeName, ts, 10)))
    return new_url

if __name__ == "__main__":
    url = f'http://bytevdn.chekkk.com/temp/heal_project/suno_fe4173bf-68e0-4ea3-9db1-b13c4754c068.mp3'
    url = f'http://bytevdn.chekkk.com/{"model/jiyue_01.zip"}'

    test(url)
