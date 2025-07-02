# import time
# import tracemalloc
# import functools
# import logging

# # 设置日志
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# # 如果没有设置 handler，可以添加一个（仅运行一次）
# if not logger.hasHandlers():
#     ch = logging.StreamHandler()
#     ch.setLevel(logging.INFO)
#     formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
#     ch.setFormatter(formatter)
#     logger.addHandler(ch)

# def monitor(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         start_time = time.perf_counter()
#         tracemalloc.start()

#         result = func(*args, **kwargs)

#         end_time = time.perf_counter()
#         current, peak = tracemalloc.get_traced_memory()
#         tracemalloc.stop()

#         logger.info(f"[{func.__name__}] 执行时间: {end_time - start_time:.4f} 秒")
#         logger.info(f"[{func.__name__}] 当前内存占用: {current / 1024:.2f} KB")
#         logger.info(f"[{func.__name__}] 峰值内存占用: {peak / 1024:.2f} KB")

#         return result
#     return wrapper

# @monitor
# def heavy_func():
#     data = [x**2 for x in range(10**6)]
#     return sum(data)

import time
import tracemalloc
import functools
import logging
import asyncio
import inspect

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def monitor(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        tracemalloc.start()

        result = await func(*args, **kwargs)

        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        logger.info(f"[{func.__name__}] 执行时间: {end_time - start_time:.4f} 秒")
        logger.info(f"[{func.__name__}] 当前内存占用: {current / 1024:.2f} KB")
        logger.info(f"[{func.__name__}] 峰值内存占用: {peak / 1024:.2f} KB")

        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        tracemalloc.start()

        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        logger.info(f"[{func.__name__}] 执行时间: {end_time - start_time:.4f} 秒")
        logger.info(f"[{func.__name__}] 当前内存占用: {current / 1024:.2f} KB")
        logger.info(f"[{func.__name__}] 峰值内存占用: {peak / 1024:.2f} KB")

        return result

    # 判断是否为异步函数
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

@monitor
def heavy_func():
    data = [x**2 for x in range(10**6)]
    return sum(data)
if __name__ == "__main__":
    heavy_func()