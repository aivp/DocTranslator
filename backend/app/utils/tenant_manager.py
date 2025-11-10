"""
租户管理器
用于实现多租户数据隔离
"""
from functools import wraps
from flask import g
from flask_jwt_extended import get_jwt_identity
from app.extensions import db
from app.models.tenant_customer import TenantCustomer
from app.models.tenant_user import TenantUser


def get_current_tenant_id(user_id=None, user_type='customer'):
    """
    获取当前用户的租户ID
    
    Args:
        user_id: 用户ID，如果不提供则从JWT获取
        user_type: 用户类型 'customer' 或 'user'
    
    Returns:
        int: 租户ID，如果用户没有租户则返回None
    """
    if user_id is None:
        user_id = get_jwt_identity()
    
    if not user_id:
        return None
    
    # 根据用户类型查询租户关联
    if user_type == 'customer':
        query = TenantCustomer.query.filter_by(customer_id=user_id).first()
    else:
        query = TenantUser.query.filter_by(user_id=user_id).first()
    
    if query:
        return query.tenant_id
    return None


def require_tenant_access(user_type='customer'):
    """
    装饰器：确保请求有租户访问权限
    自动将租户ID设置到g对象中
    
    Args:
        user_type: 用户类型 'customer' 或 'user'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            if not user_id:
                from app.utils.response import APIResponse
                return APIResponse.error('未授权访问', 401)
            
            # 获取租户ID
            tenant_id = get_current_tenant_id(user_id, user_type)
            
            if not tenant_id:
                from app.utils.response import APIResponse
                return APIResponse.error('用户未分配到租户', 403)
            
            # 将租户ID存储到g对象中，供后续使用
            g.tenant_id = tenant_id
            g.user_id = user_id
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def filter_by_tenant(query, model, tenant_id=None):
    """
    为查询添加租户过滤条件
    
    Args:
        query: SQLAlchemy查询对象
        model: 模型类
        tenant_id: 租户ID，如果不提供则从g对象获取
    
    Returns:
        过滤后的查询对象
    """
    if tenant_id is None:
        tenant_id = getattr(g, 'tenant_id', None)
    
    if tenant_id is None:
        return query
    
    # 如果模型有tenant_id字段，则添加过滤条件
    if hasattr(model, 'tenant_id'):
        return query.filter_by(tenant_id=tenant_id)
    
    return query


def set_tenant_id_for_record(record, tenant_id=None):
    """
    为记录设置租户ID
    
    Args:
        record: 数据库记录对象
        tenant_id: 租户ID，如果不提供则从g对象获取
    """
    if tenant_id is None:
        tenant_id = getattr(g, 'tenant_id', None)
    
    if tenant_id and hasattr(record, 'tenant_id'):
        record.tenant_id = tenant_id

