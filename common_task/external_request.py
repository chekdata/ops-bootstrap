import os
import asyncio
import uuid
import logging
import aiohttp
from django.conf import settings
from typing import Union
from uuid import UUID

####################################################################
# NOTE: python 文件调试增加内容
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Django设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# 添加项目根目录到Python路径
import sys
project_root = '/chekkk/code/chekappbackendnew'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 初始化Django
import django
from django.conf import settings as django_settings
if not django_settings.configured:
    django.setup()
######################################################################
logger = logging.getLogger('common_task')

async def reports_successful_audio_generation(trip_id: Union[UUID, str], task_id: Union[UUID, str]) -> None:
    """
    异步通知分发服务音频生成成功
    Args:
        trip_id: 行程ID
        task_id: 任务ID
    """
    try:
        logger.info(f"通知分发服务，trip_id：{trip_id}")
        url = f"https://{settings.DATA_DISTRIBUTION}/send_message_info"
        logger.info(f"通知分发服务，url：{url}")
        
        # 确保ID转换为字符串
        payload = {
            "trip_id": str(trip_id),
            "task_id": str(task_id),
            "message_type": "audio"
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        # 设置超时时间，避免无限等待
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.text()
                if response.status == 200:
                    logger.info(f"通知分发服务成功，响应：{data}")
                else:
                    logger.error(f"通知分发服务失败，状态码：{response.status}，响应：{data}")
                    
    except aiohttp.ClientError as e:
        logger.error(f"HTTP客户端错误: {str(e)}")
    except asyncio.TimeoutError:
        logger.error("通知分发服务超时")
    except Exception as e:
        logger.error(f"通知分发服务失败: {str(e)}", exc_info=True)


def sync_call_reports_successful_audio_generation(trip_id: Union[UUID, str], task_id: Union[UUID, str]) -> None:
    """
    在同步上下文中安全地调用异步函数
    Args:
        trip_id: 行程ID
        task_id: 任务ID
    """
    # 创建新的事件循环（用于非async环境）
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(reports_successful_audio_generation(trip_id, task_id))
    finally:
        loop.close()

if __name__ == '__main__':
    # 配置基本日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 测试调用
    sync_call_reports_successful_audio_generation(
        trip_id=uuid.uuid4(),
        task_id=uuid.uuid4()
    )