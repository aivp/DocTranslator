# resources/admin/user.py
from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required

from app import db
from app.models import User
from app.models.tenant_user import TenantUser
from app.utils.auth_tools import hash_password
from app.utils.response import APIResponse
from app.utils.admin_tenant_helper import get_admin_tenant_id, is_super_admin


class AdminUserListResource(Resource):
    @jwt_required()
    def get(self):
        """获取用户列表[^1]"""
        parser = reqparse.RequestParser()
        parser.add_argument('page', type=int, default=1, location='args')
        parser.add_argument('limit', type=int, default=20, location='args')
        parser.add_argument('search', type=str, location='args')
        args = parser.parse_args()

        # 根据管理员角色过滤用户
        tenant_id = get_admin_tenant_id()
        
        if is_super_admin():
            # 超级管理员看到所有管理员
            query = User.query
        else:
            # 租户管理员只看到本租户管理员
            query = User.query.join(
                TenantUser, User.id == TenantUser.user_id
            ).filter(TenantUser.tenant_id == tenant_id)
        
        if args['search']:
            query = query.filter(User.email.ilike(f"%{args['search']}%"))

        pagination = query.paginate(page=args['page'], per_page=args['limit'], error_out=False)
        
        # 获取所有租户信息（用于显示）
        from app.models.tenant import Tenant
        tenants = {t.id: t.name for t in Tenant.query.all()}
        
        users = []
        for u in pagination.items:
            # 获取该管理员的租户
            tenant_user = TenantUser.query.filter_by(user_id=u.id).first()
            tenant_name = tenants.get(tenant_user.tenant_id, '未分配') if tenant_user else '未分配'
            
            users.append({
                'id': u.id,
                'name': u.name,
                'email': u.email,
                'role': u.role if u.role else 'tenant_admin',
                'created_at': u.created_at.isoformat() if u.created_at else None,
                'tenant_id': tenant_user.tenant_id if tenant_user else None,
                'tenant_name': tenant_name
            })

        return APIResponse.success({
            'data': users,
            'total': pagination.total
        })


# 重置密码
class AdminResetPasswordResource(Resource):
    @jwt_required()
    def post(self, id):
        """重置管理员密码"""
        # 保护超级管理员
        if is_super_admin(id):
            return APIResponse.error('不能重置超级管理员密码', 403)
        
        tenant_id = get_admin_tenant_id()
        
        # 构建查询
        if is_super_admin():
            user = User.query.get_or_404(id)
        else:
            # 租户管理员只能重置本租户管理员
            user = User.query.join(
                TenantUser, User.id == TenantUser.user_id
            ).filter(
                User.id == id,
                TenantUser.tenant_id == tenant_id
            ).first_or_404()
        
        # 重置密码为默认值（哈希加密）
        default_password = 'ad2025'
        user.set_password(default_password)
        db.session.commit()
        
        return APIResponse.success({
            'message': '密码已重置',
            'new_password': default_password
        })


# 创建新用户
class AdminCreateUserResource(Resource):
    @jwt_required()
    def put(self):
        """创建新用户[^2]"""
        data = request.json
        required_fields = ['name', 'email', 'password']
        if not all(field in data for field in required_fields):
            return APIResponse.error('缺少必要参数', 400)

        if User.query.filter_by(email=data['email']).first():
            return APIResponse.error('邮箱已存在', 400)

        # 确定租户ID
        if is_super_admin():
            # 超级管理员需要指定租户
            tenant_id = data.get('tenant_id')
            if not tenant_id:
                return APIResponse.error('超级管理员创建管理员时必须指定租户ID', 400)
        else:
            # 租户管理员自动关联到当前租户
            tenant_id = get_admin_tenant_id()
            if not tenant_id:
                return APIResponse.error('未分配到租户', 403)

        user = User(
            name=data['name'],
            email=data['email']
        )
        user.set_password(data['password'])  # 哈希加密存储
        db.session.add(user)
        db.session.flush()  # 刷新以获取user.id
        
        # 创建租户关联
        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=user.id
        )
        db.session.add(tenant_user)
        db.session.commit()
        
        return APIResponse.success({
            'user_id': user.id,
            'message': '用户创建成功'
        })


# 获取用户详细信息
class AdminUserDetailResource(Resource):
    @jwt_required()
    def get(self, id):
        """获取用户详细信息[^3]"""
        tenant_id = get_admin_tenant_id()
        
        # 构建查询
        if is_super_admin():
            # 超级管理员可以查看所有管理员
            user = User.query.get_or_404(id)
        else:
            # 租户管理员只能查看本租户管理员
            user = User.query.join(
                TenantUser, User.id == TenantUser.user_id
            ).filter(
                User.id == id,
                TenantUser.tenant_id == tenant_id
            ).first_or_404()
        
        return APIResponse.success({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'status': 'active' if user.deleted_flag == 'N' else 'deleted',
            'created_at': user.created_at.isoformat()
        })


# 编辑用户信息
class AdminUpdateUserResource(Resource):
    @jwt_required()
    def post(self, id):
        """编辑用户信息[^4]"""
        tenant_id = get_admin_tenant_id()
        
        # 构建查询
        if is_super_admin():
            # 超级管理员可以编辑所有管理员
            user = User.query.get_or_404(id)
        else:
            # 租户管理员只能编辑本租户管理员
            user = User.query.join(
                TenantUser, User.id == TenantUser.user_id
            ).filter(
                User.id == id,
                TenantUser.tenant_id == tenant_id
            ).first_or_404()
        
        data = request.json

        if 'email' in data and User.query.filter(User.email == data['email'],User.id != id).first():
            return APIResponse.error('邮箱已被使用', 400)

        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']

        db.session.commit()
        return APIResponse.success(message='用户信息更新成功')


# 删除用户
class AdminDeleteUserResource(Resource):
    @jwt_required()
    def delete(self, id):
        """删除用户[^5]"""
        # 保护超级管理员不能被删除
        if is_super_admin(id):
            return APIResponse.error('不能删除超级管理员', 403)
        
        tenant_id = get_admin_tenant_id()
        
        # 构建查询
        if is_super_admin():
            # 超级管理员可以删除所有管理员（除了超级管理员）
            user = User.query.get_or_404(id)
        else:
            # 租户管理员只能删除本租户管理员
            user = User.query.join(
                TenantUser, User.id == TenantUser.user_id
            ).filter(
                User.id == id,
                TenantUser.tenant_id == tenant_id
            ).first_or_404()
        
        user.deleted_flag = 'Y'
        db.session.commit()
        return APIResponse.success(message='用户删除成功')
