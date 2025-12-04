from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.customer_setting import CustomerSetting
from app.models import Customer
from app.utils.response import APIResponse
from app.utils.token_checker import require_valid_token
from app.utils.tenant_helper import get_current_tenant_id


class CustomerSettingResource(Resource):
    """用户翻译配置接口"""
    
    @require_valid_token
    @jwt_required()
    def get(self):
        """获取用户翻译配置（如果没有则自动创建）"""
        try:
            user_id = get_jwt_identity()
            customer = Customer.query.get(user_id)
            
            if not customer:
                return APIResponse.error("用户不存在", 404)
            
            if customer.status == 'disabled':
                return APIResponse.error("用户状态异常", 403)
            
            # 获取租户ID
            tenant_id = get_current_tenant_id(user_id)
            
            # 查询用户配置（支持租户隔离）
            setting = CustomerSetting.query.filter_by(
                customer_id=user_id,
                tenant_id=tenant_id,
                deleted_flag='N'
            ).first()
            
            # 如果没有配置，自动创建默认配置
            if not setting:
                setting = CustomerSetting(
                    customer_id=user_id,
                    tenant_id=tenant_id,
                    lang=None,  # 默认未设置，需要用户选择
                    comparison_id=None,
                    prompt_id=None,
                    pdf_translate_method='direct',
                    origin_lang=''
                )
                db.session.add(setting)
                db.session.commit()
                current_app.logger.info(f"✅ 自动创建用户翻译配置: customer_id={user_id}, tenant_id={tenant_id}")
            
            return APIResponse.success(data=setting.to_dict())
            
        except Exception as e:
            current_app.logger.error(f"获取用户翻译配置失败: {str(e)}")
            return APIResponse.error(f"获取配置失败: {str(e)}", 500)
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """保存/更新用户翻译配置"""
        try:
            user_id = get_jwt_identity()
            customer = Customer.query.get(user_id)
            
            if not customer:
                return APIResponse.error("用户不存在", 404)
            
            if customer.status == 'disabled':
                return APIResponse.error("用户状态异常", 403)
            
            data = request.json
            if not data:
                return APIResponse.error("请求数据不能为空", 400)
            
            # 获取租户ID
            tenant_id = get_current_tenant_id(user_id)
            
            # 查询或创建配置
            setting = CustomerSetting.query.filter_by(
                customer_id=user_id,
                tenant_id=tenant_id,
                deleted_flag='N'
            ).first()
            
            if not setting:
                setting = CustomerSetting(
                    customer_id=user_id,
                    tenant_id=tenant_id
                )
                db.session.add(setting)
            
            # 更新配置字段
            if 'lang' in data:
                setting.lang = data['lang']
            if 'comparison_id' in data:
                # 如果是数组，转换为逗号分隔的字符串
                if isinstance(data['comparison_id'], list):
                    # 过滤掉空值
                    valid_ids = [str(id) for id in data['comparison_id'] if id and str(id).strip()]
                    setting.comparison_id = ','.join(valid_ids) if valid_ids else None
                elif isinstance(data['comparison_id'], (int, str)) and data['comparison_id']:
                    setting.comparison_id = str(data['comparison_id'])
                else:
                    setting.comparison_id = None
            if 'prompt_id' in data:
                setting.prompt_id = data['prompt_id'] if data['prompt_id'] else None
            if 'pdf_translate_method' in data:
                setting.pdf_translate_method = data['pdf_translate_method']
            if 'origin_lang' in data:
                setting.origin_lang = data['origin_lang'] or ''
            
            db.session.commit()
            current_app.logger.info(f"✅ 保存用户翻译配置成功: customer_id={user_id}, tenant_id={tenant_id}")
            
            return APIResponse.success(data=setting.to_dict(), message="配置保存成功")
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"保存用户翻译配置失败: {str(e)}")
            return APIResponse.error(f"保存配置失败: {str(e)}", 500)

