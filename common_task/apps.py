from django.apps import AppConfig
import atexit
import asyncio
import threading
import sys
import os
import logging

logger = logging.getLogger('common_task')

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common_task'
    cleanup_initialized = False


    # def ready(self):
    #     from .tasks import cleanup_resources

    def ready(self):
        # 检查是否是主进程
        if 'runserver' not in sys.argv or os.environ.get('RUN_MAIN') != 'true':
            return

        if not self.cleanup_initialized:
            from .tasks import (
                start_background_cleanup, 
                start_timeout_checker,
                cleanup_resources
            )            
            
            try:
                # 创建清理线程
                self.cleanup_thread = threading.Thread(
                    target=start_background_cleanup,
                    name="BackgroundCleanup"
                )
                self.cleanup_thread.daemon = True
                
                # 创建超时检查线程
                self.timeout_thread = threading.Thread(
                    target=start_timeout_checker,
                    name="TimeoutChecker"
                )
                self.timeout_thread.daemon = True
                
                # 启动线程
                self.cleanup_thread.start()
                self.timeout_thread.start()
                
                self.cleanup_initialized = True
                logger.info(f"后台清理线程已启动: {self.cleanup_thread.name}")
                logger.info(f"超时检查线程已启动: {self.timeout_thread.name}")
                
                # 注册退出时的清理函数
                def cleanup_handler():
                    """处理退出时的清理"""
                    try:
                        # 创建新的事件循环
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # 停止线程标志
                        from .tasks import cleanup_running, timeout_checker_running
                        cleanup_running = False
                        timeout_checker_running = False
                        
                        # 等待线程结束
                        if self.cleanup_thread.is_alive():
                            self.cleanup_thread.join(timeout=5)
                            
                        if self.timeout_thread.is_alive():
                            self.timeout_thread.join(timeout=5)
                            
                        # 执行资源清理
                        loop.run_until_complete(cleanup_resources())
                        
                    except Exception as e:
                        logger.error(f"清理资源时发生错误: {e}")
                    finally:
                        if loop:
                            loop.close()
                    
                atexit.register(cleanup_handler)
                
            except Exception as e:
                logger.error(f"启动后台清理任务失败: {e}")