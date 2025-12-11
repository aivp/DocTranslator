# -*- coding: utf-8 -*-
"""
队列管理器 - 智能任务调度
根据系统资源（任务数和内存使用）智能调度翻译任务
支持多进程环境：使用文件锁确保只有一个进程运行队列管理器
"""
import threading
import time
import logging
import os
import fcntl
from typing import Dict, Tuple
from flask import current_app
from pathlib import Path

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self):
        self.max_concurrent_tasks = 12  # 最大并发任务数（从10增加到12，提升20%并发能力）
        self.max_memory_gb = 16  # 最大内存占用(GB)（从10GB增加到16GB，预留2GB安全余量）
        self.critical_memory_gb = 12  # 临界内存阈值(GB) - 超过此值开始积极清理（从8GB增加到12GB）
        self.emergency_memory_gb = 14  # 紧急内存阈值(GB) - 超过此值动态暂停任务（从12GB增加到14GB）
        self.task_pause_duration = 30  # 任务暂停时长(秒) - 增加到30秒
        self.emergency_pause_active = False  # 紧急暂停状态标志
        self.emergency_start_time = None  # 紧急保护开始时间
        self.emergency_timeout_minutes = 5  # 紧急保护超时时间(分钟)
        self.memory_release_check_minutes = 2  # 内存释放检查时间(分钟)
        self.max_pdf_tasks = 2  # 最大PDF翻译任务数（已废弃，使用下面的分别限制）
        self.max_large_pdf_tasks = 2  # 最大大PDF翻译任务数（从1增加到2，超过25页）
        self.max_small_pdf_tasks = 4  # 最大小PDF翻译任务数（从3增加到4，25页以内）
        self.large_pdf_page_threshold = 25  # 大PDF页数阈值
        self.queue_lock = threading.Lock()
        self.monitor_thread = None
        self.running = False
        self._app = None  # 缓存应用实例
        self._lock_file = None  # 文件锁
        self._lock_file_handle = None  # 文件锁句柄
        
    def set_app(self, app):
        """设置应用实例（由主应用调用）"""
        self._app = app
        
    def _get_app(self):
        """获取应用实例"""
        if self._app is None:
            # 如果还没有设置应用实例，尝试从当前上下文获取
            try:
                from flask import current_app
                return current_app._get_current_object()
            except RuntimeError:
                # 如果没有应用上下文，创建一个新的（但这是最后的选择）
                from app import create_app
                return create_app()
        return self._app
        
    def start_monitor(self):
        """启动队列监控线程（多进程安全：使用文件锁确保只有一个进程运行）"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.info("队列监控线程已在运行")
            return
        
        # 尝试获取文件锁（确保只有一个进程运行队列管理器）
        if not self._acquire_lock():
            logger.info("文件翻译队列管理器已在其他进程中运行，跳过启动")
            return
            
        self.running = True
        # 延迟启动监控线程，确保Flask应用上下文已完全初始化
        def delayed_start():
            import time
            time.sleep(3)  # 等待3秒让Flask应用完全初始化
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("队列监控线程已启动（已获取进程锁）")
        
        # 在单独的线程中延迟启动
        threading.Thread(target=delayed_start, daemon=True).start()
        logger.info("队列监控线程启动中...")
        
    def stop_monitor(self):
        """停止队列监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self._release_lock()
        logger.info("队列监控线程已停止")
    
    def _acquire_lock(self):
        """获取文件锁（确保只有一个进程运行队列管理器，支持健康检查）"""
        try:
            # 创建锁文件路径
            lock_file_path = Path('/tmp/file_translate_queue_manager.lock')
            
            # 检查锁文件是否存在且进程是否存活
            if lock_file_path.exists():
                try:
                    # 读取锁文件中的进程ID
                    with open(lock_file_path, 'r') as f:
                        pid_str = f.read().strip()
                        if pid_str.isdigit():
                            pid = int(pid_str)
                            # 检查进程是否存活
                            try:
                                os.kill(pid, 0)  # 发送信号0检查进程是否存在
                            except OSError:
                                # 进程不存在，清理僵尸锁文件
                                logger.warning(f"发现僵尸锁文件（进程 {pid} 不存在），清理锁文件")
                                try:
                                    lock_file_path.unlink()
                                except:
                                    pass
                except Exception as e:
                    logger.debug(f"检查锁文件时出错（可能正常）: {e}")
            
            # 打开锁文件（如果不存在则创建）
            self._lock_file_handle = open(lock_file_path, 'w')
            
            # 尝试获取非阻塞排他锁
            fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # 写入进程ID和时间戳
            import time
            lock_info = f"{os.getpid()}\n{time.time()}\n"
            self._lock_file_handle.write(lock_info)
            self._lock_file_handle.flush()
            
            self._lock_file = lock_file_path
            logger.info(f"成功获取队列管理器文件锁（进程ID: {os.getpid()}）")
            return True
            
        except (IOError, OSError) as e:
            # 无法获取锁（其他进程正在运行）
            if self._lock_file_handle:
                try:
                    self._lock_file_handle.close()
                except:
                    pass
                self._lock_file_handle = None
            return False
        except Exception as e:
            logger.error(f"获取文件锁失败: {str(e)}")
            if self._lock_file_handle:
                try:
                    self._lock_file_handle.close()
                except:
                    pass
                self._lock_file_handle = None
            return False
    
    def _check_lock_validity(self):
        """检查文件锁是否仍然有效"""
        try:
            if not self._lock_file_handle:
                return False
            
            # 检查文件句柄是否仍然有效
            try:
                os.fstat(self._lock_file_handle.fileno())
                return True
            except OSError:
                return False
        except Exception as e:
            logger.debug(f"检查锁有效性时出错: {e}")
            return False
    
    def _release_lock(self):
        """释放文件锁"""
        try:
            if self._lock_file_handle:
                try:
                    fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_UN)
                except:
                    pass
                try:
                    self._lock_file_handle.close()
                except:
                    pass
                self._lock_file_handle = None
            
            if self._lock_file and self._lock_file.exists():
                try:
                    self._lock_file.unlink()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"释放文件锁失败: {str(e)}")
    
    def _monitor_loop(self):
        """队列监控循环（多进程优化版本）"""
        logger.info("队列监控循环已启动（多进程优化模式）")
        error_count = 0
        max_errors = 10  # 最多连续错误10次
        
        while self.running:
            try:
                # 检查文件锁是否仍然有效
                if not self._check_lock_validity():
                    logger.warning("文件锁已失效，队列管理器可能在其他进程中运行")
                    self.running = False
                    break
                
                self._process_queue()
                error_count = 0  # 重置错误计数
                time.sleep(2)  # 每2秒检查一次
                
            except Exception as e:
                error_count += 1
                logger.error(f"队列监控异常 ({error_count}/{max_errors}): {e}", exc_info=True)
                
                if error_count >= max_errors:
                    logger.critical(f"队列监控连续错误 {max_errors} 次，停止监控")
                    self.running = False
                    break
                
                # 错误后等待更长时间再重试
                time.sleep(min(5 * error_count, 30))  # 最多等待30秒
    
    def _process_queue(self):
        """处理队列中的任务（多进程安全）
        
        注意：
        1. 文件锁确保只有一个进程运行队列管理器
        2. 线程锁确保单进程内不会并发处理队列
        3. 数据库使用 SKIP LOCKED 避免行锁等待
        4. 所有事务都尽可能短，避免长时间持有锁
        """
        with self.queue_lock:  # 线程锁：确保单进程内不会并发（文件锁已保证只有一个进程运行）
            try:
                # 检查当前资源状态
                current_tasks = self._get_current_running_tasks()
                memory_gb = self._get_memory_usage_gb()
                
                logger.debug(f"资源检查: 运行任务={current_tasks}, 系统总内存={memory_gb:.2f}GB")
                
                # 如果当前没有任务但内存超限，进行内存释放
                if current_tasks == 0 and memory_gb >= self.max_memory_gb:
                    logger.info(f"当前无运行任务但内存超限({memory_gb:.2f}GB >= {self.max_memory_gb}GB)，开始内存释放")
                    self._force_memory_cleanup()
                    # 释放后重新检查内存
                    memory_gb = self._get_memory_usage_gb()
                    logger.info(f"内存释放完成，系统总内存: {memory_gb:.2f}GB")
                
                # 如果内存使用率很高（超过临界值），安全进行清理
                elif memory_gb >= self.critical_memory_gb:
                    if current_tasks <= 1:
                        logger.info(f"系统总内存使用率较高({memory_gb:.2f}GB >= {self.critical_memory_gb}GB)，当前任务很少({current_tasks}个)，进行安全内存清理")
                        self._force_memory_cleanup()
                        # 释放后重新检查内存
                        memory_gb = self._get_memory_usage_gb()
                        logger.info(f"安全内存清理完成，系统总内存: {memory_gb:.2f}GB")
                    else:
                        logger.warning(f"系统总内存使用率较高({memory_gb:.2f}GB >= {self.critical_memory_gb}GB)，当前有{current_tasks}个任务运行中，暂停启动新任务保护现有任务")
                        return  # 暂停启动新任务，保护正在运行的任务
                
                # 如果内存使用率极高（超过紧急阈值），动态暂停任务
                elif memory_gb >= self.emergency_memory_gb:
                    if not self.emergency_pause_active:
                        logger.critical(f"🚨 系统总内存使用率极高({memory_gb:.2f}GB >= {self.emergency_memory_gb}GB)，启动紧急保护机制")
                        self.emergency_pause_active = True
                        self.emergency_start_time = time.time()
                        self._emergency_pause_tasks(current_tasks)
                    else:
                        # 检查是否超时
                        elapsed_minutes = (time.time() - self.emergency_start_time) / 60
                        if elapsed_minutes >= self.emergency_timeout_minutes:
                            logger.critical(f"🚨 紧急保护超时({elapsed_minutes:.1f}分钟)，强制恢复所有任务")
                            self._force_resume_all_tasks()
                            self.emergency_pause_active = False
                            self.emergency_start_time = None
                        else:
                            logger.critical(f"🚨 紧急保护机制已激活({elapsed_minutes:.1f}分钟)，系统总内存仍高({memory_gb:.2f}GB)，继续暂停任务")
                            self._emergency_pause_tasks(current_tasks)
                
                # 如果内存降到安全水平，停止紧急保护
                elif memory_gb < self.emergency_memory_gb and self.emergency_pause_active:
                    elapsed_minutes = (time.time() - self.emergency_start_time) / 60 if self.emergency_start_time else 0
                    logger.info(f"✅ 系统总内存已降到安全水平({memory_gb:.2f}GB < {self.emergency_memory_gb}GB)，停止紧急保护机制(持续{elapsed_minutes:.1f}分钟)")
                    self.emergency_pause_active = False
                    self.emergency_start_time = None
                
                # 如果资源充足，启动队列中的任务（一次可以启动多个）
                if current_tasks < self.max_concurrent_tasks and memory_gb < self.max_memory_gb:
                    # 计算可以启动的任务数
                    available_slots = self.max_concurrent_tasks - current_tasks
                    # 一次最多启动5个任务，避免一次性启动太多导致资源紧张
                    max_start_per_cycle = min(5, available_slots)
                    
                    # 循环启动任务，直到没有可用资源或没有符合条件的任务
                    started_count = 0
                    consecutive_failures = 0  # 连续失败计数
                    max_consecutive_failures = 3  # 最多连续失败3次后退出
                    
                    while started_count < max_start_per_cycle:
                        # 快速检查资源（避免每次都查询数据库）
                        if current_tasks >= self.max_concurrent_tasks or memory_gb >= self.max_memory_gb:
                            break
                        
                        # 尝试启动一个任务
                        task_started = self._start_next_task()
                        if task_started:
                            started_count += 1
                            consecutive_failures = 0  # 重置失败计数
                            # 更新当前任务数（避免重复查询）
                            current_tasks += 1
                            # 短暂延迟，避免数据库连接竞争和CPU占用过高
                            time.sleep(0.05)  # 减少延迟时间，提高启动速度
                        else:
                            consecutive_failures += 1
                            if consecutive_failures >= max_consecutive_failures:
                                # 连续失败多次，可能没有符合条件的任务，退出循环
                                logger.debug(f"连续 {consecutive_failures} 次启动失败，退出启动循环")
                                break
                            # 短暂延迟后重试
                            time.sleep(0.1)
                    
                    if started_count > 0:
                        logger.info(f"✅ 本次循环启动了 {started_count} 个任务（当前运行: {current_tasks + started_count}/{self.max_concurrent_tasks}）")
                    
            except Exception as e:
                logger.error(f"处理队列时出错: {e}")
    
    def _get_current_running_tasks(self) -> int:
        """获取当前运行的任务数（使用数据库状态，支持多进程环境）"""
        try:
            from app.models.translate import Translate
            
            # 获取应用实例并创建上下文
            app = self._get_app()
            
            # 在应用上下文中执行数据库操作
            with app.app_context():
                # 使用数据库状态查询，而不是进程内字典，以支持多进程环境
                # 查询所有状态为 process 或 changing 的任务（这些是正在运行的任务）
                running_count = Translate.query.filter(
                    Translate.status.in_(['process', 'changing']),
                    Translate.deleted_flag == 'N'
                ).count()
                
                return running_count
        except Exception as e:
            logger.error(f"获取运行任务数失败: {e}")
            # 出错时回退到进程内方法（虽然不准确，但至少不会崩溃）
            try:
                from app.utils.task_manager import get_running_tasks
                return len(get_running_tasks())
            except:
                return 0
    
    def _get_memory_usage_gb(self) -> float:
        """
        获取系统总内存使用量(GB) - 所有Gunicorn进程的总和
        用于多进程环境下的系统级内存监控
        """
        try:
            from app.utils.memory_manager import get_gunicorn_total_memory
            
            # 获取所有Gunicorn进程的总内存使用量（字节）
            memory_bytes = get_gunicorn_total_memory()
            if memory_bytes == 0:
                # 内存监控不可用，返回0但不报错（避免日志污染）
                return 0.0
            return memory_bytes / (1024**3)  # 转换为GB
        except Exception as e:
            # 使用debug级别，避免频繁的警告日志
            logger.debug(f"获取系统总内存使用量失败: {type(e).__name__}: {e}")
            return 0.0
    
    def _is_large_pdf(self, file_path):
        """判断PDF是否为大PDF（超过阈值页数）
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: True表示大PDF，False表示小PDF（默认）
        """
        try:
            import os
            import fitz
            
            if not file_path or not os.path.exists(file_path):
                return False  # 文件不存在，默认当作小PDF
            
            # 打开PDF检查页数
            doc = fitz.open(file_path)
            page_count = doc.page_count
            doc.close()
            
            is_large = page_count > self.large_pdf_page_threshold
            logger.debug(f"PDF {os.path.basename(file_path)} 页数: {page_count}, 是否大PDF: {is_large}")
            return is_large
            
        except Exception as e:
            logger.warning(f"判断PDF大小失败: {e}，默认当作小PDF")
            return False  # 出错时默认当作小PDF
    
    def _get_current_pdf_tasks(self):
        """获取当前运行的PDF翻译任务数量（返回大PDF和小PDF的任务数）"""
        try:
            from app.models.translate import Translate
            
            # 获取应用实例并创建上下文
            app = self._get_app()
            
            # 在应用上下文中执行数据库操作
            with app.app_context():
                # 获取所有正在运行的PDF任务
                pdf_tasks = Translate.query.filter(
                    Translate.status.in_(['process', 'changing']),
                    Translate.deleted_flag == 'N',
                    Translate.origin_filepath.like('%.pdf')
                ).all()
                
                # 分别统计大PDF和小PDF
                large_pdf_count = 0
                small_pdf_count = 0
                
                for task in pdf_tasks:
                    if self._is_large_pdf(task.origin_filepath):
                        large_pdf_count += 1
                    else:
                        small_pdf_count += 1
                
                return {
                    'total': len(pdf_tasks),
                    'large': large_pdf_count,
                    'small': small_pdf_count
                }
                
        except Exception as e:
            logger.error(f"获取PDF任务数量失败: {e}")
            return {'total': 0, 'large': 0, 'small': 0}
    
    def _force_memory_cleanup(self):
        """强制内存清理 - 安全模式，不伤害运行中的任务"""
        try:
            import gc
            import ctypes
            
            logger.info("🧹 开始安全内存清理...")
            
            # 记录清理前的内存
            before_memory = self._get_memory_usage_gb()
            
            # 安全的内存清理策略
            self._safe_memory_cleanup()
            
            # 记录清理后的内存
            after_memory = self._get_memory_usage_gb()
            released = before_memory - after_memory
            
            logger.info(f"✅ 安全内存清理完成 (释放: {released:.2f}GB, 系统总内存: {after_memory:.2f}GB)")
            
        except Exception as e:
            logger.error(f"安全内存清理失败: {e}")
    
    def _safe_memory_cleanup(self):
        """安全的内存清理 - 只清理垃圾，不伤害运行中的任务"""
        try:
            import gc
            
            # 1. 温和的垃圾回收 - 只清理已释放的对象
            logger.info("执行温和垃圾回收...")
            collected = gc.collect()
            logger.info(f"温和垃圾回收释放 {collected} 个对象")
            
            # 2. 清理Python内部缓存 - 这些不会影响运行中的任务
            try:
                import sys
                # 清理类型缓存 - 只清理未使用的类型信息
                if hasattr(sys, '_clear_type_cache'):
                    sys._clear_type_cache()
                    logger.info("已清理Python类型缓存")
            except Exception as e:
                logger.debug(f"清理类型缓存失败: {e}")
            
            # 3. 系统级内存释放 - 只释放已归还给操作系统的内存
            try:
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                # malloc_trim(0) 只释放已归还的内存，不会影响正在使用的内存
                libc.malloc_trim(0)
                logger.info("已调用malloc_trim释放系统内存")
            except Exception as e:
                logger.debug(f"malloc_trim不可用: {e}")
            
            # 4. 清理模块缓存 - 只清理未使用的模块
            try:
                import sys
                # 清理模块缓存中的未使用模块
                modules_to_remove = []
                for module_name, module in sys.modules.items():
                    # 只清理非核心模块且引用计数为1的模块
                    if (not module_name.startswith('__') and 
                        not module_name.startswith('app.') and  # 保护应用模块
                        hasattr(module, '__file__') and 
                        module.__file__ and
                        'site-packages' in module.__file__):  # 只清理第三方包
                        modules_to_remove.append(module_name)
                
                for module_name in modules_to_remove[:10]:  # 限制清理数量，避免过度清理
                    try:
                        del sys.modules[module_name]
                    except:
                        pass
                
                if modules_to_remove:
                    logger.info(f"已清理 {min(len(modules_to_remove), 10)} 个未使用的第三方模块")
                    
            except Exception as e:
                logger.debug(f"清理模块缓存失败: {e}")
            
        except Exception as e:
            logger.error(f"安全内存清理过程中出错: {e}")
    
    def _emergency_pause_tasks(self, current_tasks):
        """紧急内存保护 - 根据当前任务数量动态暂停任务"""
        try:
            import random
            import threading
            import time
            
            # 获取当前运行的任务
            from app.utils.task_manager import get_running_tasks
            running_tasks = get_running_tasks()
            
            if not running_tasks:
                logger.warning("🚨 紧急保护机制：没有运行中的任务可以暂停")
                return
            
            # 暂停所有当前运行的任务
            pause_count = len(running_tasks)  # 暂停所有任务
            
            # 确保暂停数量不超过可用任务数
            pause_count = min(pause_count, len(running_tasks))
            
            logger.critical(f"🚨 紧急保护机制：当前{current_tasks}个任务，将暂停{pause_count}个任务")
            
            # 随机选择要暂停的任务
            tasks_to_pause = random.sample(running_tasks, pause_count)
            
            # 在后台线程中执行暂停和恢复
            def pause_and_resume():
                try:
                    from app.utils.task_manager import pause_task, resume_task
                    
                    # 暂停选中的任务
                    paused_tasks = []
                    for task_info in tasks_to_pause:
                        task_id = task_info.get('task_id')
                        if task_id and pause_task(task_id):
                            paused_tasks.append(task_id)
                            logger.info(f"✅ 任务 {task_id} 已暂停")
                        else:
                            logger.warning(f"⚠️ 任务 {task_id} 暂停失败")
                    
                    if not paused_tasks:
                        logger.warning("⚠️ 没有任务成功暂停")
                        return
                    
                    # 暂停任务后立即进行内存释放
                    logger.info(f"🧹 暂停{pause_count}个任务后，立即进行内存释放...")
                    self._safe_memory_cleanup()
                    
                    # 检查内存释放效果
                    current_memory_gb = self._get_memory_usage_gb()
                    logger.info(f"📊 内存释放后状态: 系统总内存 {current_memory_gb:.2f}GB")
                    
                    # 如果内存仍然很高，进行额外的安全清理
                    if current_memory_gb >= self.emergency_memory_gb:
                        logger.warning(f"⚠️ 系统总内存仍然很高({current_memory_gb:.2f}GB)，进行额外安全清理")
                        self._release_non_task_memory()
                        current_memory_gb = self._get_memory_usage_gb()
                        logger.info(f"📊 额外清理后系统总内存状态: {current_memory_gb:.2f}GB")
                    
                    # 立即恢复暂停的任务
                    for task_id in paused_tasks:
                        if resume_task(task_id):
                            logger.info(f"✅ 任务 {task_id} 已恢复")
                        else:
                            logger.warning(f"⚠️ 任务 {task_id} 恢复失败")
                    
                    logger.info(f"🔄 紧急保护机制完成，已恢复{pause_count}个任务，最终内存: {current_memory_gb:.2f}GB")
                        
                except Exception as e:
                    logger.error(f"🚨 紧急保护机制执行失败: {e}")
            
            # 在后台线程中执行暂停和恢复
            pause_thread = threading.Thread(target=pause_and_resume, daemon=True)
            pause_thread.start()
            
        except Exception as e:
            logger.error(f"🚨 紧急保护机制初始化失败: {e}")
    
    def _release_non_task_memory(self):
        """释放任务外的内存资源"""
        try:
            logger.info("🧹 开始释放任务外内存资源...")
            
            # 1. 强制垃圾回收
            import gc
            collected = gc.collect()
            logger.info(f"垃圾回收释放 {collected} 个对象")
            
            # 2. 清理系统缓存
            import sys
            sys._clear_type_cache()
            logger.info("已清理类型缓存")
            
            # 3. 释放C库内存
            try:
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
                logger.info("已释放C库内存")
            except Exception as e:
                logger.debug(f"释放C库内存失败: {e}")
            
            # 4. 清理未使用的模块
            try:
                import sys
                modules_to_remove = []
                for module_name, module in sys.modules.items():
                    if (module_name.startswith('_') or 
                        module_name.startswith('pkg_resources') or
                        module_name.startswith('setuptools') or
                        module_name.startswith('distutils')):
                        modules_to_remove.append(module_name)
                
                for module_name in modules_to_remove[:20]:  # 限制清理数量
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                
                logger.info(f"已清理 {len(modules_to_remove[:20])} 个未使用的模块")
            except Exception as e:
                logger.debug(f"清理模块失败: {e}")
            
            # 5. 检查释放后的内存
            after_memory_gb = self._get_memory_usage_gb()
            logger.info(f"🧹 任务外内存释放完成，系统总内存: {after_memory_gb:.2f}GB")
            
        except Exception as e:
            logger.error(f"释放任务外内存失败: {e}")
    
    def _force_resume_all_tasks(self):
        """强制恢复所有暂停的任务"""
        try:
            from app.utils.task_manager import get_running_tasks, resume_task
            
            running_tasks = get_running_tasks()
            resumed_count = 0
            
            for task_info in running_tasks:
                task_id = task_info.get('task_id')
                if task_id and resume_task(task_id):
                    resumed_count += 1
                    logger.info(f"✅ 强制恢复任务 {task_id}")
            
            logger.critical(f"🚨 强制恢复完成，共恢复 {resumed_count} 个任务")
            
        except Exception as e:
            logger.error(f"强制恢复任务失败: {e}")
    
    def _start_next_task(self):
        """启动下一个队列中的任务 - 智能调度（多进程优化版本）
        
        Returns:
            bool: 是否成功启动了任务
        """
        try:
            from app.models.translate import Translate
            from app.resources.task.translate_service import TranslateEngine
            from app.extensions import db
            from sqlalchemy import text
            from datetime import datetime
            import pytz
            
            # 获取应用实例并创建上下文（解决线程上下文问题）
            app = self._get_app()
            
            with app.app_context():
                # 快速检查：如果任务数已满，直接返回（避免不必要的数据库查询）
                current_tasks = self._get_current_running_tasks()
                if current_tasks >= self.max_concurrent_tasks:
                    logger.debug(f"当前任务数已满({current_tasks}/{self.max_concurrent_tasks})，跳过启动新任务")
                    return False
                
                # 使用单个事务完成：查询+更新+启动
                # 这样可以减少数据库往返次数，提高多进程环境下的性能
                start_time = datetime.now(pytz.timezone(app.config.get('TIMEZONE', 'Asia/Shanghai')))
                
                # 使用 SELECT FOR UPDATE SKIP LOCKED 原子获取并锁定任务
                # SKIP LOCKED 确保：如果行被其他进程锁定，会跳过而不是等待，避免死锁
                # 一次只获取1个任务，减少多进程竞争和锁持有时间
                query = text("""
                    SELECT id, origin_filepath FROM translate
                    WHERE status = 'queued'
                      AND deleted_flag = 'N'
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """)
                
                result = db.session.execute(query)
                task_row = result.fetchone()
                
                if not task_row:
                    logger.debug("队列中没有等待的任务")
                    return False
                
                task_id, origin_filepath = task_row[0], task_row[1]
                
                # 快速检查PDF任务限制（在事务外检查，避免长时间持有行锁）
                # 注意：这里检查可能不准确（因为其他进程可能同时启动任务），
                # 但可以避免大部分无效更新，最终通过UPDATE的WHERE条件保证原子性
                if origin_filepath and origin_filepath.lower().endswith('.pdf'):
                    current_pdf_tasks = self._get_current_pdf_tasks()
                    is_large_pdf = self._is_large_pdf(origin_filepath)
                    
                    if is_large_pdf:
                        if current_pdf_tasks.get('large', 0) >= self.max_large_pdf_tasks:
                            logger.debug(f"大PDF任务数已达上限({current_pdf_tasks.get('large', 0)}/{self.max_large_pdf_tasks})，跳过任务 {task_id}")
                            db.session.rollback()
                            return False
                    else:
                        # 小PDF：可用配额 = 小PDF限制 - 大PDF数量
                        available_small_slots = self.max_small_pdf_tasks - current_pdf_tasks.get('large', 0)
                        if current_pdf_tasks.get('small', 0) >= available_small_slots:
                            logger.debug(f"小PDF任务数已达上限({current_pdf_tasks.get('small', 0)}/{available_small_slots})，跳过任务 {task_id}")
                            db.session.rollback()
                            return False
                
                # 原子更新：只有状态为queued时才更新为process
                # 这个WHERE条件确保即使多个进程同时处理，也只有一个能成功更新
                # 使用SKIP LOCKED已经避免了行锁等待，这里只是最终的一致性保证
                update_result = db.session.execute(
                    text("""
                        UPDATE translate
                        SET status = 'process',
                            start_at = :start_time,
                            updated_at = NOW()
                        WHERE id = :task_id
                          AND status = 'queued'
                    """),
                    {
                        'task_id': task_id,
                        'start_time': start_time
                    }
                )
                
                if update_result.rowcount == 0:
                    # 更新失败（可能已被其他进程处理）
                    logger.debug(f"任务状态更新失败（可能已被其他进程处理）: task_id={task_id}")
                    db.session.rollback()
                    return False
                
                # 立即提交事务，释放行锁（避免长时间持有锁）
                db.session.commit()
                logger.info(f"队列任务 {task_id} ({origin_filepath}) 状态已更新为 process")
                
                # 获取完整任务信息（在事务外，避免长时间持有连接）
                task = Translate.query.get(task_id)
                if not task:
                    logger.warning(f"任务 {task_id} 不存在（可能已被删除）")
                    return False
                
                # 在事务外启动任务（避免长时间持有数据库连接和锁）
                # 注意：此时任务状态已经是 'process'，即使启动失败也会被标记为失败
                try:
                    success = TranslateEngine(task_id).execute()
                    
                    if success:
                        logger.info(f"队列任务 {task_id} 已启动")
                        return True
                    else:
                        # 启动失败，标记为失败（使用新的事务，避免影响其他操作）
                        try:
                            with app.app_context():
                                # 使用原子更新，避免并发问题
                                db.session.execute(
                                    text("""
                                        UPDATE translate
                                        SET status = 'failed',
                                            failed_reason = '任务启动失败',
                                            updated_at = NOW()
                                        WHERE id = :task_id
                                    """),
                                    {'task_id': task_id}
                                )
                                db.session.commit()
                        except Exception as e:
                            logger.error(f"更新任务失败状态时出错: {e}")
                        logger.error(f"队列任务 {task_id} 启动失败")
                        return False
                except Exception as e:
                    # 启动异常，标记为失败
                    logger.error(f"队列任务 {task_id} 启动异常: {e}", exc_info=True)
                    try:
                        with app.app_context():
                            # 使用原子更新，避免并发问题
                            db.session.execute(
                                text("""
                                    UPDATE translate
                                    SET status = 'failed',
                                        failed_reason = :reason,
                                        updated_at = NOW()
                                    WHERE id = :task_id
                                """),
                                {
                                    'task_id': task_id,
                                    'reason': f'任务启动异常: {str(e)[:200]}'  # 限制长度
                                }
                            )
                            db.session.commit()
                    except Exception as update_error:
                        logger.error(f"更新任务失败状态时出错: {update_error}")
                    return False
                    
        except Exception as e:
            logger.error(f"启动队列任务时出错: {e}", exc_info=True)
            try:
                from app.extensions import db
                db.session.rollback()
            except:
                pass
            return False
    
    def _select_next_task(self, queued_tasks, current_pdf_tasks):
        """智能选择下一个要启动的任务
        
        Args:
            queued_tasks: 队列中的任务列表
            current_pdf_tasks: 当前运行的PDF任务数（字典，包含 'total', 'large', 'small'）
            
        Returns:
            Translate: 要启动的任务，如果没有合适的则返回None
        """
        try:
            # 从字典中提取大PDF和小PDF的任务数
            current_large_pdf = current_pdf_tasks.get('large', 0)
            current_small_pdf = current_pdf_tasks.get('small', 0)
            
            # 计算小PDF的可用配额：小PDF配额 - 当前大PDF数量（大PDF占用小PDF配额）
            # 例如：小PDF配额3，当前有1个大PDF，则小PDF可用配额为 3-1=2
            available_small_pdf_slots = self.max_small_pdf_tasks - current_large_pdf
            
            # 按队列顺序遍历任务
            for task in queued_tasks:
                is_pdf = task.origin_filepath.lower().endswith('.pdf')
                
                if is_pdf:
                    # 如果是PDF任务，判断是大PDF还是小PDF
                    is_large = self._is_large_pdf(task.origin_filepath)
                    
                    if is_large:
                        # 大PDF任务：检查大PDF任务数是否未达上限
                        if current_large_pdf < self.max_large_pdf_tasks:
                            logger.info(f"选择PDF任务 {task.id} 开始处理")
                            logger.debug(f"选择大PDF任务 {task.id} (当前大PDF: {current_large_pdf}/{self.max_large_pdf_tasks})")
                            return task
                        else:
                            logger.debug(f"跳过大PDF任务 {task.id} (大PDF已达上限: {current_large_pdf}/{self.max_large_pdf_tasks})")
                            continue
                    else:
                        # 小PDF任务：检查可用的小PDF配额
                        if current_small_pdf < available_small_pdf_slots:
                            logger.info(f"选择PDF任务 {task.id} 开始处理")
                            logger.debug(f"选择小PDF任务 {task.id} (当前小PDF: {current_small_pdf}, 可用配额: {available_small_pdf_slots}, 大PDF占用: {current_large_pdf})")
                            return task
                        else:
                            logger.debug(f"跳过小PDF任务 {task.id} (小PDF配额不足: {current_small_pdf}/{available_small_pdf_slots}, 大PDF占用: {current_large_pdf})")
                            continue
                else:
                    # 如果不是PDF任务，直接选择
                    logger.info(f"选择非PDF任务 {task.id} 开始处理")
                    logger.debug(f"选择非PDF任务 {task.id} (大PDF: {current_large_pdf}, 小PDF: {current_small_pdf})")
                    return task
            
            # 如果遍历完所有任务都没有找到合适的，返回None
            logger.debug(f"队列中没有符合条件的任务启动 (大PDF: {current_large_pdf}/{self.max_large_pdf_tasks}, 小PDF: {current_small_pdf}/{available_small_pdf_slots})")
            logger.info("队列中没有符合条件的任务启动，等待资源释放")
            return None
            
        except Exception as e:
            logger.error(f"选择下一个任务时出错: {e}")
            return None
    
    def add_to_queue(self, task_id: int) -> bool:
        """添加任务到队列"""
        try:
            from app.models.translate import Translate
            from app.extensions import db
            
            # 获取应用实例并创建上下文
            app = self._get_app()
            
            # 在应用上下文中执行数据库操作
            with app.app_context():
                task = Translate.query.get(task_id)
                if not task:
                    logger.error(f"任务 {task_id} 不存在")
                    return False
                    
                task.status = 'queued'
                db.session.commit()
                logger.info(f"任务 {task_id} 已加入队列")
                return True
        except Exception as e:
            logger.error(f"添加任务到队列失败: {e}")
            return False
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        try:
            from app.models.translate import Translate
            
            current_tasks = self._get_current_running_tasks()
            memory_gb = self._get_memory_usage_gb()
            
            # 获取应用实例并创建上下文
            app = self._get_app()
            
            # 在应用上下文中执行数据库操作
            with app.app_context():
                # 统计各状态任务数
                queued_count = Translate.query.filter_by(status='queued', deleted_flag='N').count()
                running_count = current_tasks
                process_count = Translate.query.filter_by(status='process', deleted_flag='N').count()
                changing_count = Translate.query.filter_by(status='changing', deleted_flag='N').count()
                pdf_tasks_info = self._get_current_pdf_tasks()
                
                # 计算小PDF可用配额
                available_small_pdf_slots = self.max_small_pdf_tasks - pdf_tasks_info.get('large', 0)
                
                return {
                    'queued_count': queued_count,
                    'running_count': running_count,
                    'process_count': process_count,
                    'changing_count': changing_count,
                    'pdf_tasks_count': pdf_tasks_info.get('total', 0),  # 保持向后兼容
                    'pdf_tasks_limit': self.max_pdf_tasks,  # 保持向后兼容
                    'large_pdf_count': pdf_tasks_info.get('large', 0),
                    'small_pdf_count': pdf_tasks_info.get('small', 0),
                    'large_pdf_limit': self.max_large_pdf_tasks,
                    'small_pdf_limit': self.max_small_pdf_tasks,
                    'available_small_pdf_slots': max(0, available_small_pdf_slots),
                    'memory_usage_gb': round(memory_gb, 2),
                    'memory_limit_gb': self.max_memory_gb,
                    'task_limit': self.max_concurrent_tasks,
                    'can_start_new': current_tasks < self.max_concurrent_tasks and memory_gb < self.max_memory_gb,
                    'resource_status': {
                        'tasks_ok': current_tasks < self.max_concurrent_tasks,
                        'memory_ok': memory_gb < self.max_memory_gb,
                        'pdf_tasks_ok': pdf_tasks_info.get('total', 0) < self.max_pdf_tasks,  # 保持向后兼容
                        'large_pdf_ok': pdf_tasks_info.get('large', 0) < self.max_large_pdf_tasks,
                        'small_pdf_ok': pdf_tasks_info.get('small', 0) < available_small_pdf_slots,
                        'current_tasks': current_tasks,
                        'current_pdf_tasks': pdf_tasks_info.get('total', 0),  # 保持向后兼容
                        'current_large_pdf': pdf_tasks_info.get('large', 0),
                        'current_small_pdf': pdf_tasks_info.get('small', 0),
                        'current_memory_gb': round(memory_gb, 2)
                    }
                }
            
        except Exception as e:
            logger.error(f"获取队列状态失败: {e}")
            return {}

    def can_start_task(self, file_path=None) -> Tuple[bool, str]:
        """检查是否可以启动新任务
        
        Args:
            file_path: 要启动的任务的文件路径（可选）
        
        Returns:
            tuple: (是否可以启动, 原因说明)
        """
        try:
            current_tasks = self._get_current_running_tasks()
            memory_gb = self._get_memory_usage_gb()
            
            # 检查总任务数限制
            if current_tasks >= self.max_concurrent_tasks:
                return False, f"当前运行任务数已达上限 ({current_tasks}/{self.max_concurrent_tasks})"
            
            if memory_gb >= self.max_memory_gb:
                return False, f"内存使用量过高 ({memory_gb:.1f}GB/{self.max_memory_gb}GB)"
            
            # 检查PDF任务限制
            if file_path and file_path.lower().endswith('.pdf'):
                pdf_tasks_info = self._get_current_pdf_tasks()
                current_large_pdf = pdf_tasks_info.get('large', 0)
                current_small_pdf = pdf_tasks_info.get('small', 0)
                
                # 判断要启动的PDF是大PDF还是小PDF
                is_large = self._is_large_pdf(file_path)
                
                if is_large:
                    # 检查大PDF限制
                    if current_large_pdf >= self.max_large_pdf_tasks:
                        return False, "系统资源紧张"
                else:
                    # 检查小PDF限制（需要考虑大PDF占用）
                    available_small_pdf_slots = self.max_small_pdf_tasks - current_large_pdf
                    if current_small_pdf >= available_small_pdf_slots:
                        return False, "系统资源紧张"
            
            return True, "资源充足，可以启动"
            
        except Exception as e:
            logger.error(f"检查任务启动条件失败: {e}")
            return False, f"检查失败: {str(e)}"

# 全局队列管理器实例
queue_manager = QueueManager()
