import requests
import json


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
    long_image_result = call_long_image_succeeded(
        task_id="33332",
        brand_name="奥迪",
        trip_id = '333',
        is_test_env=False  # 生产环境设为False，测试环境设为True
    )
    print("长图接口返回:", long_image_result)

    # 测试报告生成成功接口
    report_result = call_report_succeeded(
        task_id="33332",
        brand_name="奥迪",
        trip_id='333',
        is_test_env=False  # 生产环境设为False，测试环境设为True
    )
    print("报告接口返回:", report_result)