from datetime import datetime
from decimal import Decimal

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class Customer(db.Model):
    """ 前台用户表 """
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_no = db.Column(db.String(32))  # 用户编号
    phone = db.Column(db.String(11))  # 手机号（长度11）
    name = db.Column(db.String(255))  # 用户名
    password = db.Column(db.Text, nullable=False)  # 密码（哈希值，使用Text类型匹配数据库）
    email = db.Column(db.String(255), nullable=False)  # 邮箱
    level = db.Column(db.Enum('common', 'vip'), default='vip')  # 会员等级，默认VIP
    status = db.Column(db.Enum('enabled', 'disabled'), default='enabled')  # 账户状态
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N')  # 删除标记
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)  # 更新时间
    storage = db.Column(db.BigInteger, default=0)  # 已使用的存储空间（字节）
    total_storage = db.Column(db.BigInteger, default=1073741824) # 默认1GB 总存储空间（字节）
    current_token_id = db.Column(db.String(255), nullable=True)  # 当前有效的 token ID (jti)，用于单点登录

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        """验证密码（支持哈希和明文两种格式，兼容旧数据）"""
        import logging
        if not self.password:
            logging.warning(f"密码字段为空: customer_id={self.id}")
            return False
        
        if not password:
            logging.warning(f"输入的密码为空: customer_id={self.id}")
            return False
        
        # 如果密码是哈希格式（包含 $ 符号，这是werkzeug哈希的标准格式），使用 check_password_hash 验证
        if '$' in self.password:
            try:
                result = check_password_hash(self.password, password)
                if not result:
                    # 记录更详细的信息用于调试
                    logging.debug(f"密码哈希验证失败: customer_id={self.id}, 存储密码前缀={self.password[:30]}..., 输入密码长度={len(password)}")
                return result
            except Exception as e:
                # 如果check_password_hash失败（可能是格式问题），尝试明文比较（兼容旧数据）
                logging.warning(f"密码哈希验证异常，尝试明文比较: customer_id={self.id}, error={str(e)}")
                return self.password == password
        # 否则可能是明文存储（兼容旧数据），直接比较
        else:
            result = self.password == password
            if not result:
                logging.debug(f"明文密码比较失败: customer_id={self.id}, 存储密码长度={len(self.password)}, 输入密码长度={len(password)}")
            return result

    def to_dict(self):
        """将模型实例转换为字典，处理所有需要序列化的字段"""
        return {
            'id': self.id,
            'name': self.name,
            'customer_no': self.customer_no,
            'email': self.email,
            'status': 'enabled' if self.deleted_flag == 'N'and self.status == 'enabled' else 'disabled',
            'level': self.level,
            'storage': int(self.storage),
            'total_storage': int(self.total_storage),
            # 处理 Decimal
            'created_at': self.created_at.isoformat() if self.created_at else None,  # 注册时间
            'updated_at': self.updated_at.isoformat() if self.updated_at else None  # 更新时间
        }
