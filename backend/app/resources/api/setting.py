from flask_restful import Resource
from app.models.setting import Setting
from app.utils.response import APIResponse
from flask import current_app


class SystemVersionResource(Resource):
    def get(self):
        """获取站点设置"""
        # 注意：此接口未认证，无法获取租户信息，只能返回全局配置
        tenant_id = None
        
        # 定义配置字段
        fields = ['version', 'site_title', 'site_name', 'site_logo', 'admin_site_title']
        data = {}
        
        for alias in fields:
            # 先尝试获取租户级配置
            if tenant_id:
                tenant_setting = Setting.query.filter_by(
                    alias=alias,
                    group='site_setting',
                    tenant_id=tenant_id,
                    deleted_flag='N'
                ).first()
                
                if tenant_setting and tenant_setting.value:
                    data[alias] = tenant_setting.value
                    continue
            
            # 获取全局配置（fallback）
            global_setting = Setting.query.filter_by(
                alias=alias,
                group='site_setting',
                tenant_id=None,
                deleted_flag='N'
            ).first()
            
            data[alias] = global_setting.value if global_setting and global_setting.value else ''
        
        # 特殊处理 update_time
        logo_setting = Setting.query.filter_by(
            alias='site_logo',
            group='site_setting',
            tenant_id=tenant_id if tenant_id else None,
            deleted_flag='N'
        ).first()
        
        data['update_time'] = logo_setting.remark if logo_setting else None
        
        return APIResponse.success(data=data)


class SystemSettingsResource(Resource):
    def get(self):
        """获取所有系统设置（支持租户隔离）"""
        from flask import request, current_app
        from app.models.tenant_customer import TenantCustomer
        import jwt
        
        # 尝试获取租户ID（如果已登录）
        tenant_id = None
        
        # 手动从JWT获取用户ID
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                decoded = jwt.decode(token, options={"verify_signature": False}, algorithms=['HS256'])
                user_id = decoded.get('sub')
                current_app.logger.info(f"JWT User ID: {user_id}")
                
                if user_id:
                    # 查询用户的租户关联
                    tenant_customer = TenantCustomer.query.filter_by(customer_id=user_id).first()
                    if tenant_customer:
                        tenant_id = tenant_customer.tenant_id
                        current_app.logger.info(f"Found tenant_id: {tenant_id} for user {user_id}")
        except Exception as e:
            # 未认证或认证失败，使用全局配置
            current_app.logger.warning(f"Could not get tenant_id: {str(e)}")
            tenant_id = None
        
        current_app.logger.info(f"Final tenant_id: {tenant_id}")
        
        # 获取站点设置
        fields = ['version', 'site_title', 'site_name', 'site_logo', 'admin_site_title']
        site_data = {}
        
        for alias in fields:
            # 先尝试租户级配置
            if tenant_id:
                tenant_setting = Setting.query.filter_by(
                    alias=alias,
                    group='site_setting',
                    tenant_id=tenant_id,
                    deleted_flag='N'
                ).first()
                
                if tenant_setting and tenant_setting.value:
                    site_data[alias] = tenant_setting.value
                    continue
            
            # 获取全局配置（fallback）
            global_setting = Setting.query.filter_by(
                alias=alias,
                group='site_setting',
                tenant_id=None,
                deleted_flag='N'
            ).first()
            
            site_data[alias] = global_setting.value if global_setting and global_setting.value else ''
        
        # 获取 update_time
        logo_setting = Setting.query.filter_by(
            alias='site_logo',
            group='site_setting',
            tenant_id=tenant_id if tenant_id else None,
            deleted_flag='N'
        ).first()
        
        site_data['update_time'] = logo_setting.remark if logo_setting else None
        
        return APIResponse.success({
            'site_setting': site_data,
            'api_setting': {
                'api_url': current_app.config['API_URL'],
                'models': current_app.config['TRANSLATE_MODELS']
            },
            'message': 'success'
        })
