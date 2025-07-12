import requests
import json

def generate_journey_report(journey_id, user_avatar, user_nickname, target_path, user_id ,
                           base_url="https://report-staging.chekkk.com/api"):
    """
    调用生成旅程报告的API
    
    Args:
        journey_id (str): 旅程ID
        user_avatar (str): 用户头像URL
        user_nickname (str): 用户昵称
        target_path (str): 目标路径
        base_url (str, optional): API基础URL，默认为本地开发环境
    
    Returns:
        dict: API响应数据
        None: 请求失败时
    
    Raises:
        requests.exceptions.RequestException: 网络请求异常
        json.JSONDecodeError: 响应解析异常
    """
    url = f"{base_url}/generate_journey_report"
    
    # 构建请求数据
    payload = {
        "journeyId": journey_id,
        "userInfo": {
            "avatar": user_avatar,
            "nickName": user_nickname
        },
        "targetPath": target_path
    }
    
    # headers = {
    #     "Content-Type": "application/json"
    # }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": '30e844532fb0016cc362c5decff868620c05af726055db44584d31077c2f34e7'  # 添加API密钥头
    }
    try:
        # 发送请求并获取响应
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 检查HTTP状态码
        
        # 解析JSON响应
        return response.json()
    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP错误 [{http_err.response.status_code}]: {http_err}")
        print(f"响应内容: {http_err.response.text}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"请求异常: {req_err}")
        return None
    except json.JSONDecodeError as json_err:
        print(f"JSON解析错误: {json_err}")
        print(f"响应内容: {response.text}")
        return None
    except Exception as err:
        print(f"未知错误: {err}")
        return None

# 示例调用
if __name__ == "__main__":
    result = generate_journey_report(
        journey_id="2f2b3a7b-c262-47d0-830c-408c12dd06b5",
        user_avatar="https://example.com/avatar.png",
        user_nickname="张三",
        user_id ='1111',
        target_path="00952fc9-aadd-46c6-82b6-15004e4efb30/inference_data/智己/智己L6/2025-01-26/2025-01-26 08-49-45/"
    )
    
    if result:
        print("API调用成功")
        print(result.get('data',{}).get('url'))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("API调用失败")