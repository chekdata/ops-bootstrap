import http.client
import json
from django.conf import settings
logger = logging.getLogger('common_task')


async def  reports_successful_audio_generation(trip_id, task_id):

    IP = setting.DATA_DISTRIBUTION
    conn = http.client.HTTPSConnection(IP)
    payload = json.dumps({
    "trip_id": trip_id,
    "task_id": task_id
    })
    headers = {
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'Host': IP,
    'Connection': 'keep-alive'
    }
    conn.request("POST", "/send_message_info", payload, headers)
    res = conn.getresponse()
    data = res.read()
    logger.info(f"通知分发服务，报告生成情况：{ata.decode("utf-8")}")