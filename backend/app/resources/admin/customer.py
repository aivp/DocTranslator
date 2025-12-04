# -- coding: utf-8 --**
# resources/admin/customer.py
from decimal import Decimal

from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models import Customer
from app.models.tenant_customer import TenantCustomer
from app.utils.auth_tools import hash_password
from app.utils.response import APIResponse
from app.utils.admin_tenant_helper import get_admin_tenant_id, is_super_admin, check_tenant_storage_quota


# 获取用户列表
class AdminCustomerListResource(Resource):
    @jwt_required()
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('page', type=int, required=False, location='args')  # 可选，默认值为 1
        parser.add_argument('limit', type=int, required=False, location='args')  # 可选，默认值为 10
        parser.add_argument('keyword', type=str, required=False, location='args')  # 可选，无默认值
        args = parser.parse_args()
        
        # 根据管理员角色过滤用户
        tenant_id = get_admin_tenant_id()
        
        if is_super_admin():
            # 超级管理员看到所有用户
            query = Customer.query
        else:
            # 租户管理员只看到本租户用户
            query = Customer.query.join(
                TenantCustomer, Customer.id == TenantCustomer.customer_id
            ).filter(TenantCustomer.tenant_id == tenant_id)
        
        if args['keyword']:
            query = query.filter(Customer.email.ilike(f"%{args['keyword']}%"))

        pagination = query.paginate(page=args['page'], per_page=args['limit'], error_out=False)
        
        # 获取所有租户信息（用于显示）
        from app.models.tenant import Tenant
        tenants = {t.id: t.name for t in Tenant.query.all()}
        
        # 处理每条记录，添加租户信息
        customers = []
        for c in pagination.items:
            customer_dict = c.to_dict()
            # 获取该用户的租户
            tenant_customer = TenantCustomer.query.filter_by(customer_id=c.id).first()
            customer_dict['tenant_name'] = tenants.get(tenant_customer.tenant_id, '未分配') if tenant_customer else '未分配'
            customers.append(customer_dict)
        
        return APIResponse.success({
            'data': customers,
            'total': pagination.total
        })


# 更新用户状态
class CustomerStatusResource(Resource):
    @jwt_required()
    def post(self, id):
        """
        更改用户状态
        """
        # 解析请求体中的状态参数
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, required=True, choices=('enabled', 'disabled'),
                            help="状态必须是 'enabled' 或 'disabled'")
        args = parser.parse_args()

        # 查询用户（带租户过滤）
        tenant_id = get_admin_tenant_id()
        
        if is_super_admin():
            # 超级管理员可以更新所有用户
            customer = Customer.query.get(id)
        else:
            # 租户管理员只能更新本租户用户
            customer = Customer.query.join(
                TenantCustomer, Customer.id == TenantCustomer.customer_id
            ).filter(
                Customer.id == id,
                TenantCustomer.tenant_id == tenant_id
            ).first()
        
        if not customer:
            return APIResponse.error(message="用户不存在", code=404)

        # 更新用户状态
        customer.status = args['status']
        db.session.commit()  # 假设 db 是你的 SQLAlchemy 实例
        # 更新用户状态
        customer.status = args['status']
        print(f"更新前的状态: {customer.status}")  # 调试
        db.session.commit()
        print(f"更新后的状态: {customer.status}")  # 调试

        # 返回更新后的用户信息
        return APIResponse.success(data=customer.to_dict())


# 创建新用户
class AdminCreateCustomerResource(Resource):
    @jwt_required()
    def put(self):
        """创建新用户[^2]"""
        data = request.json
        required_fields = ['email', 'password']  # 'name',
        if not all(field in data for field in required_fields):
            return APIResponse.error('缺少必要参数!', 400)

        if Customer.query.filter_by(email=data['email']).first():
            return APIResponse.error('邮箱已存在', 400)

        # 确定租户ID
        if is_super_admin():
            # 超级管理员需要指定租户
            tenant_id = data.get('tenant_id')
            if not tenant_id:
                return APIResponse.error('超级管理员创建用户时必须指定租户ID', 400)
        else:
            # 租户管理员自动关联到当前租户
            tenant_id = get_admin_tenant_id()
            if not tenant_id:
                return APIResponse.error('未分配到租户', 403)

        # 设置用户默认存储配额
        default_storage = 1073741824  # 默认1GB
        
        # 检查租户存储配额（非超级管理员需要检查）
        if not is_super_admin():
            can_allocate, msg = check_tenant_storage_quota(tenant_id, default_storage)
            if not can_allocate:
                return APIResponse.error(msg, 403)

        customer = Customer(
            # name=data['name'],
            email=data['email'],
            password=hash_password(data['password']),
            level=data.get('level', '探索'),
            total_storage=default_storage  # 设置默认1GB存储空间
        )
        db.session.add(customer)
        db.session.flush()  # 刷新以获取customer.id
        
        # 创建租户关联
        tenant_customer = TenantCustomer(
            tenant_id=tenant_id,
            customer_id=customer.id
        )
        db.session.add(tenant_customer)
        db.session.commit()
        
        return APIResponse.success({
            'customer_id': customer.id,
            'message': '用户创建成功'
        })


# 获取用户信息
class AdminCustomerDetailResource(Resource):
    @jwt_required()
    def get(self, id):
        """获取用户详细信息[^3]"""
        tenant_id = get_admin_tenant_id()
        
        # 构建查询
        if is_super_admin():
            # 超级管理员可以查看所有用户
            customer = Customer.query.get_or_404(id)
        else:
            # 租户管理员只能查看本租户用户
            customer = Customer.query.join(
                TenantCustomer, Customer.id == TenantCustomer.customer_id
            ).filter(
                Customer.id == id,
                TenantCustomer.tenant_id == tenant_id
            ).first_or_404()
        
        return APIResponse.success({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'status': 'active' if customer.deleted_flag == 'N' else 'deleted',
            'level': customer.level,
            'created_at': customer.created_at.isoformat(),
            'storage': customer.storage,
            'total_storage': customer.total_storage,
        })


# 编辑用户信息
class AdminUpdateCustomerResource(Resource):
    @jwt_required()
    def post(self, id):
        """编辑用户信息[^4]"""
        tenant_id = get_admin_tenant_id()
        
        # 构建查询
        if is_super_admin():
            # 超级管理员可以编辑所有用户
            customer = Customer.query.get_or_404(id)
        else:
            # 租户管理员只能编辑本租户用户
            customer = Customer.query.join(
                TenantCustomer, Customer.id == TenantCustomer.customer_id
            ).filter(
                Customer.id == id,
                TenantCustomer.tenant_id == tenant_id
            ).first_or_404()
        
        data = request.json

        if 'email' in data and Customer.query.filter(Customer.email == data['email'],Customer.id != id).first():
            return APIResponse.error('邮箱已被使用', 400)

        if 'name' in data:
            customer.name = data['name']
        if 'email' in data:
            customer.email = data['email']
        if 'level' in data:
            customer.level = data['level']
        if 'password' in data and data['password']:
            # 更新密码（使用Customer模型的set_password方法，确保正确哈希）
            import logging
            logging.info(f"更新用户密码: customer_id={id}, email={customer.email}")
            old_password_hash = customer.password[:20] if customer.password else "None"  # 只记录前20个字符用于调试
            customer.set_password(data['password'])
            new_password_hash = customer.password[:20] if customer.password else "None"
            logging.info(f"密码已更新: customer_id={id}, 旧密码哈希前缀={old_password_hash}..., 新密码哈希前缀={new_password_hash}...")
        if 'add_storage' in data:
            additional_storage = int(data['add_storage']) * 1024 * 1024
            
            # 检查租户存储配额（非超级管理员需要检查）
            if not is_super_admin():
                # 获取用户所在租户
                tenant_customer = TenantCustomer.query.filter_by(customer_id=id).first()
                if tenant_customer:
                    can_allocate, msg = check_tenant_storage_quota(
                        tenant_customer.tenant_id, 
                        additional_storage
                    )
                    if not can_allocate:
                        return APIResponse.error(msg, 403)
            
            customer.total_storage += additional_storage
        db.session.commit()
        return APIResponse.success(message='用户信息更新成功')


# 删除用户
class AdminDeleteCustomerResource(Resource):
    @jwt_required()
    def delete(self, id):
        """删除用户[^5]"""
        tenant_id = get_admin_tenant_id()
        
        # 构建查询
        if is_super_admin():
            # 超级管理员可以删除所有用户
            customer = Customer.query.get_or_404(id)
        else:
            # 租户管理员只能删除本租户用户
            customer = Customer.query.join(
                TenantCustomer, Customer.id == TenantCustomer.customer_id
            ).filter(
                Customer.id == id,
                TenantCustomer.tenant_id == tenant_id
            ).first_or_404()
        
        customer.deleted_flag = 'Y'
        db.session.commit()
        return APIResponse.success(message='用户删除成功')
