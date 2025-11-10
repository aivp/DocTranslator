from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.orm import relationship, foreign

from app.extensions import db


class TenantCustomer(db.Model):
    """ 租户与前台用户关联表 """
    __tablename__ = 'tenant_customer'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_id = db.Column(db.Integer, nullable=False)  # 租户ID
    customer_id = db.Column(db.Integer, nullable=False)  # 用户ID
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)  # 加入时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)  # 更新时间
    
    # 定义唯一约束：同一用户不能在同一租户中出现多次
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'customer_id', name='unique_tenant_customer'),
    )
    
    # 定义关系（用于ORM查询，但无外键约束）
    # 使用foreign()注解明确标识外键列
    tenant = db.relationship('Tenant', primaryjoin='TenantCustomer.tenant_id == foreign(Tenant.id)', backref='customers')
    customer = db.relationship('Customer', primaryjoin='TenantCustomer.customer_id == foreign(Customer.id)', backref='tenants')

    def to_dict(self):
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'customer_id': self.customer_id,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

