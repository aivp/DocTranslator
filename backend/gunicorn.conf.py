#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gunicorn 配置文件
用于生产环境部署 Flask 应用
"""
import multiprocessing
import os

# ==================== 服务器配置 ====================
bind = "0.0.0.0:5000"  # 监听地址和端口
backlog = 2048  # 等待连接的最大数量

# ==================== 工作进程配置 ====================
# 工作进程数（推荐：CPU核心数 × 2 + 1）
# 例如：8核CPU = 8 × 2 + 1 = 17个进程
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式（sync: 同步，gevent: 异步）
worker_class = "sync"  # 使用同步模式（推荐，稳定可靠）

# 每个进程的线程数（用于处理I/O密集型任务）
threads = 4  # 每个进程4个线程

# 总并发数 = workers × threads
# 例如：17进程 × 4线程 = 68个并发请求

# ==================== 超时配置 ====================
timeout = 300  # 工作进程超时时间（秒），5分钟（支持长时间翻译任务）
keepalive = 5  # Keep-alive连接超时时间（秒）

# ==================== 日志配置 ====================
# Docker环境：输出到stdout/stderr（Docker会收集日志）
accesslog = "-"  # 访问日志输出到stdout
errorlog = "-"   # 错误日志输出到stderr
loglevel = "info"  # 日志级别：debug, info, warning, error, critical

# ==================== 进程管理 ====================
proc_name = "doctranslator"  # 进程名称（ps命令中显示）
daemon = False  # 是否后台运行（Docker中设为False，让Docker管理进程）

# ==================== 优雅重启 ====================
graceful_timeout = 30  # 优雅重启超时时间（秒）
max_requests = 1000  # 每个worker处理的最大请求数（防止内存泄漏）
max_requests_jitter = 50  # 随机抖动，避免所有worker同时重启

# ==================== 性能优化 ====================
preload_app = False  # 是否预加载应用（False：每个worker独立加载，避免共享状态问题）

# ==================== 环境变量 ====================
# 可以通过环境变量覆盖配置
if os.getenv('GUNICORN_WORKERS'):
    workers = int(os.getenv('GUNICORN_WORKERS'))
if os.getenv('GUNICORN_THREADS'):
    threads = int(os.getenv('GUNICORN_THREADS'))
if os.getenv('GUNICORN_TIMEOUT'):
    timeout = int(os.getenv('GUNICORN_TIMEOUT'))

