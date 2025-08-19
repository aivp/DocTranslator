from flask import Flask, jsonify
from flask_cors import CORS
from .config import get_config
from .extensions import init_extensions, db, api
from .models.setting import Setting
from .resources.task.translate_service import TranslateEngine
from .script.init_db import safe_init_mysql
from .script.insert_init_db import insert_initial_data, set_auto_increment, insert_initial_settings
from .utils.response import APIResponse
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, DecodeError


def create_app(config_class=None):
    app = Flask(__name__)

    from .routes import register_routes
    # 加载配置
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    # 初始化数据库
    safe_init_mysql(app,'app/init.sql')
    # 初始化扩展（此时不注册路由）
    init_extensions(app)
    register_routes(api)

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

    # 初始化数据库
    with app.app_context():
        db.create_all()
        # 在这里调用 TranslateEngine
        # engine = TranslateEngine(task_id=1, app=app)
        # engine.execute()
        # 初始化默认配置
        # if not SystemSetting.query.filter_by(key='version').first():
        #     db.session.add(SystemSetting(key='version', value='business'))
        #     db.session.commit()
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