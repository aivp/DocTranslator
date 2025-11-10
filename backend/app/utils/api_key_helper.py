# -*- coding: utf-8 -*-
"""
API Key 辅助工具
支持从数据库读取租户级 API Key，降级到环境变量
"""
import os
from flask import current_app, has_app_context
from app.models.setting import Setting
from app.extensions import db


def get_dashscope_key(tenant_id=None):
    """
    获取阿里云 DashScope API 密钥
    优先级：租户配置 > 全局配置
    
    Args:
        tenant_id: 租户ID，如果提供则优先使用租户配置
    
    Returns:
        str: API密钥
    
    Raises:
        ValueError: 如果未配置或无法读取数据库配置
    """
    # 如果没有 Flask 应用上下文，报错要求管理员配置
    if not has_app_context():
        raise ValueError("未配置翻译模型，请联系管理员")
    
    try:
        # 兼容旧的 api_key 字段名和新的 dashscope_key 字段名
        aliases_to_check = ['dashscope_key', 'api_key']
        current_app.logger.info(f"🔍 get_dashscope_key 开始: tenant_id={tenant_id}, has_context={has_app_context()}")
        
        # 1. 尝试从数据库获取租户配置
        if tenant_id:
            current_app.logger.info(f"🔍 查询租户配置: tenant_id={tenant_id}")
            for alias in aliases_to_check:
                current_app.logger.info(f"  - 查询字段: {alias}")
                tenant_setting = Setting.query.filter_by(
                    alias=alias,
                    group='api_setting',
                    tenant_id=tenant_id,
                    deleted_flag='N'
                ).first()
                
                current_app.logger.info(f"  - 结果: found={tenant_setting is not None}, value_len={len(tenant_setting.value) if (tenant_setting and tenant_setting.value) else 0}")
                
                if tenant_setting and tenant_setting.value and tenant_setting.value.strip():
                    current_app.logger.info(f"✅ 使用租户配置的API Key (字段: {alias})，租户ID: {tenant_id}")
                    return tenant_setting.value
        
        # 2. 尝试从数据库获取全局配置
        for alias in aliases_to_check:
            global_setting = Setting.query.filter_by(
                alias=alias,
                group='api_setting',
                tenant_id=None,
                deleted_flag='N'
            ).first()
            
            if global_setting and global_setting.value and global_setting.value.strip():
                current_app.logger.info(f"✅ 使用全局配置的API Key (字段: {alias})，租户ID: {tenant_id}")
                return global_setting.value
        
        # 3. 两者都没有配置，报错
        error_msg = "未配置翻译模型，请联系管理员"
        current_app.logger.error(error_msg)
        raise ValueError(error_msg)
        
    except ValueError:
        # 重新抛出 ValueError
        raise
    except Exception as e:
        error_msg = f"无法读取翻译模型配置: {e}"
        if has_app_context():
            current_app.logger.error(error_msg)
        raise ValueError("未配置翻译模型，请联系管理员")


def get_akool_client_id(tenant_id=None):
    """
    获取 Akool Client ID
    优先级：租户配置 > 全局配置
    
    Args:
        tenant_id: 租户ID
    
    Returns:
        str: Client ID
    
    Raises:
        ValueError: 如果未配置或无法读取
    """
    # 如果没有 Flask 应用上下文，报错
    if not has_app_context():
        raise ValueError("未配置视频翻译服务，请联系管理员")
    
    try:
        # 添加详细的调试日志
        current_app.logger.info(f"🔍 get_akool_client_id 开始: tenant_id={tenant_id}")
        
        # 1. 尝试从数据库获取租户配置
        if tenant_id:
            current_app.logger.info(f"🔍 查询租户配置: tenant_id={tenant_id}")
            tenant_setting = Setting.query.filter_by(
                alias='akool_client_id',
                group='api_setting',
                tenant_id=tenant_id,
                deleted_flag='N'
            ).first()
            
            current_app.logger.info(f"🔍 租户配置查询结果: found={tenant_setting is not None}, value_len={len(tenant_setting.value) if (tenant_setting and tenant_setting.value) else 0}")
            
            if tenant_setting and tenant_setting.value and tenant_setting.value.strip():
                current_app.logger.info(f"✅ 使用租户配置的Akool Client ID，租户ID: {tenant_id}")
                return tenant_setting.value
        else:
            current_app.logger.info(f"⚠️ tenant_id为None，跳过租户配置查询")
        
        # 2. 尝试从数据库获取全局配置
        current_app.logger.info(f"🔍 查询全局配置")
        global_setting = Setting.query.filter_by(
            alias='akool_client_id',
            group='api_setting',
            tenant_id=None,
            deleted_flag='N'
        ).first()
        
        current_app.logger.info(f"🔍 全局配置查询结果: found={global_setting is not None}, value_len={len(global_setting.value) if (global_setting and global_setting.value) else 0}")
        
        if global_setting and global_setting.value and global_setting.value.strip():
            current_app.logger.info(f"✅ 使用全局配置的Akool Client ID，租户ID: {tenant_id}")
            return global_setting.value
        
        # 3. 未配置则报错
        error_msg = "未配置视频翻译服务，请联系管理员"
        current_app.logger.error(f"❌ {error_msg}, tenant_id={tenant_id}")
        raise ValueError(error_msg)
        
    except ValueError:
        raise
    except Exception as e:
        error_msg = f"无法读取视频翻译配置: {e}"
        if has_app_context():
            current_app.logger.error(error_msg)
        raise ValueError("未配置视频翻译服务，请联系管理员")


def get_akool_client_secret(tenant_id=None):
    """
    获取 Akool Client Secret
    优先级：租户配置 > 全局配置
    
    Args:
        tenant_id: 租户ID
    
    Returns:
        str: Client Secret
    
    Raises:
        ValueError: 如果未配置或无法读取
    """
    # 如果没有 Flask 应用上下文，报错
    if not has_app_context():
        raise ValueError("未配置视频翻译服务，请联系管理员")
    
    try:
        # 1. 尝试从数据库获取租户配置
        if tenant_id:
            tenant_setting = Setting.query.filter_by(
                alias='akool_client_secret',
                group='api_setting',
                tenant_id=tenant_id,
                deleted_flag='N'
            ).first()
            
            if tenant_setting and tenant_setting.value and tenant_setting.value.strip():
                current_app.logger.info(f"使用租户配置的Akool Client Secret，租户ID: {tenant_id}")
                return tenant_setting.value
        
        # 2. 尝试从数据库获取全局配置
        global_setting = Setting.query.filter_by(
            alias='akool_client_secret',
            group='api_setting',
            tenant_id=None,
            deleted_flag='N'
        ).first()
        
        if global_setting and global_setting.value and global_setting.value.strip():
            current_app.logger.info(f"使用全局配置的Akool Client Secret，租户ID: {tenant_id}")
            return global_setting.value
        
        # 3. 未配置则报错
        error_msg = "未配置视频翻译服务，请联系管理员"
        current_app.logger.error(error_msg)
        raise ValueError(error_msg)
        
    except ValueError:
        raise
    except Exception as e:
        error_msg = f"无法读取视频翻译配置: {e}"
        if has_app_context():
            current_app.logger.error(error_msg)
        raise ValueError("未配置视频翻译服务，请联系管理员")


def get_current_tenant_id_from_request():
    """
    从请求中获取当前租户ID（从JWT token或上下文）
    支持customer和admin两种用户类型
    
    Returns:
        int or None: 租户ID
    """
    from flask import g
    from flask_jwt_extended import get_jwt_identity
    from app.models.tenant_customer import TenantCustomer
    from app.models.tenant_user import TenantUser
    
    # 优先从g对象获取
    tenant_id = getattr(g, 'tenant_id', None)
    if tenant_id:
        return tenant_id
    
    # 从JWT获取用户ID
    user_id = get_jwt_identity()
    if not user_id:
        return None
    
    # 先尝试作为customer查询
    tenant_customer = TenantCustomer.query.filter_by(customer_id=user_id).first()
    if tenant_customer:
        return tenant_customer.tenant_id
    
    # 再尝试作为admin/user查询
    tenant_user = TenantUser.query.filter_by(user_id=user_id).first()
    if tenant_user:
        return tenant_user.tenant_id
    
    return None


