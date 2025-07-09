import requests
import json
# from handle_dialog.process_kndatabase import *
# from static.static import *
import time
import openai
import uvicorn
from typing import List
import json
from pydantic import BaseModel
from typing import List, Dict, Optional, Any



def ask_openai(cur, conn,msg,msg_answer):
    text_answer = ''
    try:
        url = "http://14.103.40.162:7999/ask_gpt"
        for i in  requests.post(url, json={"message": msg_answer},stream=True):
                pro_data = i.decode('utf-8').replace('"','')

                text_answer += pro_data
                answer = pro_data
                if answer:
                    yield json.dumps(answer, ensure_ascii=False)
        yield json.dumps('Done Generate', ensure_ascii=False)
        message_log(cur, conn, msg, text_answer)
    #data = response.json()
    #print(f"服务器响应: {data}")
    except Exception as e:
        print(e)

def ask_doubao(cur, conn, content, msg,continue_status):
    from volcenginesdkarkruntime import Ark  ##pip install volcengine-python-sdk
    # Authentication
    # 1.If you authorize your endpoint using an API key, you can set your api key to environment variable "ARK_API_KEY"
    # or specify api key by Ark(api_key="${YOUR_API_KEY}").
    # Note: If you use an API key, this API key will not be refreshed.
    # To prevent the API from expiring and failing after some time, choose an API key with no expiration date.

    # 2.If you authorize your endpoint with Volcengine Identity and Access Management（IAM), set your api key to environment variable "VOLC_ACCESSKEY", "VOLC_SECRETKEY"
    # or specify ak&sk by Ark(ak="${YOUR_AK}", sk="${YOUR_SK}").
    # To get your ak&sk, please refer to this document([https://www.volcengine.com/docs/6291/65568](https://www.volcengine.com/docs/6291/65568))
    # For more information，please check this document（[https://www.volcengine.com/docs/82379/1263279](https://www.volcengine.com/docs/82379/1263279)）
    client = Ark(api_key="598851d5-274b-4b7e-8c3d-42dfba56ae35")
    text_answer = ''
    # Streaming:
    print("----- streaming request -----")
    stream = client.chat.completions.create(
        model="ep-20240612104738-2ltkc",
        messages=msg,
        stream=True,
        temperature=0.7,  # 用于控制生成文本的随机性和创造性，Temperature值越大随机性越大，取值范围0~1
        top_p=0.9,  # 用于控制输出tokens的多样性，TopP值越大输出的tokens类型越丰富，取值范围0~1
    )
    yield json.dumps(
        {'code': 200, 'message': '成功', 'data': {'content': '','status':'start!'}}, ensure_ascii=False)
    for chunk in stream:
        if not chunk.choices:
            continue

        text_answer += chunk.choices[0].delta.content
        # yield json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)
        yield json.dumps(
       {'code': 200, 'message': '成功','data':{'content':text_answer}}, ensure_ascii=False )
    yield json.dumps(
        {'code': 200, 'message': '成功', 'data': {'content': text_answer,'status':'done!'}}, ensure_ascii=False)


    message_log(cur, conn, content, text_answer,continue_status)


def handle_web_dialog( msg):
    from volcenginesdkarkruntime import Ark
    client = Ark(
        api_key="598851d5-274b-4b7e-8c3d-42dfba56ae35",  # ARK_API_KEY 需要替换为您在平台创建的 API Key
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )

    stream = client.bot_chat.completions.create(
        model="bot-20241205142938-kcw54",  # bot-20241205142938-kcw54 为您当前的智能体的ID，注意此处与Chat API存在差异。差异对比详见 SDK使用指南
        messages=msg,
        stream=False
    )
    text_answer = ''

    # yield json.dumps(
    #     {'code': 200, 'message': '成功', 'data': {'content': '','status':'start!'}}, ensure_ascii=False)
    
    # for chunk in stream:
    #     if chunk.references:
    #         pass
    #         #sprint(chunk.references)
    #     if not chunk.choices:
    #         # print('chunk.choices')
    #         continue

    #     text_answer += chunk.choices[0].delta.content
    #     text_answer.replace('*','')
    # print(stream.choices[0].message.content)
    #     yield json.dumps(
    #    {'code': 200, 'message': '成功','data':{'content':text_answer}}, ensure_ascii=False )
    # yield json.dumps(
    #     {'code': 200, 'message': '成功', 'data': {'content': text_answer,'status':'done!'}}, ensure_ascii=False)
    return stream.choices[0].message.content




# 设置OpenAI的API密钥
openai.api_key = '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'

# 将你的功能封装在一个函数里
def get_chat_response(user_message):
    try:
        messages =[{
        "role": "system",
        "content": """Use the following guidelines:

        Generate a Chinese short comment within 15 characters.
        Describe the matching degree between the user and the car model in driving style.
        Use metaphors like couple, partner, personality mismatch, rhythm mismatch, etc.
        Prohibit technical terms (such as "100km/h acceleration", "acceleration", "torque", etc.).
        Do not explain indicators, only express matching emotions.
        Only output the content of the comment field (Chinese short sentence).
        输出结果需要类似于下面几种风格
        - “一个热脸贴冷屁股”
        - “急性子遇上慢吞吞”
        - “全程催油门，无人响应”
        - “你在飙车，他在思考人生”
        """
        }]

        content = f"""帮我按照下面的数据 根据system的要求生成15字匹配总结 要求结果不要直接带有user style 和car style 内容
            输出结果需要类似于下面几种风格 而不是 类似于活泼小e人遇内敛小i人
        - “一个热脸贴冷屁股” 
        - “急性子遇上慢吞吞”
        - “全程催油门，无人响应”
        - “你在飙车，他在思考人生”
        以下是数据：user_style={user_message.get('user_style')}
        avg_speed_kmh={user_message.get('user_features',{}).get('avg_speed_kmh')}
        accel_mps2={user_message.get('user_features',{}).get('accel_mps2')}
        turn_mps2={user_message.get('user_features',{}).get('turn_mps2')}
        car_style={user_message.get('car_style')}
        accel_100_kmh_sec={user_message.get('car_features',{}).get('accel_100_kmh_sec')}
        torque_nm={user_message.get('car_features',{}).get('torque_nm')}
        car_turn_desc={user_message.get('car_features',{}).get('car_turn_desc')}"""
        messages.append({"role": "user", "content":content})
        res = handle_web_dialog(messages)
        # res = ''
        return res
    except:
        print('gpt访问报错')
        return ''
    # tools = [
    #         {
    #     "type": "function",
    #     "function": {
    #     "name": "generate_driving_match_comment",
    #     "description": "Generate a 15-character Chinese short comment on driving style matching between user and car model",
    #     "parameters": {
    #     "type": "object",
    #     "properties": {
    #     "user_style": {
    #     "type": "string",
    #     "description": "User's driving style label (e.g., ' 快乐小 e 人 ')"
    #     },
    #     "avg_speed_kmh": {
    #     "type": "number",
    #     "description": "User's average driving speed (km/h)"
    #     },
    #     "user_accel_mps2": {
    #     "type": "number",
    #     "description": "User's 急加速 performance (m/s²)"
    #     },
    #     "user_turn_mps2": {
    #     "type": "number",
    #     "description": "User's 急转弯 performance (m/s²)"
    #     },
    #     "car_style": {
    #     "type": "string",
    #     "description": "Car model's style label (e.g., ' 苦苦装 e 小 i 人 ')"
    #     },
    #     "car_accel_100_kmh_sec": {
    #     "type": "number",
    #     "description": "Car's 百公里加速 time (seconds)"
    #     },
    #     "car_torque_nm": {
    #     "type": "number",
    #     "description": "Car's torque peak (Nm)"
    #     },
    #     "car_accel_desc": {
    #     "type": "string",
    #     "description": "Car's intelligent driving 急加速 performance description"
    #     },
    #     "car_turn_desc": {
    #     "type": "string",
    #     "description": "Car's intelligent driving 急转弯 performance description"
    #     }
    #     },
    #     "required": [
    #     "user_style",
    #     "avg_speed_kmh",
    #     "user_accel_mps2",
    #     "user_turn_mps2",
    #     "car_style",
    #     "car_accel_100_kmh_sec",
    #     "car_torque_nm",
    #     "car_accel_desc",
    #     "car_turn_desc"
    #     ],
    #     "additionalProperties": False
    #     }
    #     }
    #     }
    # ]

    # # response = openai.ChatCompletion.create(
    # #     model="gpt-4o",
    # #     messages=messages,
    # #     tools=tools,
    # # )
    # response = openai.chat.completions.create(
    #   model="gpt-4o",
    #   messages=messages,
    #   tools=tools,
    # )
    # return response




if __name__ == '__main__':
    # for i in handle_web_dialog( [{"role": "user", "content": '今天金华市天气怎么样'}]):
    #     print(i)
    # conn, cur = connect_mysql(mysql_vehicle)
    # create_database(cur, conn)
    car_dict = {
  "user_style": "快乐小e人",
  "user_features": {
    "avg_speed_kmh": 88.8,
    "max_speed_kmh": 140,
    "accel_mps2": 12.6,
    "turn_mps2": 8.8
  },
  "car_style": "苦苦装e小i人",
  "car_features": {
    "accel_100_kmh_sec": 8.8,
    "torque_nm": 1400,
    "accel_mps2": 8.81,
    "turn_mps2": 12.61
  }
}
    print(get_chat_response(car_dict))