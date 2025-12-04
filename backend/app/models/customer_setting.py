from datetime import datetime
import json

from app.extensions import db


class CustomerSetting(db.Model):
    """ 用户翻译配置表 """
    __tablename__ = 'customer_setting'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, nullable=False, comment='用户ID（关联customer表）')
    tenant_id = db.Column(db.Integer, nullable=True, comment='租户ID（支持租户隔离）')
    
    # 用户翻译配置参数（仅存储用户选择的配置）
    lang = db.Column(db.String(32), nullable=True, comment='目标语言（英文名，如English、Chinese等）')
    comparison_id = db.Column(db.String(255), nullable=True, comment='术语库ID（逗号分隔，如"1,2,3"，支持多选）')
    prompt_id = db.Column(db.BigInteger, nullable=True, comment='提示词ID（关联prompt表）')
    pdf_translate_method = db.Column(db.String(32), default='direct', comment='PDF翻译方法：direct(直接翻译) 或 doc2x(转换后翻译)')
    origin_lang = db.Column(db.String(32), default='', comment='源语言（可选，可能自动检测）')
    
    # 元数据字段
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow, comment='更新时间')
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N', comment='删除标记')
    
    def to_dict(self):
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'tenant_id': self.tenant_id,
            'lang': self.lang,
            'comparison_id': self.comparison_id.split(',') if self.comparison_id else [],
            'prompt_id': self.prompt_id,
            'pdf_translate_method': self.pdf_translate_method,
            'origin_lang': self.origin_lang,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

