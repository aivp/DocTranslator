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
import time
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

# 降低内存清理阈值，从1GB降到500MB，更积极地清理内存
MEMORY_CLEANUP_THRESHOLD = 524288000  # 500MB (单位：字节)

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
        # 多次调用gc.collect()，确保彻底清理
        collected = 0
        for i in range(3):  # 执行3次垃圾回收
            collected += gc.collect()
        
        logger.debug(f"垃圾回收释放了 {collected} 个对象")
        
        # 尝试调用glibc的malloc_trim释放未使用的内存
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.debug("🧹 已调用malloc_trim释放内存")
        except Exception as e:
            logger.debug(f"malloc_trim不可用: {e}")
        return True
    except Exception as e:
        logger.warning(f"强制释放内存失败: {e}")
        return False

def aggressive_memory_cleanup():
    """
    激进的内存清理：清理所有可能的缓存和引用
    
    包括：
    1. 多次垃圾回收
    2. 清理Python内部缓存
    3. 释放内存到操作系统
    """
    try:
        logger.info("🧹 开始激进内存清理...")
        
        # 1. 清理Python内部缓存
        import sys
        # 清理模块缓存（谨慎使用，可能影响性能）
        # sys.modules 不应该清理，但可以清理一些大对象
        
        # 2. 多次强制垃圾回收
        total_collected = 0
        for i in range(5):  # 执行5次垃圾回收
            collected = gc.collect()
            total_collected += collected
            if collected == 0:
                break  # 如果没有更多对象可回收，提前退出
        
        logger.info(f"垃圾回收释放了 {total_collected} 个对象")
        
        # 3. 强制释放内存到操作系统
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.info("✅ 已调用malloc_trim释放内存到操作系统")
        except Exception as e:
            logger.debug(f"malloc_trim不可用: {e}")
        
        # 4. 检查清理后的内存
        after_memory = get_memory_usage()
        if after_memory > 0:
            logger.info(f"✅ 激进内存清理完成，当前内存: {after_memory / 1024 / 1024:.1f}MB")
        
        return True
    except Exception as e:
        logger.error(f"激进内存清理失败: {e}")
        return False

def check_and_cleanup_memory(config=None):
    """
    检查内存使用情况，并在满足条件时自动清理
    
    Args:
        config: Flask应用配置对象（已废弃，保留参数以兼容旧代码）
    
    Returns:
        bool: 是否执行了清理
    """
    global _last_cleanup_time
    
    # 硬编码配置：始终启用
    MEMORY_CLEANUP_ENABLED = True
    
    # 检查是否启用自动清理
    if not MEMORY_CLEANUP_ENABLED:
        return False
    
    # 检查清理间隔
    current_time = time.time()
    if current_time - _last_cleanup_time < _cleanup_interval:
        return False
    
    # 使用全局阈值
    threshold = MEMORY_CLEANUP_THRESHOLD
    
    # 检查当前内存使用
    current_memory = get_memory_usage()
    
    if current_memory == 0:
        # 无法获取内存信息，跳过清理
        return False
    
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
            
            # 使用激进清理
            aggressive_memory_cleanup()
            
            # 检查清理后的内存
            after_memory = get_memory_usage()
            if after_memory > 0:
                released = current_memory - after_memory
                logger.info(f"✅ 内存清理完成 (释放: {released / 1024 / 1024:.1f}MB, 当前: {after_memory / 1024 / 1024:.1f}MB)")
            
            _last_cleanup_time = current_time
            
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

def setup_periodic_cleanup(app):
    """
    设置定期内存清理任务
    
    即使没有请求，也会定期检查并清理内存
    """
    def periodic_cleanup():
        """定期清理内存的后台任务"""
        while True:
            try:
                time.sleep(600)  # 每10分钟检查一次
                check_and_cleanup_memory()
            except Exception as e:
                logger.error(f"定期内存清理失败: {e}")
                time.sleep(60)  # 出错后等待1分钟再重试
    
    # 启动后台线程
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info("✅ 定期内存清理任务已启动（每10分钟检查一次）")
