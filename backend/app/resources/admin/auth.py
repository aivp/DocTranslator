# resources/admin/auth.py
from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, decode_token

from app import db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.tenant_user import TenantUser
from app.utils.response import APIResponse
from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id



class AdminLoginResource(Resource):
    def post(self):
        """管理员登录[^1]"""
        data = request.json
        required_fields = ['email', 'password']
        if not all(field in data for field in required_fields):
            return APIResponse.error('缺少必要参数', 400)

        try:
            # 查询管理员用户
            admin = User.query.filter_by(
                email=data['email'],
                deleted_flag='N'
            ).first()

            # 验证用户是否存在
            if not admin:
                current_app.logger.warning(f"用户不存在：{data['email']}")
                return APIResponse.unauthorized('账号或密码错误')

            # 使用哈希验证密码
            if not admin.check_password(data['password']):
                current_app.logger.warning(f"密码错误：{data['email']}")
                return APIResponse.error('账号或密码错误')

            # 判断是否为超级管理员
            is_super = is_super_admin(admin.id)
            tenant_id = get_admin_tenant_id(admin.id)
            
            # 如果是租户管理员，需要验证租户代码
            if not is_super:
                tenant_code = data.get('tenant_code', '').strip()
                if not tenant_code:
                    return APIResponse.error('租户管理员必须输入租户代码', 400)
                
                # 根据租户代码查找租户
                tenant = Tenant.query.filter_by(tenant_code=tenant_code).first()
                if not tenant:
                    return APIResponse.error('租户代码不存在，请检查后重试', 400)
                
                # 验证该管理员是否属于这个租户
                tenant_user = TenantUser.query.filter_by(
                    user_id=admin.id,
                    tenant_id=tenant.id
                ).first()
                
                if not tenant_user:
                    return APIResponse.error('该账号不属于该租户，请检查租户代码', 403)
                
                # 使用租户ID更新tenant_id
                tenant_id = tenant.id
            
            # 生成JWT令牌，添加 user_type 标识以区分管理员和普通用户
            access_token = create_access_token(
                identity=str(admin.id),
                additional_claims={'user_type': 'admin'}
            )
            
            # 解码 token 获取 jti
            decoded = decode_token(access_token)
            token_jti = decoded.get('jti')
            
            # 更新管理员表中的当前 token ID（实现单点登录：新登录会使旧 token 失效）
            old_token_id = admin.current_token_id
            admin.current_token_id = token_jti
            db.session.commit()
            
            # 记录登录日志
            current_app.logger.info(f"✅ 管理员登录成功: admin_id={admin.id}, email={admin.email}, old_token_id={old_token_id}, new_token_id={token_jti}")
            
            return APIResponse.success({
                'token': access_token,
                'email': admin.email,
                'name': admin.name,
                'is_super_admin': is_super,
                'tenant_id': tenant_id
            })

        except Exception as e:
            current_app.logger.error(f"登录失败：{str(e)}")
            return APIResponse.error('服务器内部错误', 500)


class AdminAuthInfoResource(Resource):
    @jwt_required()
    def get(self):
        """获取当前登录管理员信息[^2]"""
        try:
            # 获取当前管理员 ID
            admin_id = get_jwt_identity()
            if not admin_id:
                return APIResponse.unauthorized('未登录')
            
            # 查询管理员用户
            admin = User.query.get(admin_id)
            if not admin:
                return APIResponse.error('管理员不存在', 404)
            
            # 检查用户状态
            if admin.deleted_flag == 'Y':
                return APIResponse.unauthorized('账号已删除')
            
            # 判断是否为超级管理员
            is_super = is_super_admin(admin.id)
            tenant_id = get_admin_tenant_id(admin.id)
            
            # 构建 roles 数组（前端需要数组格式）
            roles = ['admin'] if not is_super else ['super_admin']
            
            return APIResponse.success({
                'id': admin.id,
                'email': admin.email,
                'name': admin.name,
                'roles': roles,
                'is_super_admin': is_super,
                'tenant_id': tenant_id
            })
            
        except Exception as e:
            current_app.logger.error(f"获取管理员信息失败：{str(e)}")
            return APIResponse.error('服务器内部错误', 500)


class AdminChangePasswordResource(Resource):
    @jwt_required()
    def post(self):
        """管理员修改邮箱和密码"""
        try:
            # 获取当前管理员 ID
            admin_id = get_jwt_identity()
            # 解析请求体
            data = request.get_json()
            required_fields = ['old_password']
            if not all(field in data for field in required_fields):
                return APIResponse.error('缺少必要参数', 400)

            # 查询管理员用户
            admin = User.query.get(admin_id)
            if not admin:
                return APIResponse.error('管理员不存在', 404)

            # 验证旧密码（使用哈希验证）
            if not admin.check_password(data['old_password']):
                return APIResponse.error(message='旧密码错误')

            # 更新邮箱（如果 user 不为空）
            if 'user' in data and data['user']:
                admin.email = data['user']

            # 更新密码（如果 new_password 和 confirm_password 不为空且一致）
            if 'new_password' in data and 'confirm_password' in data:
                if data['new_password'] and data['confirm_password']:
                    if data['new_password'] != data['confirm_password']:
                        return APIResponse.error('新密码和确认密码不一致', 400)
                    admin.set_password(data['new_password'])  # 哈希加密存储

            # 保存到数据库
            db.session.commit()

            return APIResponse.success(message='修改成功')

        except Exception as e:
            current_app.logger.error(f"修改失败：{str(e)}")
            return APIResponse.error('服务器内部错误', 500)




