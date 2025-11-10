"""
管理员租户工具
用于区分超级管理员和租户管理员，提供相应的权限控制
"""
from functools import wraps
from flask import g, current_app
from flask_jwt_extended import get_jwt_identity
from app.models.tenant_customer import TenantCustomer
from app.models.tenant_user import TenantUser
from app.utils.response import APIResponse
from app.extensions import db


def is_super_admin(user_id=None):
    """
    判断是否为超级管理员（通过 role 字段判断）
    
    Args:
        user_id: 用户ID，如果不提供则从JWT获取
    
    Returns:
        bool: 是否为超级管理员
    """
    if user_id is None:
        user_id = get_jwt_identity()
    
    if not user_id:
        return False
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return False
    
    # 查询用户角色
    from app.models.user import User
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    # 通过 role 字段判断
    return user.role == 'super_admin'


def get_admin_tenant_id(user_id=None):
    """
    获取管理员的租户ID
    
    Args:
        user_id: 用户ID，如果不提供则从JWT获取
    
    Returns:
        int or None: 租户ID，超级管理员返回None（表示不过滤）
    """
    # 超级管理员不过滤
    if is_super_admin(user_id):
        return None
    
    # 普通管理员查询租户
    if user_id is None:
        user_id = get_jwt_identity()
    
    if not user_id:
        return None
    
    tenant_user = TenantUser.query.filter_by(user_id=user_id).first()
    if tenant_user:
        return tenant_user.tenant_id
    
    return None


def filter_by_admin_tenant(query, model_class):
    """
    为查询添加管理员租户过滤
    超级管理员：不过滤
    租户管理员：添加租户过滤
    
    Args:
        query: SQLAlchemy查询对象
        model_class: 模型类
    
    Returns:
        过滤后的查询对象
    """
    tenant_id = get_admin_tenant_id()
    
    # 超级管理员不过滤
    if tenant_id is None:
        return query
    
    # 租户管理员过滤
    if hasattr(model_class, 'tenant_id'):
        return query.filter_by(tenant_id=tenant_id)
    
    return query


def require_super_admin(f):
    """
    装饰器：只允许超级管理员访问
    
    Usage:
        @require_super_admin
        def some_admin_function(self):
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_super_admin():
            return APIResponse.error('需要超级管理员权限', 403)
        return f(*args, **kwargs)
    return decorated_function


def require_admin_or_super(f):
    """
    装饰器：要求是管理员（超级管理员或租户管理员都可以）
    自动设置 g.tenant_id
    
    Usage:
        @require_admin_or_super
        def some_admin_function(self):
            tenant_id = g.tenant_id  # None表示超级管理员
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        
        if not user_id:
            return APIResponse.error('未授权访问', 401)
        
        # 获取租户ID并设置到g对象
        tenant_id = get_admin_tenant_id(user_id)
        g.tenant_id = tenant_id
        
        # 如果不是超级管理员，确保有租户
        if tenant_id is None and not is_super_admin(user_id):
            return APIResponse.error('未分配到租户', 403)
        
        return f(*args, **kwargs)
    return decorated_function


def get_tenant_allocated_storage(tenant_id):
    """
    计算租户已分配的存储配额总和
    
    Args:
        tenant_id: 租户ID
    
    Returns:
        int: 已分配的存储空间（字节）
    """
    try:
        from app.models.customer import Customer
        
        allocated_storage = db.session.query(
            db.func.sum(Customer.total_storage)
        ).join(
            TenantCustomer, Customer.id == TenantCustomer.customer_id
        ).filter(
            TenantCustomer.tenant_id == tenant_id,
            Customer.deleted_flag == 'N'
        ).scalar() or 0
        
        return int(allocated_storage)
    except Exception as e:
        current_app.logger.error(f"计算租户已分配配额失败: {str(e)}")
        return 0


def check_tenant_storage_quota(tenant_id, additional_storage):
    """
    检查增加配额后是否超过租户总配额
    
    Args:
        tenant_id: 租户ID
        additional_storage: 需要增加的存储空间（字节）
    
    Returns:
        tuple: (是否可以通过, 错误消息)
    """
    try:
        from app.models.tenant import Tenant
        
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return False, '租户不存在'
        
        current_allocated = get_tenant_allocated_storage(tenant_id)
        new_total = current_allocated + additional_storage
        
        if new_total > tenant.storage_quota:
            allocated_gb = current_allocated / (1024**3)
            quota_gb = tenant.storage_quota / (1024**3)
            return False, f'租户存储配额不足（已分配{allocated_gb:.2f}GB，总配额{quota_gb:.2f}GB）'
        
        return True, '配额足够'
    except Exception as e:
        current_app.logger.error(f"检查租户配额失败: {str(e)}")
        return False, f'检查配额时发生错误: {str(e)}'
