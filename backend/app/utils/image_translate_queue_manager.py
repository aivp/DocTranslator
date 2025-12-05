# -*- coding: utf-8 -*-
"""
图片翻译队列管理器
限制同时处理的图片翻译任务数（最大20个），间隔1秒提交
支持多进程环境：使用文件锁确保只有一个进程运行队列管理器
"""
import threading
import time
import logging
import os
import fcntl
from typing import Dict
from datetime import datetime
from flask import current_app
from pathlib import Path

logger = logging.getLogger(__name__)

class ImageTranslateQueueManager:
    """图片翻译队列管理器"""
    
    def __init__(self):
        self.max_concurrent_tasks = 20  # 最大并发任务数
        self.submit_interval = 1.0  # 提交间隔（秒）
        self.queue_lock = threading.Lock()
        self.processing_lock = threading.Lock()  # 处理锁
        self.monitor_thread = None
        self.running = False
        self._app = None  # 缓存应用实例
        self.check_interval = 1  # 检查间隔（秒）
        self.processing_count = 0  # 当前正在处理的任务数
        self.last_submit_time = 0  # 上次提交时间
        self._lock_file = None  # 文件锁
        self._lock_file_handle = None  # 文件锁句柄
        
    def set_app(self, app):
        """设置应用实例（由主应用调用）"""
        self._app = app
        
    def _get_app(self):
        """获取应用实例"""
        if self._app is None:
            try:
                from flask import current_app
                return current_app._get_current_object()
            except RuntimeError:
                from app import create_app
                return create_app()
        return self._app
    
    def start_monitor(self):
        """启动队列监控线程（多进程安全：使用文件锁确保只有一个进程运行）"""
        if self.running:
            logger.warning("图片翻译队列监控线程已经在运行")
            return
        
        # 尝试获取文件锁（确保只有一个进程运行队列管理器）
        if not self._acquire_lock():
            logger.info("图片翻译队列管理器已在其他进程中运行，跳过启动")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("图片翻译队列监控线程已启动（已获取进程锁）")
    
    def stop_monitor(self):
        """停止队列监控线程"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self._release_lock()
        logger.info("图片翻译队列监控线程已停止")
    
    def _acquire_lock(self):
        """获取文件锁（确保只有一个进程运行队列管理器）"""
        try:
            # 创建锁文件路径
            lock_file_path = Path('/tmp/image_translate_queue_manager.lock')
            
            # 打开锁文件（如果不存在则创建）
            self._lock_file_handle = open(lock_file_path, 'w')
            
            # 尝试获取非阻塞排他锁
            fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # 写入进程ID
            self._lock_file_handle.write(str(os.getpid()))
            self._lock_file_handle.flush()
            
            self._lock_file = lock_file_path
            return True
            
        except (IOError, OSError) as e:
            # 无法获取锁（其他进程正在运行）
            if self._lock_file_handle:
                self._lock_file_handle.close()
                self._lock_file_handle = None
            return False
        except Exception as e:
            logger.error(f"获取文件锁失败: {str(e)}")
            if self._lock_file_handle:
                self._lock_file_handle.close()
                self._lock_file_handle = None
            return False
    
    def _release_lock(self):
        """释放文件锁"""
        try:
            if self._lock_file_handle:
                fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_UN)
                self._lock_file_handle.close()
                self._lock_file_handle = None
            
            if self._lock_file and self._lock_file.exists():
                try:
                    self._lock_file.unlink()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"释放文件锁失败: {str(e)}")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._process_queue()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"图片翻译队列监控循环异常: {str(e)}", exc_info=True)
                time.sleep(self.check_interval)
    
    def _process_queue(self):
        """处理队列中的任务"""
        try:
            # 快速检查并发数，避免长时间持有锁
            with self.processing_lock:
                if self.processing_count >= self.max_concurrent_tasks:
                    return  # 已达到最大并发数
                
                # 检查提交间隔
                current_time = time.time()
                if current_time - self.last_submit_time < self.submit_interval:
                    return  # 还未到提交间隔
            
            # 在独立的上下文中快速获取任务，避免长时间占用连接
            app = self._get_app()
            queued_tasks = []
            try:
                with app.app_context():
                    from app.extensions import db
                    try:
                        # 获取队列中的任务（状态为uploaded，等待翻译）
                        # 使用快速查询，避免阻塞
                        queued_tasks = self._get_queued_tasks(1)  # 每次只取1个任务
                    finally:
                        # 立即清理session，释放连接
                        db.session.remove()
            except Exception as e:
                logger.error(f"获取队列任务时发生异常: {str(e)}", exc_info=True)
                try:
                    from app.extensions import db
                    db.session.remove()
                except:
                    pass
                return
            
            if not queued_tasks:
                return
            
            # 处理任务
            for task in queued_tasks:
                # 再次检查并发数
                with self.processing_lock:
                    if self.processing_count >= self.max_concurrent_tasks:
                        break
                    
                    # 检查提交间隔
                    current_time = time.time()
                    if current_time - self.last_submit_time < self.submit_interval:
                        break
                    
                    self.processing_count += 1
                    self.last_submit_time = current_time
                
                # 在后台线程中处理任务
                thread = threading.Thread(
                    target=self._process_single_task,
                    args=(task,),
                    daemon=True
                )
                thread.start()
                    
        except Exception as e:
            logger.error(f"处理图片翻译队列异常: {str(e)}", exc_info=True)
    
    def _get_queued_tasks(self, limit=1):
        """
        获取队列中的任务（状态为uploaded，有source_language和target_language）
        使用 SELECT FOR UPDATE SKIP LOCKED 避免多进程重复处理
        """
        try:
            from app.models.image_translate import ImageTranslate
            from app.extensions import db
            from sqlalchemy import text
            
            # 使用 SELECT FOR UPDATE SKIP LOCKED 确保多进程环境下不会重复处理
            # 这样可以确保即使多个进程同时查询，也只有一个进程能获取到任务
            query = text("""
                SELECT id FROM image_translate
                WHERE status = 'uploaded'
                  AND source_language IS NOT NULL
                  AND target_language IS NOT NULL
                  AND deleted_flag = 'N'
                ORDER BY created_at ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            """)
            
            result = db.session.execute(query, {'limit': limit})
            task_ids = [row[0] for row in result]
            
            if not task_ids:
                return []
            
            # 根据ID查询完整记录
            tasks = ImageTranslate.query.filter(
                ImageTranslate.id.in_(task_ids)
            ).all()
            
            return tasks
        except Exception as e:
            logger.error(f"获取队列任务失败: {str(e)}", exc_info=True)
            return []
    
    def _process_single_task(self, task):
        """处理单个任务"""
        app = self._get_app()
        try:
            # 快速获取任务信息，然后立即释放数据库连接
            task_id = task.id
            tenant_id = None
            source_lang = None
            target_lang = None
            image_url = None
            
            # 第一步：快速查询任务信息，立即释放连接
            try:
                with app.app_context():
                    from app.models.image_translate import ImageTranslate
                    from app.extensions import db
                    
                    # 使用 with_for_update(skip_locked=True) 避免并发问题
                    image_record = ImageTranslate.query.filter_by(id=task_id).first()
                    if not image_record or image_record.status != 'uploaded':
                        return
                    
                    # 快速获取需要的信息
                    # 保存真实的 tenant_id（可能为 None，后续会正确处理）
                    tenant_id = image_record.tenant_id
                    source_lang = image_record.source_language
                    target_lang = image_record.target_language
                    image_url = image_record.filepath
                    
                    # 立即关闭session，释放连接
                    db.session.close()
            except Exception as e:
                logger.error(f"查询任务信息失败: task_id={task_id}, error={str(e)}")
                return
            
            # 第二步：在app_context外执行网络请求（避免占用数据库连接）
            if not (image_url.startswith('http://') or image_url.startswith('https://')):
                image_url = self._convert_filepath_to_url(image_url)
                if not image_url:
                    # 更新状态失败
                    try:
                        with app.app_context():
                            from app.models.image_translate import ImageTranslate
                            from app.extensions import db
                            image_record = ImageTranslate.query.get(task_id)
                            if image_record:
                                image_record.status = 'failed'
                                image_record.error_message = '无法生成图片访问URL'
                                db.session.commit()
                            db.session.close()
                    except:
                        pass
                    return
            
            # 获取API Key（需要在应用上下文中）
            api_key = None
            try:
                with app.app_context():
                    from app.utils.api_key_helper import get_dashscope_key
                    # 使用图片记录中的 tenant_id（可能为 None，get_dashscope_key 会处理）
                    # tenant_id 已经在第一步中从图片记录获取
                    effective_tenant_id = tenant_id
                    logger.info(f"队列管理器获取API Key: task_id={task_id}, tenant_id={effective_tenant_id}")
                    api_key = get_dashscope_key(effective_tenant_id)
            except ValueError as e:
                logger.error(f"获取API Key失败: task_id={task_id}, tenant_id={tenant_id}, error={str(e)}")
                try:
                    with app.app_context():
                        from app.models.image_translate import ImageTranslate
                        from app.extensions import db
                        image_record = ImageTranslate.query.get(task_id)
                        if image_record:
                            image_record.status = 'failed'
                            image_record.error_message = '未配置翻译服务API密钥'
                            db.session.commit()
                        db.session.close()
                except:
                    pass
                return
            except Exception as e:
                logger.error(f"获取API Key异常: task_id={task_id}, tenant_id={tenant_id}, error={str(e)}")
                try:
                    with app.app_context():
                        from app.models.image_translate import ImageTranslate
                        from app.extensions import db
                        image_record = ImageTranslate.query.get(task_id)
                        if image_record:
                            image_record.status = 'failed'
                            image_record.error_message = f'获取API密钥失败: {str(e)}'
                            db.session.commit()
                        db.session.close()
                except:
                    pass
                return
            
            if not api_key:
                logger.error(f"API Key为空: task_id={task_id}, tenant_id={tenant_id}")
                try:
                    with app.app_context():
                        from app.models.image_translate import ImageTranslate
                        from app.extensions import db
                        image_record = ImageTranslate.query.get(task_id)
                        if image_record:
                            image_record.status = 'failed'
                            image_record.error_message = 'API密钥为空'
                            db.session.commit()
                        db.session.close()
                except:
                    pass
                return
            
            # 第三步：创建翻译任务（网络请求，不占用数据库连接）
            task_result = self._create_qwen_mt_image_task(
                api_key,
                image_url,
                source_lang,
                target_lang
            )
            
            # 第四步：快速更新数据库状态，立即释放连接
            try:
                with app.app_context():
                    from app.models.image_translate import ImageTranslate
                    from app.extensions import db
                    
                    # 使用原子更新，确保只有状态为uploaded的任务才会被更新
                    from sqlalchemy import text
                    
                    if task_result.get('success'):
                        task_id_from_api = task_result.get('task_id')
                        if task_id_from_api:
                            # 原子更新：只有状态为uploaded时才更新为translating
                            update_result = db.session.execute(
                                text("""
                                    UPDATE image_translate
                                    SET status = 'translating',
                                        qwen_task_id = :qwen_task_id,
                                        updated_at = NOW()
                                    WHERE id = :image_id
                                      AND status = 'uploaded'
                                """),
                                {
                                    'image_id': task_id,
                                    'qwen_task_id': task_id_from_api
                                }
                            )
                            
                            if update_result.rowcount == 0:
                                # 更新失败（可能已被其他进程处理）
                                logger.warning(f"任务状态更新失败（可能已被其他进程处理）: task_id={task_id}")
                                db.session.rollback()
                            else:
                                db.session.commit()
                                logger.info(f"✅ 图片翻译任务已提交: image_id={task_id}, qwen_task_id={task_id_from_api}")
                        else:
                            # 更新为失败状态（原子操作）
                            update_result = db.session.execute(
                                text("""
                                    UPDATE image_translate
                                    SET status = 'failed',
                                        error_message = '未获取到任务ID',
                                        updated_at = NOW()
                                    WHERE id = :image_id
                                      AND status = 'uploaded'
                                """),
                                {'image_id': task_id}
                            )
                            db.session.commit()
                            logger.error(f"图片翻译任务提交失败: image_id={task_id}, 未获取到任务ID")
                    else:
                        error_msg = task_result.get('error', '创建翻译任务失败')
                        # 更新为失败状态（原子操作）
                        update_result = db.session.execute(
                            text("""
                                UPDATE image_translate
                                SET status = 'failed',
                                    error_message = :error_msg,
                                    updated_at = NOW()
                                WHERE id = :image_id
                                  AND status = 'uploaded'
                            """),
                            {
                                'image_id': task_id,
                                'error_msg': error_msg[:500]  # 限制错误信息长度
                            }
                        )
                        db.session.commit()
                        logger.error(f"图片翻译任务提交失败: image_id={task_id}, error={error_msg}")
                    
                    # 立即关闭session，释放连接
                    db.session.close()
            except Exception as e:
                logger.error(f"更新任务状态失败: task_id={task_id}, error={str(e)}")
                
        except Exception as e:
            logger.error(f"处理图片翻译任务异常: image_id={task.id}, error={str(e)}", exc_info=True)
            try:
                with app.app_context():
                    from app.models.image_translate import ImageTranslate
                    from app.extensions import db
                    image_record = ImageTranslate.query.get(task.id)
                    if image_record:
                        image_record.status = 'failed'
                        image_record.error_message = f'处理异常: {str(e)}'
                        db.session.commit()
                    db.session.close()
            except:
                pass
        finally:
            with self.processing_lock:
                self.processing_count -= 1
    
    def _convert_filepath_to_url(self, filepath):
        """将本地文件路径转换为公网可访问的URL"""
        try:
            import os
            base_url = os.getenv('VIDEO_BASE_URL', 'http://localhost:1475')
            path_str = filepath.replace('\\', '/')
            if '/uploads/' in path_str:
                relative_path = path_str.split('/uploads/', 1)[1]
                image_url = f"{base_url}/uploads/{relative_path}"
                return image_url
            elif 'uploads' in path_str:
                idx = path_str.find('uploads')
                relative_path = path_str[idx:]
                image_url = f"{base_url}/{relative_path}"
                return image_url
            else:
                logger.error(f"无法从文件路径提取相对路径: {filepath}")
                return None
        except Exception as e:
            logger.error(f"转换文件路径为URL失败: {str(e)}")
            return None
    
    def _create_qwen_mt_image_task(self, api_key, image_url, source_language, target_language):
        """创建 Qwen-MT-Image 翻译任务（使用统一客户端）"""
        from app.utils.qwen_mt_image_client import QwenMTImageClient
        
        return QwenMTImageClient.create_translation_task(
            api_key=api_key,
            image_url=image_url,
            source_language=source_language,
            target_language=target_language,
            enable_async=True
        )


# 全局队列管理器实例
image_translate_queue_manager = ImageTranslateQueueManager()

