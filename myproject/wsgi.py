"""
WSGI config for myproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import atexit
import asyncio
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

from common_task.views import shutdown_background_tasks

# 在应用退出时注册后台任务的关闭函数
atexit.register(lambda: asyncio.run(shutdown_background_tasks()))

application = get_wsgi_application()
