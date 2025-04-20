from django.apps import AppConfig
import atexit
import asyncio
import threading
import sys
import os
import logging
import psutil
from typing import Optional
from django.db import connections
from django.db.utils import OperationalError
import time

logger = logging.getLogger('common_task')

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common_task'
    cleanup_initialized = False
    cleanup_thread: Optional[threading.Thread] = None
    timeout_thread: Optional[threading.Thread] = None
    db_checker_thread: Optional[threading.Thread] = None

    def ready(self):
        """
        应用初始化入口,支持 runserver 和 daphne 两种启动方式
        """
        try:
            # 检查是否允许启动后台任务
            if os.environ.get('DISABLE_BACKGROUND_TASKS') == '1':
                logger.info("后台任务被环境变量禁用")
                return

            # 获取当前进程信息
            current_process = psutil.Process()
            cmdline = ' '.join(current_process.cmdline())

            # 根据不同启动方式进行检查
            if self._should_initialize_tasks(cmdline):
                self._initialize_background_tasks()

        except Exception as e:
            logger.error(f"后台任务初始化检查失败: {str(e)}")

    def _should_initialize_tasks(self, cmdline: str) -> bool:
        """
        检查是否应该初始化后台任务
        """
        try:
            if 'daphne' in cmdline:
                # daphne 模式检查
                return os.environ.get('DAPHNE_WORKER_ID') is None
            elif 'runserver' in sys.argv:
                # runserver 模式检查
                return os.environ.get('RUN_MAIN') == 'true'
            else:
                logger.info(f"未知的启动模式: {cmdline}")
                return False
        except Exception as e:
            logger.error(f"任务初始化检查失败: {e}")
            return False

    def _check_db_connection(self, max_retries=3, retry_delay=5):
        """
        检查数据库连接并尝试重连
        """
        retries = 0
        while retries < max_retries:
            try:
                connections['default'].ensure_connection()
                logger.info("数据库连接成功")
                return True
            except OperationalError as e:
                retries += 1
                logger.warning(f"数据库连接失败 (尝试 {retries}/{max_retries}): {str(e)}")
                if retries < max_retries:
                    time.sleep(retry_delay)
                connections['default'].close()
        
        logger.error("无法建立数据库连接")
        return False

    def _initialize_background_tasks(self) -> None:
        """
        初始化并启动后台任务
        """
        if self.cleanup_initialized:
            return

        try:
            # 首先检查数据库连接
            if not self._check_db_connection():
                logger.error("由于数据库连接问题，后台任务初始化失败")
                return

            from .tasks import (
                start_background_cleanup,
                start_timeout_checker,
                cleanup_resources,
                start_db_connection_checker  # 新增
            )

            # 创建并启动清理线程
            self.cleanup_thread = self._create_thread(
                start_background_cleanup,
                "BackgroundCleanup"
            )

            # 创建并启动超时检查线程
            self.timeout_thread = self._create_thread(
                start_timeout_checker,
                "TimeoutChecker"
            )

            # 创建并启动数据库连接检查线程
            self.db_checker_thread = self._create_thread(
                start_db_connection_checker,
                "DBConnectionChecker"
            )

            # 启动线程
            self._start_threads()

            # 注册清理函数
            atexit.register(self._cleanup_handler)
            
            logger.info("后台任务初始化完成")

        except Exception as e:
            logger.error(f"初始化后台任务失败: {e}")
            self._cleanup_running_threads()

    def _create_thread(self, target, name: str) -> threading.Thread:
        """
        创建守护线程
        """
        thread = threading.Thread(
            target=target,
            name=name,
            daemon=True
        )
        return thread

    def _start_threads(self) -> None:
        """
        启动所有线程
        """
        try:
            if self.cleanup_thread:
                self.cleanup_thread.start()
                logger.info(f"后台清理线程已启动: {self.cleanup_thread.name}")

            if self.timeout_thread:
                self.timeout_thread.start()
                logger.info(f"超时检查线程已启动: {self.timeout_thread.name}")

            if self.db_checker_thread:
                self.db_checker_thread.start()
                logger.info(f"数据库连接检查线程已启动: {self.db_checker_thread.name}")

            self.cleanup_initialized = True

        except Exception as e:
            logger.error(f"启动线程失败: {e}")
            self._cleanup_running_threads()
            raise

    def _cleanup_handler(self) -> None:
        """
        退出时的资源清理
        """
        try:
            # 确保数据库连接正常
            self._check_db_connection(max_retries=1, retry_delay=1)
            
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # 停止线程标志
                from .tasks import cleanup_running, timeout_checker_running
                cleanup_running = False
                timeout_checker_running = False

                # 等待线程结束
                self._wait_for_threads()

                # 执行资源清理
                loop.run_until_complete(cleanup_resources())

            finally:
                loop.close()

        except Exception as e:
            logger.error(f"清理资源时发生错误: {e}")

        finally:
            # 确保关闭所有数据库连接
            for conn in connections.all():
                conn.close()

    def _wait_for_threads(self, timeout: int = 5) -> None:
        """
        等待线程结束
        """
        try:
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                self.cleanup_thread.join(timeout=timeout)
                if self.cleanup_thread.is_alive():
                    logger.warning("清理线程未能在超时时间内结束")

            if self.timeout_thread and self.timeout_thread.is_alive():
                self.timeout_thread.join(timeout=timeout)
                if self.timeout_thread.is_alive():
                    logger.warning("超时检查线程未能在超时时间内结束")

            if self.db_checker_thread and self.db_checker_thread.is_alive():
                self.db_checker_thread.join(timeout=timeout)
                if self.db_checker_thread.is_alive():
                    logger.warning("数据库连接检查线程未能在超时时间内结束")

        except Exception as e:
            logger.error(f"等待线程结束失败: {e}")

    def _cleanup_running_threads(self) -> None:
        """
        清理正在运行的线程
        """
        try:
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                from .tasks import cleanup_running
                cleanup_running = False
                self.cleanup_thread.join(timeout=1)

            if self.timeout_thread and self.timeout_thread.is_alive():
                from .tasks import timeout_checker_running
                timeout_checker_running = False
                self.timeout_thread.join(timeout=1)

            if self.db_checker_thread and self.db_checker_thread.is_alive():
                from .tasks import db_checker_running
                db_checker_running = False
                self.db_checker_thread.join(timeout=1)

        except Exception as e:
            logger.error(f"清理运行中的线程失败: {e}")