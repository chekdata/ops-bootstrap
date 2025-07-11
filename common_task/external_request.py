from django.conf import settings
import aiohttp
import json
import logging

logger = logging.getLogger('common_task')


async def reports_successful_audio_generation(trip_id, task_id):
    try:
        logger.info(f"通知分发服务，trip_id：{trip_id}")
        url = f"https://{settings.DATA_DISTRIBUTION}/send_message_info"
        payload = {
            "trip_id": str(trip_id),
            "task_id": str(task_id),
            "message_type": "audio"
        }
        headers = {
            'Content-Type': 'application/json',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.text()
                if response.status == 200:
                    logger.info(f"通知分发服务成功，响应：{data}")
                else:
                    logger.error(f"通知分发服务失败，状态码：{response.status}，响应：{data}")
    except Exception as e:
        logger.error(f"通知分发服务失败!", exc_info=True)