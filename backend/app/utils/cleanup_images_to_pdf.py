"""
图片合并PDF文件自动清理工具
清理超过24小时的图片合并生成的PDF文件
"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)


def cleanup_expired_images_to_pdf_files(expire_hours=24):
    """
    清理过期的图片合并PDF文件
    
    Args:
        expire_hours: 过期时间（小时），默认24小时
    
    Returns:
        dict: 清理结果统计
    """
    try:
        # 获取存储根目录
        base_dir = Path(current_app.config.get('UPLOAD_BASE_DIR', '/app/storage'))
        uploads_dir = base_dir / 'uploads'
        
        if not uploads_dir.exists():
            logger.warning(f"上传目录不存在: {uploads_dir}")
            return {
                'success': False,
                'message': '上传目录不存在',
                'deleted_count': 0,
                'deleted_size': 0
            }
        
        # 计算过期时间点
        expire_time = datetime.now() - timedelta(hours=expire_hours)
        expire_timestamp = expire_time.timestamp()
        
        deleted_count = 0
        deleted_size = 0
        error_count = 0
        
        # 遍历所有租户目录
        for tenant_dir in uploads_dir.glob('tenant_*'):
            if not tenant_dir.is_dir():
                continue
            
            # 遍历所有用户目录
            for user_dir in tenant_dir.glob('user_*'):
                if not user_dir.is_dir():
                    continue
                
                # 遍历所有日期目录
                for date_dir in user_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    
                    # 检查是否有 images_to_pdf 子目录
                    images_to_pdf_dir = date_dir / 'images_to_pdf'
                    if not images_to_pdf_dir.exists() or not images_to_pdf_dir.is_dir():
                        continue
                    
                    # 遍历 images_to_pdf 目录下的所有PDF文件
                    for pdf_file in images_to_pdf_dir.glob('*.pdf'):
                        try:
                            # 获取文件修改时间
                            file_mtime = pdf_file.stat().st_mtime
                            
                            # 检查是否过期
                            if file_mtime < expire_timestamp:
                                file_size = pdf_file.stat().st_size
                                
                                # 删除文件
                                pdf_file.unlink()
                                deleted_count += 1
                                deleted_size += file_size
                                
                                logger.info(
                                    f"已删除过期PDF文件: {pdf_file} "
                                    f"(创建时间: {datetime.fromtimestamp(file_mtime)}, "
                                    f"大小: {file_size / 1024 / 1024:.2f}MB)"
                                )
                        except Exception as e:
                            error_count += 1
                            logger.error(f"删除PDF文件失败: {pdf_file} - {str(e)}")
                    
                    # 如果 images_to_pdf 目录为空，尝试删除它
                    try:
                        if images_to_pdf_dir.exists() and not any(images_to_pdf_dir.iterdir()):
                            images_to_pdf_dir.rmdir()
                            logger.debug(f"已删除空目录: {images_to_pdf_dir}")
                    except Exception as e:
                        logger.debug(f"删除空目录失败（可能不为空）: {images_to_pdf_dir} - {str(e)}")
        
        result = {
            'success': True,
            'message': f'清理完成，删除 {deleted_count} 个文件，释放 {deleted_size / 1024 / 1024:.2f}MB 空间',
            'deleted_count': deleted_count,
            'deleted_size': deleted_size,
            'error_count': error_count,
            'expire_hours': expire_hours
        }
        
        if deleted_count > 0:
            logger.info(
                f"图片合并PDF清理完成: 删除 {deleted_count} 个过期文件，"
                f"释放 {deleted_size / 1024 / 1024:.2f}MB 空间，"
                f"错误 {error_count} 个"
            )
        else:
            logger.debug("图片合并PDF清理完成: 没有过期文件需要清理")
        
        return result
        
    except Exception as e:
        logger.error(f"清理图片合并PDF文件时出错: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'清理失败: {str(e)}',
            'deleted_count': 0,
            'deleted_size': 0,
            'error_count': 0
        }


def cleanup_expired_images_to_pdf_files_with_app_context(app, expire_hours=24):
    """
    在Flask应用上下文中清理过期的图片合并PDF文件
    
    Args:
        app: Flask应用实例
        expire_hours: 过期时间（小时），默认24小时
    
    Returns:
        dict: 清理结果统计
    """
    with app.app_context():
        return cleanup_expired_images_to_pdf_files(expire_hours=expire_hours)

