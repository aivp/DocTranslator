from datetime import datetime
from app.extensions import db


class ImageTranslate(db.Model):
    """ 图片翻译任务表 """
    __tablename__ = 'image_translate'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, nullable=False, comment='用户ID')
    tenant_id = db.Column(db.Integer, default=1, comment='租户ID')
    
    # 文件信息
    filename = db.Column(db.String(520), nullable=False, comment='存储后的文件名（时间戳命名）')
    original_filename = db.Column(db.String(520), nullable=False, comment='原始文件名')
    filepath = db.Column(db.String(520), nullable=False, comment='图片文件存储路径（绝对路径）')
    file_size = db.Column(db.BigInteger, default=0, comment='文件大小(字节)')
    
    # 翻译信息
    source_language = db.Column(db.String(32), nullable=True, comment='用户指定的源语言')
    target_language = db.Column(db.String(32), nullable=True, comment='目标语言')
    detected_language = db.Column(db.String(32), comment='API检测到的源语言')
    original_text = db.Column(db.Text, comment='原文内容')
    translated_text = db.Column(db.Text, comment='译文内容')
    
    # 状态信息
    status = db.Column(db.Enum('uploaded', 'translating', 'completed', 'failed'), 
                      default='uploaded', comment='翻译状态')
    error_message = db.Column(db.Text, comment='错误信息')
    qwen_task_id = db.Column(db.String(128), comment='Qwen API返回的任务ID')
    translated_image_url = db.Column(db.String(520), comment='翻译后的图片URL')
    
    # 时间信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 删除标记
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N', comment='删除标记')
    deleted_at = db.Column(db.DateTime, comment='删除时间')
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'tenant_id': self.tenant_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'filepath': self.filepath,
            'file_size': self.file_size,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'detected_language': self.detected_language,
            'original_text': self.original_text,
            'translated_text': self.translated_text,
            'status': self.status,
            'error_message': self.error_message,
            'qwen_task_id': self.qwen_task_id,
            'translated_image_url': self.translated_image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_flag': self.deleted_flag,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

