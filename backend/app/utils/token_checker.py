"""
Token检查工具
在JWT装饰器之前检查token有效性，确保JWT问题返回401而不是500
"""
import logging
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import decode_token, get_jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, DecodeError

logger = logging.getLogger(__name__)

def check_token_validity():
    """
    检查token是否有效
    返回: (is_valid, error_message, status_code)
    """
    try:
        # 获取Authorization header
        auth_header = request.headers.get('Authorization')
        # Token验证日志已关闭
        # logger.info(f"Authorization header: {auth_header}")
        
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Authorization header缺失或格式错误")
            return False, "Missing Authorization Header", 401
        
        # 提取token
        token = auth_header.split(' ')[1]
        if not token:
            return False, "Invalid token format", 401
        
        # 解码并验证token
        decoded = decode_token(token)
        
        # 检查token是否过期
        if decoded.get('exp'):
            import time
            if time.time() > decoded['exp']:
                logger.warning(f"Token已过期: {decoded.get('sub')}")
                return False, "Token has expired", 401
        
        # 检查用户ID
        user_id = decoded.get('sub')
        if not user_id:
            return False, "Invalid token payload", 401
        
        # 获取 token 的 jti (JWT ID)
        token_jti = decoded.get('jti')
        
        # 检查用户状态和单点登录（支持 customer 和 admin 两种用户类型）
        from app.models.customer import Customer
        from app.models.user import User
        
        # 先尝试作为 customer 查询
        user = Customer.query.get(user_id)
        user_type = 'customer'
        
        # 如果不是 customer，尝试作为 admin/user 查询
        if not user:
            user = User.query.get(user_id)
            user_type = 'admin'
        
        if not user:
            return False, "User not found", 401
        
        # 检查用户状态
        if hasattr(user, 'status') and user.status == 'disabled':
            return False, "User account is disabled", 401
        if hasattr(user, 'deleted_flag') and user.deleted_flag == 'Y':
            return False, "User account is disabled", 401
        
        # 单点登录检查：验证当前 token 的 jti 是否与数据库中存储的一致
        if hasattr(user, 'current_token_id') and user.current_token_id and token_jti != user.current_token_id:
            # 只在token被替换时记录警告日志（重要错误）
            logger.warning(f"Token已被新登录替换: user_id={user_id}, user_type={user_type}")
            return False, "账号已在其他设备登录，请重新登录", 401
        
        # Token验证成功日志已关闭
        # logger.info(f"Token验证成功: {user_id}")
        return True, None, 200
        
    except ExpiredSignatureError:
        logger.warning("Token过期异常")
        return False, "Token has expired", 401
    except InvalidTokenError:
        logger.warning("Token无效异常")
        return False, "Invalid token", 401
    except DecodeError:
        logger.warning("Token解码异常")
        return False, "Token decode error", 401
    except Exception as e:
        logger.error(f"Token检查异常: {e}")
        return False, "Token validation failed", 401

def require_valid_token(f):
    """
    装饰器：要求有效的token
    在@jwt_required()之前使用
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_valid, error_message, status_code = check_token_validity()
        
        if not is_valid:
            logger.warning(f"Token验证失败: {error_message}")
            # 返回与APIResponse.error一致的格式
            return {"code": status_code, "message": error_message}, status_code
        
        # token有效，继续执行
        # Token验证通过日志已关闭
        # logger.info("Token验证通过，继续执行接口")
        return f(*args, **kwargs)
    
    return decorated_function 