# resources/auth.py
from flask import request
from flask_restful import Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta

from app.extensions import db
from app.models import  Customer, SendCode
from app.models.tenant import Tenant
from app.models.tenant_customer import TenantCustomer
from app.utils.security import hash_password, verify_password
from app.utils.response import APIResponse
from app.utils.mail_service import EmailService
import random

from app.utils.validators import (
    validate_verification_code,
    validate_password_confirmation
)




class SendRegisterCodeResource(Resource):
    def post(self):
        """发送注册验证码接口[^1]"""
        email = request.form.get('email')
        if Customer.query.filter_by(email=email).first():
            return APIResponse.error('邮箱已存在', 400)

        code = ''.join(random.choices('0123456789', k=6))
        send_code = SendCode(
            send_type=1,
            send_to=email,
            code=code,
            created_at=datetime.utcnow()
        )
        db.session.add(send_code)
        try:
            EmailService.send_verification_code(email, code)
            db.session.commit()
            return APIResponse.success()
        except Exception as e:
            db.session.rollback()
            return APIResponse.error('邮件发送失败', 500)


class UserRegisterResource(Resource):
    def post(self):
        """用户注册接口[^2]"""
        data = request.form

        required_fields = ['email', 'password', 'code']
        if not all(field in data for field in required_fields):
            return APIResponse.error('缺少必要参数', 400)

        # 验证码有效性验证
        is_valid, msg = validate_verification_code(
            data['email'], data['code'], 1
        )
        if not is_valid:
            return APIResponse.error(msg, 400)

        customer = Customer(
            email=data['email'],
            password=hash_password(data['password']),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            total_storage=1073741824  # 设置默认1GB存储空间
        )
        db.session.add(customer)
        db.session.commit()

        # 确保identity是字符串
        # access_token = create_access_token(identity=str(customer.id))
        return APIResponse.success(message='注册成功！',data={
            # 'token': access_token,
            'email': data['email']
        })


class UserLoginResource(Resource):
    def post(self):
        """用户登录接口[^3]"""
        try:
            data = request.form
            customer = Customer.query.filter_by(email=data['email']).first()

            if not customer:
                return APIResponse.error('账号或密码错误', 401)
            
            # 验证密码（添加异常处理和详细日志）
            import logging
            try:
                # 检查密码字段是否存在且不为空
                if not customer.password:
                    logging.error(f"用户密码字段为空: customer_id={customer.id}, email={data.get('email')}")
                    return APIResponse.error('账号或密码错误', 401)
                
                # 记录密码格式信息（不记录实际密码）
                password_format = "哈希格式" if '$' in customer.password else "可能是明文"
                logging.info(f"密码验证: customer_id={customer.id}, email={data.get('email')}, 密码格式={password_format}, 密码长度={len(customer.password)}")
                
                # 优先使用Customer模型的verify_password方法（支持哈希和明文兼容）
                if hasattr(customer, 'verify_password'):
                    password_valid = customer.verify_password(data['password'])
                else:
                    # 回退到使用工具函数
                    password_valid = verify_password(customer.password, data['password'])
                
                if not password_valid:
                    logging.warning(f"密码验证失败: customer_id={customer.id}, email={data.get('email')}, 密码格式={password_format}")
                    return APIResponse.error('账号或密码错误', 401)
            except Exception as e:
                # 如果密码验证出错（可能是密码格式问题），记录详细日志
                logging.error(f"密码验证异常: {str(e)}, customer_id={customer.id}, email={data.get('email')}, 密码长度={len(customer.password) if customer.password else 0}")
                return APIResponse.error('账号或密码错误', 401)
            
            # 获取租户代码（必填）
            tenant_code = data.get('tenant_code', '').strip()
            if not tenant_code:
                return APIResponse.error('请输入租户代码', 400)
            
            # 根据租户代码查找租户
            tenant = Tenant.query.filter_by(tenant_code=tenant_code).first()
            if not tenant:
                return APIResponse.error('租户代码不存在，请检查后重试', 400)
            
            # 验证该用户是否属于这个租户
            tenant_customer = TenantCustomer.query.filter_by(
                customer_id=customer.id,
                tenant_id=tenant.id
            ).first()
            
            if not tenant_customer:
                return APIResponse.error('该账号不属于该租户，请检查租户代码', 403)
            
            # 生成新的 token，并获取其 jti (JWT ID)
            # 添加 user_type 标识以区分管理员和普通用户
            access_token = create_access_token(
                identity=str(customer.id),
                additional_claims={'user_type': 'customer'}
            )
            
            # 解码 token 获取 jti
            from flask_jwt_extended import decode_token
            decoded = decode_token(access_token)
            token_jti = decoded.get('jti')
            
            # 更新用户表中的当前 token ID（实现单点登录：新登录会使旧 token 失效）
            customer.current_token_id = token_jti
            db.session.commit()
            
            return APIResponse.success({
                'token': access_token,
                'email': data['email'],
                'level': customer.level
            })
        except Exception as e:
            import logging
            logging.error(f"登录接口异常: {str(e)}", exc_info=True)
            return APIResponse.error('服务器内部错误', 500)


class SendResetCodeResource(Resource):
    def post(self):
        """发送密码重置验证码接口[^4]"""
        email = request.form.get('email')
        if not Customer.query.filter_by(email=email).first():
            return APIResponse.not_found('用户不存在')

        code = ''.join(random.choices('0123456789', k=6))
        send_code = SendCode(
            send_type=2,
            send_to=email,
            code=code,
            created_at=datetime.utcnow()
        )
        db.session.add(send_code)
        try:
            EmailService.send_verification_code(email, code)
            db.session.commit()
            return APIResponse.success()
        except Exception as e:
            db.session.rollback()
            return APIResponse.error('邮件发送失败', 500)


class ResetPasswordResource(Resource):
    def post(self):
        """重置密码接口[^5]"""
        data = request.form

        # 密码一致性验证
        is_valid, msg = validate_password_confirmation(data)
        if not is_valid:
            return APIResponse.error(msg, 400)

        # 验证码有效性验证
        is_valid, msg = validate_verification_code(
            data['email'], data['code'], 2
        )
        if not is_valid:
            return APIResponse.error(msg, 400)

        customer = Customer.query.filter_by(email=data['email']).first()
        customer.password = hash_password(data['password'])
        customer.updated_at = datetime.utcnow()
        db.session.commit()
        return APIResponse.success()


class UserLogoutResource(Resource):
    @jwt_required()
    def post(self):
        """用户退出登录接口"""
        # 获取当前用户ID
        current_user_id = get_jwt_identity()
        
        # 这里可以添加一些退出登录的逻辑，比如：
        # 1. 记录退出登录时间
        # 2. 清除服务端session（如果有的话）
        # 3. 记录日志等
        
        # 由于JWT是无状态的，服务端不需要特别处理token失效
        # 客户端清除token即可
        
        return APIResponse.success(message='退出登录成功')

