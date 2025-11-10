# resources/admin/tenant.py
from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required

from app import db
from app.models.tenant import Tenant
from app.models.tenant_customer import TenantCustomer
from app.models.tenant_user import TenantUser
from app.models import Customer, User
from app.utils.response import APIResponse
from app.utils.admin_tenant_helper import require_super_admin, get_tenant_allocated_storage


# 租户列表
class AdminTenantListResource(Resource):
    @jwt_required()
    @require_super_admin
    def get(self):
        """获取租户列表（超级管理员专用）"""
        parser = reqparse.RequestParser()
        parser.add_argument('page', type=int, default=1, location='args')
        parser.add_argument('limit', type=int, default=20, location='args')
        parser.add_argument('keyword', type=str, location='args')
        args = parser.parse_args()

        query = Tenant.query
        
        if args['keyword']:
            query = query.filter(
                (Tenant.tenant_code.ilike(f"%{args['keyword']}%")) |
                (Tenant.name.ilike(f"%{args['keyword']}%")) |
                (Tenant.company_name.ilike(f"%{args['keyword']}%"))
            )

        pagination = query.paginate(page=args['page'], per_page=args['limit'], error_out=False)
        tenants = [t.to_dict() for t in pagination.items]

        return APIResponse.success({
            'data': tenants,
            'total': pagination.total
        })


# 租户详情
class AdminTenantDetailResource(Resource):
    @jwt_required()
    @require_super_admin
    def get(self, id):
        """获取租户详细信息（超级管理员专用）"""
        tenant = Tenant.query.get_or_404(id)
        return APIResponse.success(tenant.to_dict())


# 创建租户
class AdminCreateTenantResource(Resource):
    @jwt_required()
    @require_super_admin
    def post(self):
        """创建租户（超级管理员专用）"""
        data = request.json
        required_fields = ['name', 'company_name', 'tenant_code']
        if not all(field in data for field in required_fields):
            return APIResponse.error('缺少必要参数', 400)

        # 检查租户代码是否已存在
        existing_tenant = Tenant.query.filter_by(tenant_code=data['tenant_code']).first()
        if existing_tenant:
            return APIResponse.error('租户代码已存在，请使用其他代码', 400)

        # 生成租户编号（基于UUID）
        import uuid
        tenant_no = f"TENANT_{uuid.uuid4().hex[:8].upper()}"
        
        tenant = Tenant(
            tenant_no=tenant_no,
            tenant_code=data['tenant_code'],
            name=data['name'],
            company_name=data['company_name'],
            contact_person=data.get('contact_person'),
            status=data.get('status', 'active'),
            storage_quota=data.get('storage_quota', 10737418240),  # 默认10GB
            max_users=data.get('max_users', 100)
        )
        db.session.add(tenant)
        db.session.commit()
        
        return APIResponse.success({
            'tenant_id': tenant.id,
            'message': '租户创建成功'
        })


# 更新租户
class AdminUpdateTenantResource(Resource):
    @jwt_required()
    @require_super_admin
    def put(self, id):
        """更新租户信息（超级管理员专用）"""
        tenant = Tenant.query.get_or_404(id)
        data = request.json

        # 如果更新租户代码，需要验证唯一性
        if 'tenant_code' in data:
            if data['tenant_code'] != tenant.tenant_code:
                existing_tenant = Tenant.query.filter_by(tenant_code=data['tenant_code']).first()
                if existing_tenant:
                    return APIResponse.error('租户代码已存在，请使用其他代码', 400)
                tenant.tenant_code = data['tenant_code']
        
        if 'name' in data:
            tenant.name = data['name']
        if 'company_name' in data:
            tenant.company_name = data['company_name']
        if 'contact_person' in data:
            tenant.contact_person = data['contact_person']
        if 'status' in data:
            tenant.status = data['status']
        if 'storage_quota' in data:
            tenant.storage_quota = data['storage_quota']
        if 'max_users' in data:
            tenant.max_users = data['max_users']

        db.session.commit()
        return APIResponse.success(message='租户信息更新成功')


# 删除租户
class AdminDeleteTenantResource(Resource):
    @jwt_required()
    @require_super_admin
    def delete(self, id):
        """删除租户（超级管理员专用）"""
        # 检查是否有用户和管理员关联
        customer_count = TenantCustomer.query.filter_by(tenant_id=id).count()
        user_count = TenantUser.query.filter_by(tenant_id=id).count()
        
        if customer_count > 0 or user_count > 0:
            return APIResponse.error(
                f'租户下有{customer_count}个用户和{user_count}个管理员，无法删除', 
                400
            )
        
        tenant = Tenant.query.get_or_404(id)
        tenant.deleted_flag = 'Y'
        db.session.commit()
        
        return APIResponse.success(message='租户删除成功')


# 分配用户到租户
class AdminAssignCustomerToTenantResource(Resource):
    @jwt_required()
    @require_super_admin
    def post(self):
        """分配用户到租户（超级管理员专用）"""
        data = request.json
        customer_id = data.get('customer_id')
        tenant_id = data.get('tenant_id')
        
        if not customer_id or not tenant_id:
            return APIResponse.error('缺少必要参数：customer_id, tenant_id', 400)
        
        # 检查用户是否存在
        customer = Customer.query.get(customer_id)
        if not customer:
            return APIResponse.error('用户不存在', 404)
        
        # 检查租户是否存在
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return APIResponse.error('租户不存在', 404)
        
        # 检查是否已关联
        existing = TenantCustomer.query.filter_by(
            customer_id=customer_id,
            tenant_id=tenant_id
        ).first()
        
        if existing:
            return APIResponse.error('用户已经在该租户下', 400)
        
        # 创建关联
        tenant_customer = TenantCustomer(
            tenant_id=tenant_id,
            customer_id=customer_id
        )
        db.session.add(tenant_customer)
        db.session.commit()
        
        return APIResponse.success(message='用户分配成功')


# 分配管理员到租户
class AdminAssignUserToTenantResource(Resource):
    @jwt_required()
    @require_super_admin
    def post(self):
        """分配管理员到租户（超级管理员专用）"""
        data = request.json
        user_id = data.get('user_id')
        tenant_id = data.get('tenant_id')
        
        if not user_id or not tenant_id:
            return APIResponse.error('缺少必要参数：user_id, tenant_id', 400)
        
        # 保护超级管理员不能被重新分配
        if is_super_admin(user_id):
            return APIResponse.error('不能重新分配超级管理员', 403)
        
        # 检查管理员是否存在
        user = User.query.get(user_id)
        if not user:
            return APIResponse.error('管理员不存在', 404)
        
        # 检查租户是否存在
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return APIResponse.error('租户不存在', 404)
        
        # 检查是否已关联
        existing = TenantUser.query.filter_by(
            user_id=user_id,
            tenant_id=tenant_id
        ).first()
        
        if existing:
            return APIResponse.error('管理员已经在该租户下', 400)
        
        # 创建关联
        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=user_id
        )
        db.session.add(tenant_user)
        db.session.commit()
        
        return APIResponse.success(message='管理员分配成功')


# 获取租户存储配额信息
class AdminTenantStorageQuotaResource(Resource):
    @jwt_required()
    def get(self, id):
        """获取租户存储配额使用情况"""
        # 超级管理员可以查看所有租户
        from app.utils.admin_tenant_helper import get_admin_tenant_id, is_super_admin
        if not is_super_admin():
            # 租户管理员只能查看自己的租户
            tenant_id = get_admin_tenant_id()
            if tenant_id != id:
                return APIResponse.error('无权限查看该租户信息', 403)
        
        tenant = Tenant.query.get_or_404(id)
        
        # 计算已分配的存储配额
        allocated_storage = get_tenant_allocated_storage(id)
        
        # 计算使用率
        usage_percentage = (allocated_storage / tenant.storage_quota * 100) if tenant.storage_quota > 0 else 0
        
        return APIResponse.success({
            'tenant_id': tenant.id,
            'tenant_name': tenant.name,
            'storage_quota': int(tenant.storage_quota),
            'allocated_storage': int(allocated_storage),
            'available_storage': int(tenant.storage_quota - allocated_storage),
            'usage_percentage': round(usage_percentage, 2)
        })

