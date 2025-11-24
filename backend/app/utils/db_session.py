# -*- coding: utf-8 -*-
"""
数据库会话管理工具
提供统一的会话管理和异常处理装饰器
"""
from functools import wraps
from flask import current_app
from app.extensions import db
import logging

logger = logging.getLogger(__name__)


def with_db_session(func):
    """
    确保数据库会话正确管理的装饰器
    
    使用方式:
        @with_db_session
        def my_api_function():
            # 数据库操作
            db.session.add(...)
            # 不需要手动 commit，装饰器会自动处理
            return result
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # 如果没有异常，自动提交
            db.session.commit()
            return result
        except Exception as e:
            # 发生异常时回滚
            db.session.rollback()
            logger.error(f"数据库操作失败: {str(e)}", exc_info=True)
            raise
        finally:
            # 确保会话被清理（Flask-SQLAlchemy 会自动处理，但显式调用更安全）
            # 注意：不要在这里调用 db.session.remove()，因为 Flask 的 teardown 会处理
            pass
    return wrapper


def with_db_context(func):
    """
    为后台线程提供数据库上下文的装饰器
    
    使用方式:
        @with_db_context
        def background_task():
            # 在后台线程中执行，自动创建应用上下文
            task = Translate.query.get(task_id)
            # ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        app = current_app._get_current_object()
        with app.app_context():
            try:
                result = func(*args, **kwargs)
                db.session.commit()
                return result
            except Exception as e:
                db.session.rollback()
                logger.error(f"后台任务数据库操作失败: {str(e)}", exc_info=True)
                raise
            finally:
                # 后台线程中需要显式清理会话
                db.session.remove()
    return wrapper


def safe_db_operation(operation_func, *args, **kwargs):
    """
    安全执行数据库操作的上下文管理器
    
    使用方式:
        def update_task_status(task_id, status):
            def _update():
                task = Translate.query.get(task_id)
                task.status = status
                db.session.add(task)
            
            safe_db_operation(_update)
    """
    try:
        result = operation_func(*args, **kwargs)
        db.session.commit()
        return result
    except Exception as e:
        db.session.rollback()
        logger.error(f"数据库操作失败: {str(e)}", exc_info=True)
        raise
    finally:
        # 在后台线程中需要清理，但在请求上下文中不需要
        # Flask 的 teardown 会自动处理请求上下文
        pass

