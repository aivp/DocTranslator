#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存管理工具
用于监控和自动清理内存
"""

import os
import gc
import ctypes
import logging
import threading
from flask import current_app

logger = logging.getLogger(__name__)

# 尝试导入psutil，如果失败则使用备用方案
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError as e:
    PSUTIL_AVAILABLE = False
    logger.warning(f"psutil模块未安装: {e}，将使用备用内存监控方案")
except Exception as e:
    PSUTIL_AVAILABLE = False
    logger.warning(f"psutil模块导入失败: {e}，将使用备用内存监控方案")

# 全局锁，防止并发执行内存清理
_cleanup_lock = threading.Lock()
_last_cleanup_time = 0
_cleanup_interval = 300  # 5分钟内最多清理一次

def get_memory_usage():
    """获取当前进程的内存使用量（字节）"""
    if not PSUTIL_AVAILABLE:
        # psutil不可用时，使用备用方案：返回0表示无法获取
        logger.debug("psutil不可用，无法获取内存使用量")
        return 0
    
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss
    except psutil.AccessDenied as e:
        logger.warning(f"获取内存使用量失败：权限不足 ({e})")
        return 0
    except psutil.NoSuchProcess as e:
        logger.warning(f"获取内存使用量失败：进程不存在 ({e})")
        return 0
    except Exception as e:
        logger.warning(f"获取内存使用量失败：{type(e).__name__}: {e}")
        return 0

def force_memory_release():
    """强制释放内存到操作系统"""
    try:
        gc.collect()
        # 尝试调用glibc的malloc_trim释放未使用的内存
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.info("🧹 已调用malloc_trim释放内存")
        except Exception as e:
            logger.debug(f"malloc_trim不可用: {e}")
        return True
    except Exception as e:
        logger.warning(f"强制释放内存失败: {e}")
        return False

def check_and_cleanup_memory(config):
    """
    检查内存使用情况，并在满足条件时自动清理
    
    Args:
        config: Flask应用配置对象
    
    Returns:
        bool: 是否执行了清理
    """
    global _last_cleanup_time
    
    # 检查是否启用自动清理
    if not config.get('MEMORY_CLEANUP_ENABLED', True):
        return False
    
    # 检查清理间隔
    import time
    current_time = time.time()
    if current_time - _last_cleanup_time < _cleanup_interval:
        return False
    
    # 获取阈值
    threshold = config.get('MEMORY_CLEANUP_THRESHOLD', 1073741824)  # 默认1GB
    
    # 检查当前内存使用
    current_memory = get_memory_usage()
    
    if current_memory < threshold:
        return False
    
    # 检查是否有运行中的任务
    if has_running_tasks():
        logger.info(f"内存使用 {current_memory / 1024 / 1024:.1f}MB 超过阈值 {threshold / 1024 / 1024:.1f}MB，但有任务在运行，跳过清理")
        return False
    
    # 执行清理
    with _cleanup_lock:
        # 双重检查，防止并发
        if current_time - _last_cleanup_time < _cleanup_interval:
            return False
        
        try:
            logger.info(f"🧹 开始自动内存清理 (当前: {current_memory / 1024 / 1024:.1f}MB, 阈值: {threshold / 1024 / 1024:.1f}MB)")
            
            # 强制垃圾回收
            collected = gc.collect()
            logger.info(f"垃圾回收释放 {collected} 个对象")
            
            # 强制释放内存到操作系统
            force_memory_release()
            
            # 检查清理后的内存
            after_memory = get_memory_usage()
            released = current_memory - after_memory
            
            _last_cleanup_time = current_time
            
            logger.info(f"✅ 内存清理完成 (释放: {released / 1024 / 1024:.1f}MB, 当前: {after_memory / 1024 / 1024:.1f}MB)")
            
            return True
            
        except Exception as e:
            logger.error(f"内存清理失败: {e}")
            return False

def has_running_tasks():
    """检查是否有正在运行的翻译任务"""
    try:
        from app.utils.task_manager import is_any_task_running
        return is_any_task_running()
    except Exception as e:
        logger.debug(f"检查运行任务失败: {e}")
        # 如果检查失败，假设有任务在运行，保守处理
        return True

def setup_memory_monitor(app):
    """设置内存监控器"""
    
    @app.before_request
    def check_memory():
        """在每个请求前检查内存"""
        try:
            check_and_cleanup_memory(app.config)
        except Exception as e:
            logger.debug(f"内存检查失败: {e}")

