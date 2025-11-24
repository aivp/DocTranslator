from datetime import datetime
from app.extensions import db


class TokenUsage(db.Model):
    """ Token使用记录表（记录每次API调用的token使用情况）"""
    __tablename__ = 'token_usage'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)  # 主键ID
    
    # 关联字段（用于关联翻译任务和用户）
    translate_id = db.Column(db.Integer, nullable=False, comment='翻译任务ID（关联 translate 表）')
    customer_id = db.Column(db.Integer, nullable=False, comment='用户ID（冗余字段，方便查询统计）')
    tenant_id = db.Column(db.Integer, default=1, comment='租户ID（冗余字段，方便多租户统计）')
    uuid = db.Column(db.String(64), comment='翻译任务UUID（冗余字段，方便查询）')
    
    # Token 统计字段（核心计费字段）- 使用 BIGINT
    input_tokens = db.Column(db.BigInteger, nullable=False, default=0, comment='输入token数（prompt_tokens）')
    output_tokens = db.Column(db.BigInteger, nullable=False, default=0, comment='输出token数（completion_tokens）')
    total_tokens = db.Column(db.BigInteger, nullable=False, default=0, comment='总token数（input + output）')
    
    # 模型和服务信息
    model = db.Column(db.String(64), comment='使用的模型（如 qwen-mt-plus, gpt-4o 等）')
    server = db.Column(db.String(32), default='openai', comment='使用的服务（openai, qwen 等）')
    
    # 文本信息（用于审计和调试）
    text_length = db.Column(db.Integer, comment='输入文本长度（字符数）')
    translated_text_length = db.Column(db.Integer, comment='输出文本长度（字符数）')
    text_preview = db.Column(db.String(500), comment='输入文本预览（前500字符，用于审计）')
    
    # API调用信息
    api_call_time = db.Column(db.DateTime, default=datetime.utcnow, comment='API调用时间')
    api_duration = db.Column(db.Integer, comment='API调用耗时（毫秒）')
    status = db.Column(db.Enum('success', 'failed'), default='success', comment='调用状态')
    error_message = db.Column(db.Text, comment='错误信息（如果调用失败）')
    retry_count = db.Column(db.Integer, default=0, comment='重试次数（如果是重试调用）')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='记录创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='记录更新时间')
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'translate_id': self.translate_id,
            'customer_id': self.customer_id,
            'tenant_id': self.tenant_id,
            'uuid': self.uuid,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'model': self.model,
            'server': self.server,
            'text_length': self.text_length,
            'translated_text_length': self.translated_text_length,
            'text_preview': self.text_preview,
            'api_call_time': self.api_call_time.isoformat() if self.api_call_time else None,
            'api_duration': self.api_duration,
            'status': self.status,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

