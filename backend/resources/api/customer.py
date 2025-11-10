# resources/customer.py
from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import Customer
from app.utils.security import hash_password, verify_password
from app.utils.response import APIResponse
from app.utils.mail_service import EmailService
from app.utils.validators import (
    validate_verification_code,
    validate_password_confirmation,
    validate_password_complexity
)
from app.utils.token_checker import require_valid_token


class GuestIdResource(Resource):
    def get(self):
        """生成临时访客唯一标识[^1]"""
        guest_id = str(uuid.uuid4())
        return APIResponse.success({
            'guest_id': guest_id
        })


class CustomerDetailResource(Resource):
    @require_valid_token  # 先检查token
    @jwt_required()
    def get(self, customer_id):
        """获取客户详细信息[^2]"""
        customer = Customer.query.get_or_404(customer_id)
        return APIResponse.success({
            'id': customer.id,
            'email': customer.email,
            'level': customer.level,
            'created_at': customer.created_at.isoformat(),
            'storage': customer.storage
        })
