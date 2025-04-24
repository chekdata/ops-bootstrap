#!/bin/bash

# 创建日志目录
LOG_DIR="/chekkk/code/chekappbackendnew/logs"
mkdir -p $LOG_DIR

# 获取当前日期作为日志文件名
DATE=$(date +"%Y-%m-%d")
LOG_FILE="$LOG_DIR/daphne-$DATE.log"

# 删除30天前的日志文件
find $LOG_DIR -name "daphne-*.log" -type f -mtime +30 -delete

# 启动Daphne服务器，将输出重定向到按日期命名的日志文件
nohup daphne -b 0.0.0.0 -p 8000 myproject.asgi:application > $LOG_FILE 2>&1 &

# 输出进程ID和日志文件位置
echo "Daphne服务器已启动，进程ID: $!"
echo "日志文件: $LOG_FILE"