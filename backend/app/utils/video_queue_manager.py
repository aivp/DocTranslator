# -*- coding: utf-8 -*-
"""
视频翻译队列管理器
限制同时处理的视频翻译任务数（最大20个）
"""
import threading
import time
import logging
from typing import Dict
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

class VideoQueueManager:
    """视频翻译队列管理器"""
    
    def __init__(self):
        self.max_concurrent_videos = 20  # 最大并发视频数
        self.queue_lock = threading.Lock()
        self.monitor_thread = None
        self.running = False
        self._app = None  # 缓存应用实例
        self.check_interval = 10  # 检查间隔（秒）
        
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
        """启动队列监控线程"""
        if self.running:
            logger.warning("视频队列监控线程已经在运行")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("视频队列监控线程已启动")
    
    def stop_monitor(self):
        """停止队列监控线程"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("视频队列监控线程已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._process_queue()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"视频队列监控循环异常: {str(e)}")
                time.sleep(self.check_interval)
    
    def _process_queue(self):
        """处理队列中的视频"""
        try:
            app = self._get_app()
            with app.app_context():
                # 定期清理僵尸任务（每60次循环清理一次，约10分钟）
                if not hasattr(self, '_cleanup_counter'):
                    self._cleanup_counter = 0
                self._cleanup_counter += 1
                if self._cleanup_counter >= 60:
                    self._cleanup_counter = 0
                    self._cleanup_zombie_tasks()
                
                # 获取当前正在处理的视频数
                current_processing = self._get_current_processing_count()
                
                # 如果还有空位，启动队列中的任务
                if current_processing < self.max_concurrent_videos:
                    # 需要启动的任务数
                    slots_available = self.max_concurrent_videos - current_processing
                    
                    # 获取队列中的任务，按创建时间排序
                    queued_videos = self._get_queued_videos(slots_available)
                    
                    for video in queued_videos:
                        try:
                            self._start_video_translation(video)
                            logger.info(f"从队列启动视频翻译: video_id={video.id}, filename={video.filename}")
                        except Exception as e:
                            logger.error(f"启动视频翻译失败: video_id={video.id}, error={str(e)}")
        except Exception as e:
            logger.error(f"处理视频队列异常: {str(e)}")
    
    def _cleanup_zombie_tasks(self):
        """清理僵尸任务（超过6小时且没有akool_task_id的processing任务）"""
        try:
            from app.models.video_translate import VideoTranslate
            from app.extensions import db
            from datetime import datetime, timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=6)
            zombie_tasks = VideoTranslate.query.filter(
                VideoTranslate.status == 'processing',
                VideoTranslate.deleted_flag == 'N',
                VideoTranslate.akool_task_id == None,
                VideoTranslate.created_at < cutoff
            ).all()
            
            if zombie_tasks:
                for task in zombie_tasks:
                    task.status = 'failed'
                    task.error_message = '任务超时，自动清理'
                    task.updated_at = datetime.utcnow()
                
                db.session.commit()
                logger.info(f"清理了 {len(zombie_tasks)} 个僵尸任务")
        except Exception as e:
            logger.error(f"清理僵尸任务失败: {str(e)}")
    
    def _get_current_processing_count(self):
        """获取当前正在处理的视频数
        
        注意：这里是按任务数量统计的，不是按原始视频数量
        例如：一个视频翻译3种语言 = 3个任务
        """
        try:
            from app.models.video_translate import VideoTranslate
            count = VideoTranslate.query.filter_by(
                status='processing',
                deleted_flag='N'
            ).count()
            return count
        except Exception as e:
            logger.error(f"获取正在处理的视频数失败: {str(e)}")
            return 0
    
    def _get_queued_videos(self, limit=1):
        """获取队列中的视频（按创建时间排序）"""
        try:
            from app.models.video_translate import VideoTranslate
            videos = VideoTranslate.query.filter_by(
                status='queued',
                deleted_flag='N'
            ).order_by(VideoTranslate.created_at.asc()).limit(limit).all()
            return videos
        except Exception as e:
            logger.error(f"获取队列视频失败: {str(e)}")
            return []
    
    def _start_video_translation(self, video):
        """启动视频翻译"""
        try:
            from app.extensions import db
            
            # 如果akool_task_id已经存在，说明任务已经在Akool创建了，只需要更新状态
            if video.akool_task_id:
                logger.info(f"视频任务已在Akool创建，直接更新状态: video_id={video.id}, akool_task_id={video.akool_task_id}")
                video.status = 'processing'
                video.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"视频翻译任务已启动: video_id={video.id}")
                return True
            
            # 如果akool_task_id不存在，需要调用Akool API创建任务
            from app.utils.akool_video import AkoolVideoService
            import os
            
            # 初始化Akool服务（使用租户配置）
            # 从video对象获取租户ID
            tenant_id = getattr(video, 'tenant_id', None)
            akool_service = AkoolVideoService(tenant_id=tenant_id)
            
            # 准备翻译参数
            from app.resources.api.video import VideoTranslateResource
            webhook_url = VideoTranslateResource._generate_webhook_url(video.id)
            
            # 准备语音映射
            voices_map = {}
            if video.voice_id:
                voices_map[video.target_language] = video.voice_id
            
            # 准备术语库ID
            terminology_ids = []
            if video.terminology_ids:
                import json
                try:
                    terminology_ids = json.loads(video.terminology_ids)
                except:
                    pass
            
            # 调用Akool API创建翻译任务
            result = akool_service.create_translation(
                video_url=video.video_url,
                source_language=video.source_language,
                target_languages=[video.target_language],
                lipsync=video.lipsync_enabled,
                webhook_url=webhook_url,
                speaker_num=0,
                voice_id=video.voice_id,
                voices_map=voices_map if voices_map else None,
                terminology_ids=terminology_ids if terminology_ids else None,
                dynamic_duration=False  # 从队列启动的任务默认不启用动态时长
            )
            
            # 更新视频状态
            if result and result.get('data'):
                video_data = result['data']
                video.akool_task_id = video_data.get('_id') or video_data.get('task_id')
                video.status = 'processing'
                video.webhook_url = webhook_url
                video.updated_at = datetime.utcnow()
                
                db.session.commit()
                logger.info(f"视频翻译任务已启动: video_id={video.id}, akool_task_id={video.akool_task_id}")
                return True
            else:
                logger.error(f"创建视频翻译任务失败: video_id={video.id}")
                video.status = 'failed'
                video.error_message = '创建翻译任务失败'
                video.updated_at = datetime.utcnow()
                db.session.commit()
                return False
                
        except Exception as e:
            logger.error(f"启动视频翻译异常: video_id={video.id}, error={str(e)}")
            try:
                from app.extensions import db
                video.status = 'failed'
                video.error_message = str(e)
                video.updated_at = datetime.utcnow()
                db.session.commit()
            except:
                pass
            return False
    
    def can_start_new_translation(self):
        """检查是否可以启动新的翻译任务"""
        try:
            app = self._get_app()
            with app.app_context():
                current_processing = self._get_current_processing_count()
                return current_processing < self.max_concurrent_videos
        except Exception as e:
            logger.error(f"检查是否可以启动新任务失败: {str(e)}")
            return True  # 出错时允许启动，避免阻塞
    
    def get_queue_status(self):
        """获取队列状态"""
        try:
            app = self._get_app()
            with app.app_context():
                current_processing = self._get_current_processing_count()
                queued_count = self._get_queued_count()
                
                return {
                    'current_processing': current_processing,
                    'max_concurrent': self.max_concurrent_videos,
                    'queued_count': queued_count,
                    'can_start_new': current_processing < self.max_concurrent_videos,
                    'slots_available': max(0, self.max_concurrent_videos - current_processing)
                }
        except Exception as e:
            logger.error(f"获取队列状态失败: {str(e)}")
            return {
                'current_processing': 0,
                'max_concurrent': self.max_concurrent_videos,
                'queued_count': 0,
                'can_start_new': True,
                'slots_available': self.max_concurrent_videos
            }
    
    def _get_queued_count(self):
        """获取队列中的视频数"""
        try:
            from app.models.video_translate import VideoTranslate
            count = VideoTranslate.query.filter_by(
                status='queued',
                deleted_flag='N'
            ).count()
            return count
        except Exception as e:
            logger.error(f"获取队列视频数失败: {str(e)}")
            return 0

# 全局视频队列管理器实例
video_queue_manager = VideoQueueManager()

