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

    # 单点登录检查：在每次 token 验证时自动检查
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """
        检查 token 是否被撤销（用于单点登录）
        虽然我们使用数据库而不是 blocklist，但可以利用这个回调来检查
        """
        from flask import has_app_context, current_app
        import traceback
        
        try:
            user_id = jwt_payload.get('sub')
            token_jti = jwt_payload.get('jti')
            
            # 单点登录检查日志已关闭
            # logger.info(f"🔍 单点登录检查: user_id={user_id}, token_jti={token_jti}")
            
            if not user_id or not token_jti:
                # logger.info("⚠️ 缺少 user_id 或 token_jti，跳过单点登录检查")
                return False  # 如果没有这些信息，让其他验证器处理
            
            # 确保在应用上下文中执行数据库查询
            if not has_app_context():
                logger.error("❌ 单点登录检查时没有应用上下文，无法查询数据库")
                return False  # 没有应用上下文时，允许通过（避免影响正常流程）
            
            # 检查用户状态和单点登录（支持 customer 和 admin 两种用户类型）
            from app.models.customer import Customer
            from app.models.user import User
            from app.extensions import db
            
            # 优先从 JWT payload 中获取 user_type（如果存在）
            user_type = jwt_payload.get('user_type')
            
            # 根据 user_type 查询对应的用户表
            if user_type == 'admin':
                # 管理员登录，查询 User 表
                user = User.query.get(user_id)
                if not user:
                    logger.warning(f"⚠️ 管理员用户不存在: user_id={user_id}")
                    return True  # 用户不存在，视为 token 已撤销
            elif user_type == 'customer':
                # 普通用户登录，查询 Customer 表
                user = Customer.query.get(user_id)
                if not user:
                    logger.warning(f"⚠️ 普通用户不存在: user_id={user_id}")
                    return True  # 用户不存在，视为 token 已撤销
            else:
                # 兼容旧 token（没有 user_type 字段），先查 Customer 再查 User
                # logger.info(f"ℹ️ Token 中没有 user_type 字段，使用兼容模式: user_id={user_id}")
                user = Customer.query.get(user_id)
                user_type = 'customer'
                
                # 如果不是 customer，尝试作为 admin/user 查询
                if not user:
                    user = User.query.get(user_id)
                    user_type = 'admin'
            
            if not user:
                logger.warning(f"⚠️ 用户不存在: user_id={user_id}, user_type={user_type}")
                return True  # 用户不存在，视为 token 已撤销
            
            # 检查用户状态
            if hasattr(user, 'status') and user.status == 'disabled':
                logger.warning(f"⚠️ 用户账号已禁用: user_id={user_id}, user_type={user_type}")
                return True  # 账号已禁用，视为 token 已撤销
            if hasattr(user, 'deleted_flag') and user.deleted_flag == 'Y':
                logger.warning(f"⚠️ 用户账号已删除: user_id={user_id}, user_type={user_type}")
                return True  # 账号已删除，视为 token 已撤销
            
            # 单点登录检查：验证当前 token 的 jti 是否与数据库中存储的一致
            if hasattr(user, 'current_token_id'):
                stored_jti = user.current_token_id
                # 单点登录检查日志已关闭
                # logger.info(f"🔍 单点登录检查: user_id={user_id}, user_type={user_type}, token_jti={token_jti}, stored_jti={stored_jti}")
                
                if stored_jti:
                    if token_jti != stored_jti:
                        # 只在token被替换时记录警告日志（重要错误）
                        logger.warning(f"❌ Token已被新登录替换: user_id={user_id}, user_type={user_type}")
                        return True  # token 不匹配，视为已撤销
                    # else:
                    #     logger.info(f"✅ Token验证通过: user_id={user_id}, user_type={user_type}")
                # else:
                #     logger.info(f"ℹ️ 用户尚未设置 current_token_id: user_id={user_id}, user_type={user_type}")
            
            return False  # token 有效
        except Exception as e:
            logger.error(f"❌ 单点登录检查异常: {e}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return False  # 异常时允许通过，避免影响正常流程

    # 注意：wrong_token_type_loader 在当前版本的 flask_jwt_extended 中不存在
    # 已移除该回调函数以避免启动错误
    
    # logger.info("✅ JWT回调函数配置完成（包含单点登录检查）")
    return jwt


