from datetime import datetime
from app.extensions import db


class VideoTranslate(db.Model):
    """ 视频翻译任务表 """
    __tablename__ = 'video_translate'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, nullable=False, comment='用户ID')
    filename = db.Column(db.String(520), nullable=False, comment='视频文件名(存储后的文件名)')
    original_filename = db.Column(db.String(520), nullable=False, comment='原始文件名')
    filepath = db.Column(db.String(520), nullable=False, comment='视频文件存储路径')
    video_url = db.Column(db.String(1024), comment='视频公开访问URL')
    source_language = db.Column(db.String(32), nullable=False, comment='源语言')
    target_language = db.Column(db.String(32), nullable=False, comment='目标语言')
    akool_task_id = db.Column(db.String(128), comment='Akool任务ID')
    status = db.Column(db.Enum('uploaded', 'processing', 'completed', 'failed', 'expired'), 
                      default='uploaded', comment='翻译状态')
    translated_video_url = db.Column(db.String(1024), comment='翻译后视频URL')
    lipsync_enabled = db.Column(db.Boolean, default=False, comment='是否启用唇语同步')
    webhook_url = db.Column(db.String(512), comment='回调URL')
    file_size = db.Column(db.BigInteger, default=0, comment='文件大小(字节)')
    duration = db.Column(db.Numeric(10, 2), comment='视频时长(秒)')
    error_message = db.Column(db.Text, comment='错误信息')
    expires_at = db.Column(db.DateTime, comment='过期时间')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N', comment='删除标记')
    deleted_at = db.Column(db.DateTime, comment='删除时间')

    def to_dict(self):
        """转换为字典格式"""
        from datetime import timezone, timedelta
        
        # GMT+8 时区
        gmt8 = timezone(timedelta(hours=8))
        
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'filepath': self.filepath,
            'video_url': self.video_url,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'akool_task_id': self.akool_task_id,
            'status': self.status,
            'translated_video_url': self.translated_video_url,
            'lipsync_enabled': self.lipsync_enabled,
            'file_size': self.file_size,
            'duration': float(self.duration) if self.duration else None,
            'error_message': self.error_message,
            'expires_at': self.expires_at.replace(tzinfo=timezone.utc).astimezone(gmt8).isoformat() if self.expires_at else None,
            'created_at': self.created_at.replace(tzinfo=timezone.utc).astimezone(gmt8).isoformat() if self.created_at else None,
            'updated_at': self.updated_at.replace(tzinfo=timezone.utc).astimezone(gmt8).isoformat() if self.updated_at else None,
            'deleted_flag': self.deleted_flag,
            'deleted_at': self.deleted_at.replace(tzinfo=timezone.utc).astimezone(gmt8).isoformat() if self.deleted_at else None
        }

    def is_expired(self):
        """检查是否过期"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def get_status_info(self):
        """获取状态信息"""
        now = datetime.utcnow()
        
        if self.status == 'completed':
            if self.is_expired():
                return {
                    'status': 'expired',
                    'message': '视频已过期',
                    'can_download': False
                }
            elif self.expires_at:
                days_left = (self.expires_at - now).days
                return {
                    'status': 'completed',
                    'message': f'视频有效，{days_left}天后过期',
                    'can_download': True,
                    'days_left': days_left
                }
            else:
                return {
                    'status': 'completed',
                    'message': '视频有效',
                    'can_download': True
                }
        elif self.status == 'processing':
            return {
                'status': 'processing',
                'message': '视频处理中...',
                'can_download': False
            }
        elif self.status == 'failed':
            return {
                'status': 'failed',
                'message': '视频处理失败',
                'can_download': False
            }
        else:
            return {
                'status': self.status,
                'message': '状态未知',
                'can_download': False
            }
