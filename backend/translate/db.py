# -*- coding: utf-8 -*-
"""
Docker环境优化的数据库操作模块
使用简化版连接池提供高可用性和高性能的数据库操作
"""
import logging
import pymysql
from typing import Optional, List, Dict, Any, Union

# 配置日志
logger = logging.getLogger(__name__)

# 使用简化版Docker连接池
from .db_simple import (
    get_simple_pool, 
    execute, 
    get, 
    get_all, 
    health_check, 
    get_status as get_pool_status,
    get_conn,
    get_conn1
)

def get_database_pool():
    """获取数据库连接池"""
    return get_simple_pool()

logger.info("🐳 使用简化Docker数据库连接池")

def execute_with_cursor(callback_func) -> Any:
    """
    执行自定义数据库操作（使用游标）
    
    Args:
        callback_func: 回调函数，接收cursor和conn参数
    
    Returns:
        回调函数的返回值
    """
    try:
        pool = get_database_pool()
        with pool.get_connection() as conn:
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor if 'pymysql' in str(type(conn)) else None)
            try:
                return callback_func(cursor, conn)
            finally:
                cursor.close()
                
    except Exception as e:
        logger.error(f"❌ 自定义数据库操作失败: {e}")
        raise

def execute_batch(sql_template: str, param_list: List[tuple], batch_size: int = 1000) -> bool:
    """
    批量执行SQL语句
    
    Args:
        sql_template: SQL模板
        param_list: 参数列表[(param1, param2, ...), ...]
        batch_size: 批次大小
    
    Returns:
        bool: 是否成功执行
    """
    try:
        pool = get_database_pool()
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # 分批处理
                for i in range(0, len(param_list), batch_size):
                    batch_params = param_list[i:i + batch_size]
                    cursor.executemany(sql_template, batch_params)
                
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.error(f"❌ 批量SQL执行失败: {e}")
                raise
            finally:
                cursor.close()
                
    except Exception as e:
        logger.error(f"❌ 批量数据库操作失败: {e}")
        return False

def transaction(callback_func) -> Any:
    """
    在事务中执行操作
    
    Args:
        callback_func: 回调函数，接收cursor和conn参数
    
    Returns:
        回调函数的返回值
    """
    try:
        pool = get_database_pool()
        with pool.get_connection() as conn:
            cursor = conn.cursor(cursor=pymysql.cursors.DictCursor if 'pymysql' in str(type(conn)) else None)
            try:
                conn.begin()  # 开始事务
                result = callback_func(cursor, conn)
                conn.commit()  # 提交事务
                return result
            except Exception as e:
                conn.rollback()  # 回滚事务
                logger.error(f"❌ 事务执行失败: {e}")
                raise
            finally:
                cursor.close()
                
    except Exception as e:
        logger.error(f"❌ 事务操作失败: {e}")
        raise

# 兼容性函数（保持向后兼容）
def init_db_pool():
    """初始化数据库连接池"""
    try:
        pool = get_database_pool()
        logger.info("✅ Docker数据库连接池初始化成功")
        
        # 执行健康检查
        health = health_check()
        logger.info(f"🐳 Docker数据库健康状态: {health}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Docker数据库连接池初始化失败: {e}")
        return False

def test_docker_db():
    """测试Docker数据库功能"""
    logger.info("🐳 开始Docker数据库功能测试...")
    
    try:
        # 测试健康检查
        health = health_check()
        logger.info(f"🏥 Docker健康检查: {health}")
        
        if health.get('status') != 'healthy':
            raise Exception(f"Docker数据库健康检查失败: {health}")
        
        # 测试基本查询
        result = get('SELECT 1 as docker_test')
        logger.info(f'✅ Docker基本查询测试: {result}')
        
        if result and result.get('docker_test') == 1:
            logger.info("🎉 Docker环境数据库功能测试全部通过！")
            return True
        else:
            raise Exception(f"Docker基本查询失败: {result}")
            
    except Exception as e:
        logger.error(f"❌ Docker数据库测试失败: {e}")
        return False

# 导入pymysql用于类型检查
import pymysql

# 🔄 初始化连接池
def init_db_pool():
    """初始化数据库连接池"""
    try:
        get_database_pool()
        logger.info("✅ 数据库连接池初始化成功")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接池初始化失败: {e}")
        return False

if __name__ == "__main__":
    # 🔍 测试连接池功能
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 开始测试数据库连接池...")
    
    # 测试健康检查
    health = health_check()
    print(f"🏥 健康检查结果: {health}")
    
    # 测试连接池状态
    status = get_pool_status()
    print(f"📊 连接池状态: {status}")
    
    # 测试基本操作
    try:
        result = get("SELECT 1 as test")
        print(f"✅ 基本查询测试: {result}")
        
        print("🎉 数据库连接池测试完成！")
    except Exception as e:
        print(f"❌ 测试失败: {e}")