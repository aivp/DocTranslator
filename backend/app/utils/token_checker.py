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
        if not auth_header or not auth_header.startswith('Bearer '):
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
        
        # 可以在这里添加更多检查，比如用户状态等
        # from app.models.customer import Customer
        # user = Customer.query.get(user_id)
        # if not user or user.status == 'disabled':
        #     return False, "User not found or disabled", 401
        
        logger.info(f"Token验证成功: {user_id}")
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
            return {"message": error_message, "code": status_code}, status_code
        
        # token有效，继续执行
        logger.info("Token验证通过，继续执行接口")
        return f(*args, **kwargs)
    
    return decorated_function 