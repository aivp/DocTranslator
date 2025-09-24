from datetime import  date

from app.extensions import db


class Prompt(db.Model):
    """ 提示词模板表 """
    __tablename__ = 'prompt'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)              # 提示词标题
    share_flag = db.Column(db.Enum('N', 'Y'), default='N')         # 共享状态
    added_count = db.Column(db.Integer, default=0)                 # 被添加次数
    content = db.Column(db.Text, nullable=False)                   # 提示词内容（拼接后的完整内容）
    role_content = db.Column(db.Text, nullable=True)               # 角色内容
    task_content = db.Column(db.Text, nullable=True)                # 任务内容
    requirements_content = db.Column(db.Text, nullable=True)       # 翻译要求内容
    customer_id = db.Column(db.Integer, default=0)                 # 创建用户ID
    created_at = db.Column(db.Date,default=date.today)                            # 创建时间
    updated_at = db.Column(db.Date,onupdate=date.today)                            # 更新时间
    deleted_flag = db.Column(db.Enum('N', 'Y'), default='N')       # 删除标记

class PromptFav(db.Model):
    """ 提示词收藏表 """
    __tablename__ = 'prompt_fav'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    prompt_id = db.Column(db.Integer, nullable=False)              # 提示词ID
    customer_id = db.Column(db.Integer, nullable=False)            # 用户ID
    created_at = db.Column(db.DateTime)                            # 收藏时间
    updated_at = db.Column(db.DateTime)                            # 更新时间
