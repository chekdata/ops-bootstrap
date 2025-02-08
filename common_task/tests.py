from django.test import TestCase

# Create your tests here.
import requests

# 定义要发送的数据
data = {

        "intervention":2,
        "intervention_risk":1,
        "mpi":150.5,
        "mpi_risk":120.3,
        "total_mile":1050.5,
        "noa_mile":500.0,
        "lcc_mile":300.0,
        "noa_lcc_mile":800.0,
        "standby_mile":250.0,
        "cur_speed":60.0,
        "intervention_state":"接管",
}

# 定义请求头
headers = {
    'Content-Type': 'application/json',
    # 根据需要添加其他头部信息
}

# 发送 POST 请求
response = requests.post('http://1.95.87.50:8000/common_task/process_after_analysis_data',data=data)

# 打印响应结果
print(response.status_code)
print(response.json())
