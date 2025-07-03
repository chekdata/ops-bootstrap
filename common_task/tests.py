from django.test import TestCase

# Create your tests here.
import requests

# # 定义要发送的数据
# data = {

#         "intervention":2,
#         "intervention_risk":1,
#         "mpi":150.5,
#         "mpi_risk":120.3,
#         "total_mile":1050.5,
#         "noa_mile":500.0,
#         "lcc_mile":300.0,
#         "noa_lcc_mile":800.0,
#         "standby_mile":250.0,
#         "cur_speed":60.0,
#         "intervention_state":"接管",
# }

# # 定义请求头
# headers = {
#     'Content-Type': 'application/json',
#     # 根据需要添加其他头部信息
# }

# # 发送 POST 请求
# response = requests.post('http://1.95.87.50:8000/common_task/process_after_analysis_data',data=data)

# # 打印响应结果
# print(response.status_code)
# print(response.json())

from pandas import DataFrame
from pathlib import Path
import pandas as pd

def test_tos_csv(csv_path):
    merged_csv = pd.DataFrame()
    if Path(csv_path).exists():
        try:
            df = pd.read_csv(csv_path)
            print(f"读取CSV分片成功 {csv_path}: {df.shape}")
            print(f"第一行数据： {df.iloc[0].to_dict()}")
        except Exception as e:
            logger.error(f"读取CSV分片失败 {csv_path}: {e}")

if __name__ == "__main__":
    csv_path = '/tos/chek-app/app_project/cb8e3aa4-fc19-4e60-9281-939a5886694e/inference_data/阿维塔/阿维塔12/2025-07-03/2025-07-03 18-10-39/阿维塔12_2023款 650 三激光四驱GT版_AVATR.OS 4.0.0_2025-07-03 18-10-39.csv'  # 替换为实际的CSV目录路径
    # 或者测试单个CSV文件
    test_tos_csv(csv_path)  # 替换为实际的CSV文件路径