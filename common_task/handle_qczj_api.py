import requests
import json

import requests
import json

def send_message_info(trip_id: str, task_id: str, url: str = "http://14.103.114.175:8008/send_message_info") -> dict:
    """
    调用发送消息信息的API
    
    参数:
        trip_id (str): 行程ID
        task_id (str): 任务ID
        url (str, optional): API地址，默认为生产环境地址
    
    返回:
        dict: API响应结果（包含success、message等字段）
        
    异常:
        requests.exceptions.RequestException: 网络请求异常
        ValueError: 响应内容非JSON格式
    """
    # 请求头
    headers = {
        "Content-Type": "application/json"
    }
    
    # 请求体
    payload = {
        "trip_id": trip_id,
        "task_id": task_id,
        'message_type':'image'
    }
    
    try:
        # 发送POST请求，设置5秒超时
        response = requests.post(
            url=url,
            headers=headers,
            data=json.dumps(payload),
            timeout=5
        )
        
        # 检查HTTP状态码
        response.raise_for_status()  # 非200状态码会抛出异常
        
        # 解析JSON响应
        return response.json()
        
    except requests.exceptions.RequestException as e:
        # 网络异常处理
        return {
            "success": False,
            "message": f"网络请求失败: {str(e)}",
            "status_code": e.response.status_code if hasattr(e, 'response') else None
        }
    except (json.JSONDecodeError, ValueError) as e:
        # 响应解析异常
        return {
            "success": False,
            "message": f"响应解析失败: {str(e)}",
            "raw_response": response.text if 'response' in locals() else None
        }



def call_long_image_succeeded(task_id, brand_name, trip_id,is_test_env=False):
    """
    调用长图生成成功回调接口

    参数:
        task_id (str): 任务ID（对应接口字段task_id）
        brand_name (str): 品牌名称（对应接口示例中的brandName）
        is_test_env (bool): 是否使用测试环境，默认False（生产环境）

    返回:
        dict: 接口返回的JSON数据
    """
    # 确定请求地址
    if is_test_env:
        url = "xx2"  # 测试环境地址（请替换为实际测试地址）
    else:
        url = "http://voc.autohome.com.cn/api/common/testDriveReport/longImageSucceeded"  # 生产环境地址

    # 构造请求参数
    payload = {
        "task_id": task_id,
        'trip_id':trip_id,
    }

    # 设置请求头
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # 发送POST请求
        response = requests.post(
            url=url,
            data=json.dumps(payload),
            headers=headers
        )
        # 解析返回的JSON数据并返回
        return response.json()
    except Exception as e:
        # 异常处理（如网络错误等）
        return {
            "message": f"请求失败: {str(e)}",
            "returncode": 1,
            "success": False
        }


def call_report_succeeded(task_id, brand_name, trip_id,is_test_env=False):
    """
    调用报告生成成功回调接口

    参数:
        task_id (str): 任务ID（对应接口字段task_id）
        brand_name (str): 品牌名称（对应接口示例中的brandName）
        is_test_env (bool): 是否使用测试环境，默认False（生产环境）

    返回:
        dict: 接口返回的JSON数据
    """
    # 确定请求地址
    if is_test_env:
        url = "xx2"  # 测试环境地址（请替换为实际测试地址）
    else:
        url = "http://voc.autohome.com.cn/api/common/testDriveReport/reportSucceeded"  # 生产环境地址

    # 构造请求参数
    payload = {
        "task_id": task_id,
        'trip_id':trip_id
    }

    # 设置请求头
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # 发送POST请求
        response = requests.post(
            url=url,
            data=json.dumps(payload),
            headers=headers
        )
        # 解析返回的JSON数据并返回
        return response.json()
    except Exception as e:
        # 异常处理（如网络错误等）
        return {
            "message": f"请求失败: {str(e)}",
            "returncode": 1,
            "success": False
        }


# 示例调用
if __name__ == "__main__":
    # 测试长图生成成功接口
    # long_image_result = call_long_image_succeeded(
    #     task_id="33332",
    #     brand_name="奥迪",
    #     trip_id = '333',
    #     is_test_env=False  # 生产环境设为False，测试环境设为True
    # )
    # print("长图接口返回:", long_image_result)

    # # 测试报告生成成功接口
    # report_result = call_report_succeeded(
    #     task_id="33332",
    #     brand_name="奥迪",
    #     trip_id='333',
    #     is_test_env=False  # 生产环境设为False，测试环境设为True
    # )
    # print("报告接口返回:", report_result)

# 示例调用
# if __name__ == "__main__":
    result = send_message_info(
        trip_id="111111",
        task_id="111111",
    )
    print("API响应:", result)