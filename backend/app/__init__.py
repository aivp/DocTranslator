# -*- coding: utf-8 -*-
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
    
    # 设置内存监控器
    from app.utils.memory_manager import setup_memory_monitor
    setup_memory_monitor(app)

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
        logger.error("Unhandled exception: " + str(e))
        logger.error("Traceback: " + traceback.format_exc())
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
                logger.warning("数据库连接失败 (尝试 " + str(attempt + 1) + "/" + str(max_retries) + "): " + str(e))
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
    
    # 启动时清理未完成的翻译任务（已禁用）
    # cleanup_incomplete_tasks(app)
    
    # 开发环境路由打印
    # if app.debug:
    #     with app.app_context():
    #         print("\n=== 已注册路由 ===")
    #         for rule in app.url_map.iter_rules():
    #             methods = ','.join(rule.methods)
    #             print(f"{rule.endpoint}: {methods} -> {rule}")
    #         print("===================\n")

    return app


# 全局标志，确保清理逻辑只执行一次
_cleanup_executed = False

def cleanup_incomplete_tasks(app):
    """清理未完成的翻译任务（服务重启时调用，只执行一次）"""
    global _cleanup_executed
    
    # 如果已经执行过，直接返回
    if _cleanup_executed:
        return
    
    _cleanup_executed = True
    
    import logging
    import os
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    try:
        with app.app_context():
            from app.models.translate import Translate
            from app.extensions import db
            
            # 定义合法的状态值（从模型定义中获取）
            VALID_STATUSES = ['none', 'changing', 'process', 'done', 'failed']
            
            # 查找processing或changing状态的任务
            incomplete_tasks = Translate.query.filter(
                Translate.status.in_(['process', 'changing']),
                Translate.deleted_flag == 'N'
            ).all()
            
            if not incomplete_tasks:
                logger.info("没有未完成的翻译任务需要清理")
                return
            
            logger.info(f"发现 {len(incomplete_tasks)} 个未完成的翻译任务，开始清理...")
            
            cleaned_count = 0
            for task in incomplete_tasks:
                try:
                    # 验证当前状态是否合法
                    if task.status not in VALID_STATUSES:
                        logger.warning(f"任务 {task.id} 状态异常: {task.status}，跳过处理")
                        continue
                    
                    # 将任务状态标记为失败，让用户可以重试
                    task.status = 'failed'
                    task.failed_reason = '服务重启，任务中断，请点击重试'
                    task.end_at = datetime.utcnow()
                    
                    # 清理临时文件
                    if task.target_filepath and os.path.exists(task.target_filepath):
                        try:
                            os.remove(task.target_filepath)
                            logger.info(f"已删除未完成的翻译结果文件: {task.target_filepath}")
                        except Exception as e:
                            logger.warning(f"删除翻译结果文件失败: {task.target_filepath} - {e}")
                    
                    # 清理临时目录（大文件PDF翻译可能产生的）
                    if task.origin_filepath:
                        base_dir = os.path.dirname(task.origin_filepath)
                        temp_dir_pattern = os.path.join(base_dir, 'temp_user_*')
                        
                        import glob
                        temp_dirs = glob.glob(temp_dir_pattern)
                        for temp_dir in temp_dirs:
                            try:
                                import shutil
                                shutil.rmtree(temp_dir, ignore_errors=True)
                                logger.info(f"已清理临时目录: {temp_dir}")
                            except Exception as e:
                                logger.warning(f"清理临时目录失败: {temp_dir} - {e}")
                    
                    cleaned_count += 1
                    logger.info(f"已清理未完成任务: {task.id} - {task.origin_filename}")
                    
                except Exception as e:
                    logger.error(f"清理任务 {task.id} 时出错: {str(e)}")
                    continue
            
            # 提交更改
            if cleaned_count > 0:
                db.session.commit()
                logger.info(f"清理完成，共处理 {cleaned_count} 个未完成任务")
            else:
                logger.info("没有需要清理的任务")
            
    except Exception as e:
        logger.error(f"清理未完成任务时出错: {str(e)}", exc_info=True)