"""
配置读取工具
支持多租户配置继承逻辑
"""
from app.models.setting import Setting
from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
from flask import g


def get_setting_value(alias, group, tenant_id=None, default=None):
    """
    获取配置值（支持租户级配置继承）
    
    优先级：
    1. 租户配置（如果存在且不为空）
    2. 全局配置（作为fallback）
    
    Args:
        alias: 配置别名
        group: 配置分组
        tenant_id: 租户ID（可选，不提供则从当前管理员获取）
        default: 默认值
    
    Returns:
        str: 配置值
    """
    # 如果没有提供tenant_id，尝试从当前管理员获取
    if tenant_id is None:
        tenant_id = g.get('tenant_id')
    
    # 1. 如果有租户ID，先查询租户配置
    if tenant_id:
        tenant_setting = Setting.query.filter_by(
            alias=alias,
            group=group,
            tenant_id=tenant_id,
            deleted_flag='N'
        ).first()
        
        # 如果租户配置存在且值不为空，直接返回
        if tenant_setting and tenant_setting.value:
            return tenant_setting.value
    
    # 2. 查询全局配置（fallback）
    global_setting = Setting.query.filter_by(
        alias=alias,
        group=group,
        tenant_id=None,
        deleted_flag='N'
    ).first()
    
    if global_setting and global_setting.value:
        return global_setting.value
    
    return default


def get_settings_by_group(group, tenant_id=None):
    """
    获取某个分组的所有配置（支持租户级配置继承）
    
    Args:
        group: 配置分组
        tenant_id: 租户ID（可选）
    
    Returns:
        dict: {alias: value} 配置字典
    """
    result = {}
    
    if tenant_id is None:
        tenant_id = g.get('tenant_id')
    
    # 获取全局配置（作为默认值）
    global_settings = Setting.query.filter_by(
        group=group,
        tenant_id=None,
        deleted_flag='N'
    ).all()
    
    global_dict = {s.alias: s.value for s in global_settings if s.alias and s.value}
    
    # 如果有租户ID，查询租户配置并覆盖全局配置
    if tenant_id:
        tenant_settings = Setting.query.filter_by(
            group=group,
            tenant_id=tenant_id,
            deleted_flag='N'
        ).all()
        
        tenant_dict = {s.alias: s.value for s in tenant_settings if s.alias and s.value}
        
        # 合并：租户配置优先，全局配置作为fallback
        result = {**global_dict, **tenant_dict}
    else:
        result = global_dict
    
    return result


def set_setting_value(alias, group, value, tenant_id=None):
    """
    设置配置值（自动识别是租户配置还是全局配置）
    
    Args:
        alias: 配置别名
        group: 配置分组
        value: 配置值
        tenant_id: 租户ID（可选，不提供则根据当前管理员决定）
    
    Returns:
        Setting: 配置对象
    """
    from app.extensions import db
    
    # 确定是租户配置还是全局配置
    if tenant_id is None:
        # 超级管理员：全局配置
        # 租户管理员：租户配置
        if is_super_admin():
            tenant_id = None
        else:
            tenant_id = get_admin_tenant_id()
    
    # 查询或创建配置
    setting = Setting.query.filter_by(
        alias=alias,
        group=group,
        tenant_id=tenant_id,
        deleted_flag='N'
    ).first()
    
    if not setting:
        setting = Setting(
            alias=alias,
            group=group,
            tenant_id=tenant_id
        )
    
    setting.value = value
    db.session.add(setting)
    db.session.commit()
    
    return setting


def check_setting_is_inherited(alias, group, tenant_id=None):
    """
    检查某个配置是否是继承的（租户未单独配置）
    
    Args:
        alias: 配置别名
        group: 配置分组
        tenant_id: 租户ID
    
    Returns:
        bool: True表示是继承的，False表示租户单独配置了
    """
    if tenant_id is None:
        tenant_id = g.get('tenant_id')
    
    if not tenant_id:
        return False  # 全局配置不叫"继承"
    
    # 查询租户是否有单独配置
    tenant_setting = Setting.query.filter_by(
        alias=alias,
        group=group,
        tenant_id=tenant_id,
        deleted_flag='N'
    ).first()
    
    # 如果没有租户配置，或者配置值为空，说明是继承的
    return not tenant_setting or not tenant_setting.value


def get_setting_info(alias, group, tenant_id=None):
    """
    获取配置详细信息（包括是否继承）
    
    Args:
        alias: 配置别名
        group: 配置分组
        tenant_id: 租户ID
    
    Returns:
        dict: {
            'value': str,  # 配置值
            'is_inherited': bool,  # 是否继承
            'source': str,  # 'tenant' 或 'global'
        }
    """
    result = {
        'value': None,
        'is_inherited': False,
        'source': None
    }
    
    if tenant_id is None:
        tenant_id = g.get('tenant_id')
    
    # 如果有租户ID，先查租户配置
    if tenant_id:
        tenant_setting = Setting.query.filter_by(
            alias=alias,
            group=group,
            tenant_id=tenant_id,
            deleted_flag='N'
        ).first()
        
        if tenant_setting and tenant_setting.value:
            result['value'] = tenant_setting.value
            result['is_inherited'] = False
            result['source'] = 'tenant'
            return result
    
    # 查全局配置
    global_setting = Setting.query.filter_by(
        alias=alias,
        group=group,
        tenant_id=None,
        deleted_flag='N'
    ).first()
    
    if global_setting and global_setting.value:
        result['value'] = global_setting.value
        result['is_inherited'] = bool(tenant_id)  # 如果有租户ID，说明是继承的
        result['source'] = 'global'
    
    return result

