"""
图片合并PDF文件自动清理调度器
定期清理超过24小时的图片合并生成的PDF文件
"""
import threading
import time
import logging
from flask import Flask

logger = logging.getLogger(__name__)


class ImagesToPdfCleanupScheduler:
    """图片合并PDF文件清理调度器"""
    
    def __init__(self, app: Flask = None, cleanup_interval_hours: int = 6, expire_hours: int = 24):
        """
        初始化清理调度器
        
        Args:
            app: Flask应用实例
            cleanup_interval_hours: 清理检查间隔（小时），默认6小时
            expire_hours: 文件过期时间（小时），默认24小时
        """
        self.app = app
        self.cleanup_interval = cleanup_interval_hours * 3600  # 转换为秒
        self.expire_hours = expire_hours
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
    
    def start(self):
        """启动清理调度器"""
        with self._lock:
            if self.running:
                logger.warning("图片合并PDF清理调度器已在运行")
                return
            
            if not self.app:
                logger.error("Flask应用未初始化，无法启动清理调度器")
                return
            
            self.running = True
            self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.thread.start()
            logger.info(
                f"图片合并PDF清理调度器已启动: "
                f"清理间隔={self.cleanup_interval / 3600}小时, "
                f"过期时间={self.expire_hours}小时"
            )
    
    def stop(self):
        """停止清理调度器"""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("图片合并PDF清理调度器已停止")
    
    def _cleanup_loop(self):
        """清理循环"""
        logger.info("图片合并PDF清理调度器线程已启动")
        
        # 启动后立即执行一次清理
        self._execute_cleanup()
        
        while self.running:
            try:
                # 等待指定间隔
                time.sleep(self.cleanup_interval)
                
                if not self.running:
                    break
                
                # 执行清理
                self._execute_cleanup()
                
            except Exception as e:
                logger.error(f"图片合并PDF清理调度器循环异常: {str(e)}", exc_info=True)
                # 出错后等待一段时间再继续
                time.sleep(60)
        
        logger.info("图片合并PDF清理调度器线程已退出")
    
    def _execute_cleanup(self):
        """执行清理任务"""
        try:
            with self.app.app_context():
                from app.utils.cleanup_images_to_pdf import cleanup_expired_images_to_pdf_files
                
                logger.info("开始执行图片合并PDF文件清理任务...")
                result = cleanup_expired_images_to_pdf_files(expire_hours=self.expire_hours)
                
                if result['success']:
                    if result['deleted_count'] > 0:
                        logger.info(
                            f"图片合并PDF清理任务完成: {result['message']}, "
                            f"错误数: {result['error_count']}"
                        )
                    else:
                        logger.debug("图片合并PDF清理任务完成: 没有过期文件需要清理")
                else:
                    logger.error(f"图片合并PDF清理任务失败: {result['message']}")
                    
        except Exception as e:
            logger.error(f"执行图片合并PDF清理任务时出错: {str(e)}", exc_info=True)


# 全局调度器实例
_cleanup_scheduler = None


def init_cleanup_scheduler(app: Flask, cleanup_interval_hours: int = 6, expire_hours: int = 24):
    """
    初始化并启动清理调度器
    
    Args:
        app: Flask应用实例
        cleanup_interval_hours: 清理检查间隔（小时），默认6小时
        expire_hours: 文件过期时间（小时），默认24小时
    """
    global _cleanup_scheduler
    
    if _cleanup_scheduler is not None:
        logger.warning("清理调度器已初始化，跳过重复初始化")
        return _cleanup_scheduler
    
    _cleanup_scheduler = ImagesToPdfCleanupScheduler(
        app=app,
        cleanup_interval_hours=cleanup_interval_hours,
        expire_hours=expire_hours
    )
    _cleanup_scheduler.start()
    
    return _cleanup_scheduler


def get_cleanup_scheduler():
    """获取清理调度器实例"""
    return _cleanup_scheduler

