#!/bin/bash

# 获取所有相关的daphne进程
pids=$(ps aux | grep "daphne -b 0.0.0.0 -p 8000" | grep -v grep | awk '{print $2}')

if [ -n "$pids" ]; then
    echo "找到以下 daphne 进程:"
    ps aux | grep "daphne -b 0.0.0.0 -p 8000" | grep -v grep
    
    # 先尝试正常终止
    for pid in $pids; do
        echo "尝试终止进程 PID: $pid"
        kill $pid
    done
    
    # 等待2秒看进程是否结束
    sleep 2
    
    # 检查是否还有残留进程
    remaining_pids=$(ps aux | grep "daphne -b 0.0.0.0 -p 8000" | grep -v grep | awk '{print $2}')
    if [ -n "$remaining_pids" ]; then
        echo "仍有残留进程，使用强制终止:"
        for pid in $remaining_pids; do
            echo "强制终止进程 PID: $pid"
            kill -9 $pid
        done
    fi
    
    # 最后确认
    if ps aux | grep "daphne -b 0.0.0.0 -p 8000" | grep -v grep > /dev/null; then
        echo "警告: 仍有daphne进程无法终止"
    else
        echo "所有daphne进程已成功终止"
    fi
else
    echo "未找到运行中的 daphne 进程"
fi