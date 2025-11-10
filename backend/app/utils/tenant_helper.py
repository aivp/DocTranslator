"""
租户辅助工具 - 简化租户过滤的使用
提供便捷的函数来快速添加租户过滤
"""
from flask import g
from flask_jwt_extended import get_jwt_identity
from app.models.tenant_customer import TenantCustomer
from app.models.tenant_user import TenantUser


def get_tenant_id_from_g():
    """从g对象获取租户ID"""
    return getattr(g, 'tenant_id', None)


def ensure_tenant_filter(query, user_id=None, user_type='customer'):
    """
    确保查询添加了租户过滤
    
    使用方式：
    query = Translate.query.filter_by(deleted_flag='N')
    query = ensure_tenant_filter(query, get_jwt_identity())
    
    Args:
        query: SQLAlchemy查询对象
        user_id: 用户ID，如果不提供则从JWT获取
        user_type: 用户类型 'customer' 或 'user'
    
    Returns:
        添加了租户过滤的查询对象
    """
    # 优先从g对象获取租户ID
    tenant_id = get_tenant_id_from_g()
    
    if tenant_id is None:
        # 如果没有，则查询用户的租户ID
        if user_id is None:
            user_id = get_jwt_identity()
        
        if user_id:
            if user_type == 'customer':
                tenant_customer = TenantCustomer.query.filter_by(customer_id=user_id).first()
                if tenant_customer:
                    tenant_id = tenant_customer.tenant_id
            else:
                tenant_user = TenantUser.query.filter_by(user_id=user_id).first()
                if tenant_user:
                    tenant_id = tenant_user.tenant_id
    
    # 如果找到了租户ID，则添加过滤
    if tenant_id:
        try:
            # 尝试获取模型类
            model_class = query.column_descriptions[0]['entity']
            if hasattr(model_class, 'tenant_id'):
                query = query.filter_by(tenant_id=tenant_id)
        except (IndexError, KeyError, AttributeError):
            # 如果无法获取模型类，尝试直接添加tenant_id过滤
            # 这适用于简单查询
            pass
    
    return query


def get_current_tenant_id(user_id=None, user_type='customer'):
    """
    获取当前用户的租户ID
    
    Args:
        user_id: 用户ID，如果不提供则从JWT获取
        user_type: 用户类型 'customer' 或 'user'
    
    Returns:
        int: 租户ID，如果用户没有租户则返回None
    """
    # 优先从g对象获取
    tenant_id = get_tenant_id_from_g()
    if tenant_id:
        return tenant_id
    
    # 如果没有，则查询数据库
    if user_id is None:
        user_id = get_jwt_identity()
    
    if not user_id:
        return None
    
    if user_type == 'customer':
        tenant_customer = TenantCustomer.query.filter_by(customer_id=user_id).first()
        if tenant_customer:
            return tenant_customer.tenant_id
    else:
        tenant_user = TenantUser.query.filter_by(user_id=user_id).first()
        if tenant_user:
            return tenant_user.tenant_id
    
    return None

