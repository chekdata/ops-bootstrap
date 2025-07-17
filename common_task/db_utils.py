import time
import logging
import asyncio
from functools import wraps
from django.db import connections, OperationalError, InterfaceError, connection
from django.conf import settings
from django.db import transaction, DatabaseError

logger = logging.getLogger(__name__)

# Connection error codes that indicate a connection issue
CONNECTION_ERROR_CODES = [2006, 2013]
CONNECTION_ERROR_MESSAGES = [
    "MySQL server has gone away",
    "Lost connection to MySQL server",
    "Connection reset by peer"
]

def db_retry(max_attempts=3, retry_delay=0.5):
    """
    数据库操作重试装饰器
    用于处理数据库连接断开的情况
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, InterfaceError) as e:
                    # 检查是否是连接断开错误
                    if any(err in str(e) for err in ["2006", "MySQL server has gone away", "Connection reset by peer"]):
                        if attempt < max_attempts - 1:  # 如果不是最后一次尝试
                            logger.warning(f"数据库连接断开，正在重试 ({attempt+1}/{max_attempts}): {e}")
                            # 关闭所有连接并等待重试
                            connections.close_all()
                            time.sleep(retry_delay * (attempt + 1))  # 指数退避
                        else:
                            logger.error(f"数据库连接重试失败 ({max_attempts}/{max_attempts}): {e}")
                            raise
                    else:
                        # 其他数据库错误，直接抛出
                        raise
        return wrapper
    return decorator

def async_db_retry(max_attempts=3, retry_delay=0.5):
    """
    异步数据库操作重试装饰器
    用于处理数据库连接断开的情况
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, InterfaceError) as e:
                    # 检查是否是连接断开错误
                    if any(err in str(e) for err in ["2006", "MySQL server has gone away", "Connection reset by peer"]):
                        if attempt < max_attempts - 1:  # 如果不是最后一次尝试
                            logger.warning(f"数据库连接断开，正在重试 ({attempt+1}/{max_attempts}): {e}")
                            # 关闭所有连接并等待重试
                            connections.close_all()
                            await asyncio.sleep(retry_delay * (attempt + 1))  # 指数退避
                        else:
                            logger.error(f"数据库连接重试失败 ({max_attempts}/{max_attempts}): {e}")
                            raise
                    else:
                        # 其他数据库错误，直接抛出
                        raise
        return wrapper
    return decorator

def ensure_connection():
    """
    确保数据库连接有效
    在长时间运行的任务中定期调用此函数
    """
    try:
        # 尝试执行一个简单的查询来验证连接
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except (OperationalError, InterfaceError, DatabaseError) as e:
        error_str = str(e)
        is_connection_error = any(str(code) in error_str for code in CONNECTION_ERROR_CODES) or \
                             any(msg in error_str for msg in CONNECTION_ERROR_MESSAGES)
        
        if is_connection_error:
            logger.warning(f"数据库连接已断开，正在重新连接: {e}")
            connections.close_all()
            return False
        logger.error(f"数据库连接检查失败 (非连接错误): {e}")
        raise