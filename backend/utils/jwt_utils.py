from .response import APIResponse


def configure_jwt_callbacks(jwt):
    """
    配置 JWT 的错误处理回调函数
    :param jwt: 已初始化的 JWTManager 实例
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 拦截 Token 过期错误
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        logger.warning(f"Token expired: {jwt_payload}")
        # 确保返回正确的401状态码
        response = {"message": "Token has expired", "code": 401}
        return response, 401

    # 拦截无效 Token 错误
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        logger.warning(f"Invalid token: {error}")
        response = {"message": "Invalid token", "code": 401}
        return response, 401

    # 拦截缺少 Token 的情况
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        logger.warning(f"Missing token: {error}")
        response = {"message": "Missing Authorization Header", "code": 401}
        return response, 401

    # 拦截 Token 撤销错误
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        logger.warning(f"Token revoked: {jwt_payload}")
        response = {"message": "Token has been revoked", "code": 401}
        return response, 401

    # 拦截 Token 需要刷新错误
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        logger.warning(f"Token not fresh: {jwt_payload}")
        response = {"message": "Fresh token required", "code": 401}
        return response, 401

    # 注意：wrong_token_type_loader 在当前版本的 flask_jwt_extended 中不存在
    # 已移除该回调函数以避免启动错误
    
    logger.info("✅ JWT回调函数配置完成")
    return jwt


