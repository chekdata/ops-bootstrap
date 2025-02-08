# from django.test import TestCase
#
# # Create your tests here.
# import requests
#
# # 定义要发送的数据
# data = {
#
#         'model':'极越01'
#
# }
#
# # 定义请求头
# headers = {
#     'Content-Type': 'application/json',
#     # 根据需要添加其他头部信息
# }
#
# # 发送 POST 请求
# response = requests.post('http://1.95.87.50:8000/api/search_model_info',data=data)
# import json
# # 打印响应结果
# list_res = []
# data = response.json()
#
# for _ in data.get('data'):
#
#     json_string = json.dumps(_,ensure_ascii=False)
#
#     # 将 JSON 字符串中的双引号转义
#     escaped_json_string = json_string.replace('"', '\\"')
#     # str_data = rf""""\"model\":\"{_.get('model')}\",\"hardware_config_version\":\"{_.get('hardware_config_version')}\",\"software_config_version\":\"{_.get('software_config_version')}\""""
#     # res_dat = '{'+str_data+'}'
#     print(escaped_json_string,',')
#     list_res.append(escaped_json_string)
# from django.test import TestCase
# print(list_res)
# # Create your tests here.
# """
#
#
# curl -X POST http://1.95.87.50:8000/api/update_model_tos  -F "file=@/Users/auggie/Downloads/jiyue_01.zip" -F "desc=极越01" -F "name=极越01" -F "version=2024-09-12" -F "brand=极越"  -F "md5_value=a704d58b5c6227a8b6518116a53da473" --form-string "model_config=[
# {\"model\": \"极越01\", \"hardware_config_version\": \"2023款 Max\", \"software_config_version\": \"V2.0.0\"} ,
# {\"model\": \"极越01\", \"hardware_config_version\": \"2023款 Max 长续航\", \"software_config_version\": \"V2.0.0\"} ,
# {\"model\": \"极越01\", \"hardware_config_version\": \"2023款 Max Performance\", \"software_config_version\": \"V2.0.0\"} ,]"
# """


def calculate_md5_value(file_path):
    import hashlib

    md5_hash = hashlib.md5()
    with open(file_path, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()

print(calculate_md5_value('/Users/auggie/PycharmProjects/pythonProject1/myproject/data/jiyue_01 (3).zip'))
