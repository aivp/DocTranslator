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

# 内存清理阈值：1.5GB（系统总内存，所有Gunicorn进程的总和）
MEMORY_CLEANUP_THRESHOLD = 1610612736  # 1.5GB (单位：字节)

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

def get_gunicorn_total_memory():
    """
    获取所有Gunicorn进程的总内存使用量（字节）
    用于多进程环境下的系统总内存监控
    
    Returns:
        int: 所有Gunicorn进程的总内存（字节），如果无法获取则返回0
    """
    if not PSUTIL_AVAILABLE:
        logger.debug("psutil不可用，无法获取Gunicorn总内存")
        return 0
    
    try:
        current_process = psutil.Process(os.getpid())
        current_pid = os.getpid()
        total_memory = 0
        found_processes = []
        
        # 方法1：通过父进程查找所有worker进程（最准确）
        try:
            parent = current_process.parent()
            if parent:
                parent_name = parent.name().lower()
                parent_cmdline = ' '.join(parent.cmdline()).lower() if hasattr(parent, 'cmdline') else ''
                
                # 检查是否是Gunicorn master进程（通过进程名或命令行）
                is_gunicorn_master = (
                    'gunicorn' in parent_name or 
                    'gunicorn' in parent_cmdline or
                    'doctranslator' in parent_cmdline
                )
                
                if is_gunicorn_master:
                    # 找到Gunicorn master进程，获取所有子进程
                    children = parent.children(recursive=True)
                    # 包括master进程本身
                    all_processes = [parent] + children
                    
                    for proc in all_processes:
                        try:
                            memory_info = proc.memory_info()
                            total_memory += memory_info.rss
                            found_processes.append({
                                'pid': proc.pid,
                                'name': proc.name(),
                                'memory_mb': memory_info.rss / 1024 / 1024
                            })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # 进程可能已经退出或没有权限，跳过
                            continue
                    
                    if total_memory > 0:
                        total_mb = total_memory / 1024 / 1024
                        logger.debug(f"✅ 方法1成功: 找到{len(found_processes)}个Gunicorn进程，总内存={total_mb:.1f}MB")

                        return total_memory
        except (psutil.NoSuchProcess, AttributeError, psutil.AccessDenied) as e:
            # 父进程不存在或没有权限，尝试方法2
            logger.debug(f"方法1失败: {type(e).__name__}: {e}")
        
        # 方法2：通过进程命令行查找所有Gunicorn进程（更可靠）
        try:
            total_memory = 0
            found_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '').lower()
                    proc_cmdline_list = proc_info.get('cmdline', [])
                    proc_cmdline = ' '.join(proc_cmdline_list).lower() if proc_cmdline_list else ''
                    
                    # 检查是否是Gunicorn进程（通过进程名或命令行）
                    # 更严格的匹配：必须包含gunicorn或wsgi:app
                    is_gunicorn = (
                        'gunicorn' in proc_name or 
                        'gunicorn' in proc_cmdline or
                        ('wsgi:app' in proc_cmdline and ('python' in proc_name or 'python' in proc_cmdline))
                    )
                    
                    if is_gunicorn:
                        memory_info = proc_info.get('memory_info')
                        if memory_info:
                            memory_rss = memory_info.rss
                            total_memory += memory_rss
                            found_processes.append({
                                'pid': proc_info.get('pid'),
                                'name': proc_info.get('name'),
                                'cmdline': proc_cmdline[:100],  # 截断命令行，避免日志过长
                                'memory_mb': memory_rss / 1024 / 1024
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, TypeError):
                    # 进程可能已经退出或没有权限，跳过
                    continue
            
            if total_memory > 0:
                total_mb = total_memory / 1024 / 1024
                logger.debug(f"✅ 方法2成功: 找到{len(found_processes)}个Gunicorn进程，总内存={total_mb:.1f}MB")
                return total_memory
        except Exception as e:
            logger.warning(f"方法2失败: {type(e).__name__}: {e}")
        
        # 方法3：如果都失败，回退到当前进程内存（兼容单进程模式）
        logger.warning(f"⚠️ 无法获取所有Gunicorn进程内存（方法1和2都失败），回退到当前进程内存（PID={current_pid}）")
        single_memory = get_memory_usage()
        if single_memory > 0:
            logger.warning(f"⚠️ 使用单进程模式: 当前进程内存={single_memory / 1024 / 1024:.1f}MB（这可能是开发模式或查找逻辑需要改进）")
        return single_memory
        
    except Exception as e:
        logger.warning(f"获取Gunicorn总内存失败: {type(e).__name__}: {e}")
        # 回退到当前进程内存
        single_memory = get_memory_usage()
        if single_memory > 0:
            logger.warning(f"⚠️ 异常回退: 使用当前进程内存={single_memory / 1024 / 1024:.1f}MB")
        return single_memory

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
    1. 清理应用级缓存（tokenizer、术语库缓存等）
    2. 清理Python内部缓存
    3. 多次垃圾回收
    4. 释放内存到操作系统
    """
    try:
        logger.info("🧹 开始激进内存清理...")
        
        # 1. 清理应用级缓存
        try:
            # 清理 tokenizer 缓存
            try:
                from app.utils.token_counter import _tokenizer_cache
                cache_size = len(_tokenizer_cache)
                _tokenizer_cache.clear()
                logger.info(f"✅ 已清理 tokenizer 缓存 ({cache_size} 个条目)")
            except Exception as e:
                logger.debug(f"清理 tokenizer 缓存失败: {e}")
            
            # 清理术语库倒排索引缓存
            try:
                from app.translate.term_filter import (
                    _inverted_index_cache,
                    _inverted_index_cache_time,
                    _result_cache,
                    _result_cache_time
                )
                index_cache_size = len(_inverted_index_cache)
                result_cache_size = len(_result_cache)
                _inverted_index_cache.clear()
                _inverted_index_cache_time.clear()
                _result_cache.clear()
                _result_cache_time.clear()
                logger.info(f"✅ 已清理术语库缓存 (倒排索引: {index_cache_size} 个, 结果: {result_cache_size} 个)")
            except Exception as e:
                logger.debug(f"清理术语库缓存失败: {e}")
        except Exception as e:
            logger.debug(f"清理应用级缓存时出错: {e}")
        
        # 2. 清理Python内部缓存
        try:
            import sys
            if hasattr(sys, '_clear_type_cache'):
                sys._clear_type_cache()
                logger.info("✅ 已清理Python类型缓存")
        except Exception as e:
            logger.debug(f"清理Python类型缓存失败: {e}")
        
        # 3. 多次强制垃圾回收
        total_collected = 0
        for i in range(5):  # 执行5次垃圾回收
            collected = gc.collect() 
            total_collected += collected
            if collected == 0:
                break  # 如果没有更多对象可回收，提前退出
        
        logger.info(f"垃圾回收释放了 {total_collected} 个对象")
        
        # 4. 强制释放内存到操作系统
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.info("✅ 已调用malloc_trim释放内存到操作系统")
        except Exception as e:
            logger.debug(f"malloc_trim不可用: {e}")
        
        # 5. 检查清理后的系统总内存（所有Gunicorn进程的总和）
        after_memory = get_gunicorn_total_memory()
        if after_memory > 0:
            logger.info(f"✅ 激进内存清理完成，系统总内存: {after_memory / 1024 / 1024:.1f}MB")
        
        return True
    except Exception as e:
        logger.error(f"激进内存清理失败: {e}")
        return False

def check_and_cleanup_memory(config=None):
    """
    检查内存使用情况，并在满足条件时自动清理
    
    注意：使用系统总内存（所有Gunicorn进程的总和）进行判断
    
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
        logger.info("内存清理已禁用")
        return False
    
    # 使用全局阈值
    threshold = MEMORY_CLEANUP_THRESHOLD
    
    # 检查系统总内存使用（所有Gunicorn进程的总和）
    current_memory = get_gunicorn_total_memory()
    
    if current_memory == 0:
        # 无法获取内存信息，跳过清理
        logger.info("无法获取内存信息，跳过清理")
        return False
    
    # 检查清理间隔
    current_time = time.time()
    time_since_last_cleanup = current_time - _last_cleanup_time
    
    # 记录检查信息（即使不清理也记录，方便排查）
    memory_mb = current_memory / 1024 / 1024
    threshold_mb = threshold / 1024 / 1024
    logger.info(f"内存检查: 当前={memory_mb:.1f}MB, 阈值={threshold_mb:.1f}MB, 距上次清理={time_since_last_cleanup:.0f}秒")
    
    # 检查清理间隔
    if time_since_last_cleanup < _cleanup_interval:
        logger.info(f"距离上次清理仅 {time_since_last_cleanup:.0f} 秒，未达到间隔 {_cleanup_interval} 秒，跳过清理")
        return False
    
    if current_memory < threshold:
        logger.info(f"系统总内存 {memory_mb:.1f}MB 低于阈值 {threshold_mb:.1f}MB，无需清理")
        return False
    
    # 检查是否有运行中的任务
    has_tasks = has_running_tasks()
    if has_tasks:
        logger.info(f"系统总内存 {memory_mb:.1f}MB 超过阈值 {threshold_mb:.1f}MB，但有任务在运行，跳过清理")
        return False
    
    # 执行清理
    with _cleanup_lock:
        # 双重检查，防止并发
        if current_time - _last_cleanup_time < _cleanup_interval:
            return False
        
        try:
            logger.info(f"🧹 开始自动内存清理 (系统总内存: {current_memory / 1024 / 1024:.1f}MB, 阈值: {threshold / 1024 / 1024:.1f}MB)")
            
            # 使用激进清理
            aggressive_memory_cleanup()
            
            # 检查清理后的系统总内存（所有Gunicorn进程的总和）
            after_memory = get_gunicorn_total_memory()
            if after_memory > 0:
                released = current_memory - after_memory
                logger.info(f"✅ 内存清理完成 (释放: {released / 1024 / 1024:.1f}MB, 系统总内存: {after_memory / 1024 / 1024:.1f}MB)")
            
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
                logger.info("⏰ 定期内存检查任务触发（每10分钟检查一次）")
                result = check_and_cleanup_memory()
                if not result:
                    # 即使没有清理，也记录检查结果（使用info级别，方便排查）
                    current_memory = get_gunicorn_total_memory()
                    if current_memory > 0:
                        memory_mb = current_memory / 1024 / 1024
                        threshold_mb = MEMORY_CLEANUP_THRESHOLD / 1024 / 1024
                        has_tasks = has_running_tasks()
                        time_since_last = time.time() - _last_cleanup_time
                        logger.info(f"📊 定期内存检查: 系统总内存={memory_mb:.1f}MB, 阈值={threshold_mb:.1f}MB, 有任务运行={has_tasks}, 距上次清理={time_since_last:.0f}秒")
            except Exception as e:
                logger.error(f"定期内存清理失败: {e}", exc_info=True)
                time.sleep(60)  # 出错后等待1分钟再重试
    
    # 启动后台线程
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info("✅ 定期内存清理任务已启动（每10分钟检查一次）")
