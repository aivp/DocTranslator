from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class Tenant(db.Model):
    """ 租户表 """
    __tablename__ = 'tenant'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tenant_no = db.Column(db.String(32), unique=True, nullable=False)  # 租户编号（唯一）
    tenant_code = db.Column(db.String(64), unique=True, nullable=False)  # 租户代码（唯一）
    name = db.Column(db.String(255), nullable=False)  # 租户名称
    company_name = db.Column(db.String(255))  # 公司名称
    description = db.Column(db.Text)  # 租户描述
    contact_person = db.Column(db.String(255))  # 联系人
    contact_phone = db.Column(db.String(20))  # 联系电话
    contact_email = db.Column(db.String(255))  # 联系邮箱
    status = db.Column(db.Enum('active', 'inactive', 'suspended'), default='active')  # 租户状态
    storage_quota = db.Column(db.BigInteger, default=107374182400)  # 租户存储配额（默认100GB）
    total_storage = db.Column(db.BigInteger, default=0)  # 租户已使用存储空间（字节）
    max_users = db.Column(db.Integer, default=10)  # 最大用户数
    config = db.Column(db.JSON)  # 租户配置（JSON格式）
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N')  # 删除标记
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)  # 更新时间
    expires_at = db.Column(db.DateTime)  # 到期时间（可选）

    def to_dict(self):
        """将模型实例转换为字典"""
        # 动态计算已分配的存储配额
        from app.utils.admin_tenant_helper import get_tenant_allocated_storage
        allocated_storage = get_tenant_allocated_storage(self.id)
        
        return {
            'id': self.id,
            'tenant_no': self.tenant_no,
            'tenant_code': self.tenant_code,
            'name': self.name,
            'company_name': self.company_name,
            'description': self.description,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'status': self.status,
            'storage_quota': int(self.storage_quota),
            'total_storage': int(allocated_storage),  # 返回已分配的存储配额
            'max_users': self.max_users,
            'config': self.config,
            'deleted_flag': self.deleted_flag,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

