"""
租户路径工具
用于生成带租户ID的文件存储路径
"""
from pathlib import Path
from datetime import datetime
from flask import current_app
from app.utils.tenant_helper import get_current_tenant_id


def get_tenant_upload_dir(user_id=None, tenant_id=None):
    """
    获取带租户ID的上传目录
    
    Args:
        user_id: 用户ID，如果不提供则从JWT获取
        tenant_id: 租户ID，如果不提供则查询用户租户
    
    Returns:
        str: 目录路径，格式为 storage/uploads/tenant_1/user_123/2024-01-20
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id(user_id)
    
    if tenant_id is None:
        tenant_id = 1  # 默认租户
    
    # 获取上传根目录
    base_dir = Path(current_app.config['UPLOAD_BASE_DIR'])
    
    # 按租户ID、用户ID和日期创建子目录
    date_str = datetime.now().strftime('%Y-%m-%d')
    upload_dir = base_dir / 'uploads' / f'tenant_{tenant_id}' / f'user_{user_id}' / date_str
    
    # 如果目录不存在则创建
    if not upload_dir.exists():
        upload_dir.mkdir(parents=True, exist_ok=True)
    
    return str(upload_dir)


def get_tenant_translate_dir(user_id=None, tenant_id=None):
    """
    获取带租户ID的翻译结果目录
    
    Args:
        user_id: 用户ID，如果不提供则从JWT获取
        tenant_id: 租户ID，如果不提供则查询用户租户
    
    Returns:
        str: 目录路径，格式为 storage/translate/tenant_1/user_123/2024-01-20
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id(user_id)
    
    if tenant_id is None:
        tenant_id = 1  # 默认租户
    
    # 获取存储根目录
    base_dir = Path(current_app.config['UPLOAD_BASE_DIR'])
    
    # 按租户ID、用户ID和日期创建子目录
    date_str = datetime.now().strftime('%Y-%m-%d')
    translate_dir = base_dir / 'translate' / f'tenant_{tenant_id}' / f'user_{user_id}' / date_str
    
    # 如果目录不存在则创建
    if not translate_dir.exists():
        translate_dir.mkdir(parents=True, exist_ok=True)
    
    return str(translate_dir)


def get_tenant_video_dir(user_id=None, tenant_id=None):
    """
    获取带租户ID的视频存储目录
    
    Args:
        user_id: 用户ID，如果不提供则从JWT获取
        tenant_id: 租户ID，如果不提供则查询用户租户
    
    Returns:
        str: 目录路径，格式为 storage/video/tenant_1/user_123/2024-01-20
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id(user_id)
    
    if tenant_id is None:
        tenant_id = 1  # 默认租户
    
    # 获取存储根目录
    base_dir = Path(current_app.config['UPLOAD_BASE_DIR'])
    
    # 按租户ID、用户ID和日期创建子目录
    date_str = datetime.now().strftime('%Y-%m-%d')
    video_dir = base_dir / 'video' / f'tenant_{tenant_id}' / f'user_{user_id}' / date_str
    
    # 如果目录不存在则创建
    if not video_dir.exists():
        video_dir.mkdir(parents=True, exist_ok=True)
    
    return str(video_dir)

