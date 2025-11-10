from datetime import datetime

from app.extensions import db


class Comparison(db.Model):
    """ 术语对照表 """
    __tablename__ = 'comparison'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)               # 对照表标题
    origin_lang = db.Column(db.String(32), nullable=False)          # 源语言代码（如en）
    target_lang = db.Column(db.String(32), nullable=False)          # 目标语言代码（如zh）
    share_flag = db.Column(db.Enum('N', 'Y'), default='N')          # 是否共享
    added_count = db.Column(db.Integer, default=0)                  # 被添加次数（之前遗漏的字段）[^2]
    content = db.Column(db.Text, nullable=True)                     # 术语内容（已废弃，保留用于兼容）
    customer_id = db.Column(db.Integer, default=0)                  # 创建用户ID
    tenant_id = db.Column(db.Integer, default=1)                    # 租户ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)                            # 更新时间
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N')        # 删除标记

    # 关联关系
    terms = db.relationship('ComparisonSub', backref='comparison', lazy='dynamic')

    def to_dict(self):
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'origin_lang': self.origin_lang,
            'target_lang': self.target_lang,
            'share_flag': self.share_flag,
            'added_count': self.added_count,
            'content': self.content,  # 保留兼容性
            'customer_id': self.customer_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,  # 格式化时间
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,  # 格式化时间
            'deleted_flag': self.deleted_flag
        }

    def get_terms_paginated(self, page=1, per_page=20):
        """获取分页的术语列表"""
        return self.terms.order_by(ComparisonSub.id)\
                        .paginate(page=page, per_page=per_page, error_out=False)

    def update_term_count(self):
        """更新术语数量"""
        self.added_count = self.terms.count()
        db.session.commit()


class ComparisonSub(db.Model):
    """ 术语子表 """
    __tablename__ = 'comparison_sub'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    comparison_sub_id = db.Column(db.Integer, db.ForeignKey('comparison.id'), nullable=False, comment='主表id')
    original = db.Column(db.String(200), nullable=True, comment='原文')
    comparison_text = db.Column(db.String(200), nullable=True, comment='对照术语')

    def to_dict(self):
        """将模型实例转换为字典"""
        return {
            'id': self.id,
            'original': self.original,
            'comparison_text': self.comparison_text
        }


class ComparisonFav(db.Model):
    """ 对照表收藏关系 """
    __tablename__ = 'comparison_fav'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    comparison_id = db.Column(db.Integer, nullable=False)           # 对照表ID
    customer_id = db.Column(db.Integer, nullable=False)             # 用户ID
    created_at = db.Column(db.DateTime,default=datetime.utcnow)                             # 收藏时间
    updated_at = db.Column(db.DateTime,onupdate=datetime.utcnow)                             # 更新时间


