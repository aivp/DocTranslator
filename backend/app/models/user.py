# 后台管理用户模型 (对应user表)
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    password = db.Column(db.String(255), nullable=False)  # 增加长度以存储哈希值
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('super_admin', 'tenant_admin'), default='tenant_admin', comment='角色类型：super_admin=超级管理员，tenant_admin=租户管理员')
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def set_password(self, password):
        """设置密码（哈希加密）"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """验证密码（支持明文和哈希两种格式）"""
        # 如果密码是哈希格式（包含 $ 符号），使用 check_password_hash 验证
        if '$' in self.password and ('pbkdf2:sha256' in self.password or 'scrypt:' in self.password):
            return check_password_hash(self.password, password)
        # 否则是明文存储，直接比较
        else:
            return self.password == password

    