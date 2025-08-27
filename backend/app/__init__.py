from flask import Flask
from .config import get_config
from .extensions import init_extensions, db, api
from .script.init_db import safe_init_mysql
from .script.insert_init_db import insert_initial_data, set_auto_increment, insert_initial_settings
from .utils.response import APIResponse
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, DecodeError


def create_app(config_class=None):
    app = Flask(__name__)

    # 加载配置
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    # 初始化数据库
    safe_init_mysql(app,'app/init.sql')
    # 初始化扩展（扩展内部会注册路由）
    init_extensions(app)

    # 首先注册JWT相关异常处理器（优先级最高）
    from flask_jwt_extended.exceptions import JWTExtendedException
    
    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(e):
        return {"message": "Token has expired", "code": 401}, 401
    
    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token(e):
        return {"message": "Invalid token", "code": 401}, 401
    
    @app.errorhandler(DecodeError)
    def handle_decode_error(e):
        return {"message": "Token decode error", "code": 401}, 401
    
    @app.errorhandler(JWTExtendedException)
    def handle_jwt_extended_error(e):
        return {"message": str(e), "code": 401}, 401

    # 然后注册其他HTTP状态码处理器
    @app.errorhandler(404)
    def handle_404(e):
        return APIResponse.not_found()

    @app.errorhandler(500)
    def handle_500(e):
        return APIResponse.error(message='服务器错误', code=500)

    # 最后注册通用异常处理器（优先级最低）
    @app.errorhandler(Exception)
    def handle_generic_error(e):
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"message": "Internal server error", "code": 500}, 500

    # 初始化数据库（带重试机制）
    def init_database_with_retry():
        import time
        import logging
        logger = logging.getLogger(__name__)
        
        max_retries = 30  # 最大重试30次
        retry_interval = 2  # 每次重试间隔2秒
        
        for attempt in range(max_retries):
            try:
                with app.app_context():
                    db.create_all()
                    logger.info("数据库连接成功，表创建完成")
                    return True
            except Exception as e:
                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
                else:
                    logger.error("数据库连接失败，已达到最大重试次数")
                    raise e
        
        return False
    
    # 执行数据库初始化
    init_database_with_retry()
    
    # 初始化数据
    insert_initial_data(app)
    set_auto_increment(app)
    insert_initial_settings(app) # 初始化默认系统配置
    # 开发环境路由打印
    # if app.debug:
    #     with app.app_context():
    #         print("\n=== 已注册路由 ===")
    #         for rule in app.url_map.iter_rules():
    #             methods = ','.join(rule.methods)
    #             print(f"{rule.endpoint}: {methods} -> {rule}")
    #         print("===================\n")

    return app