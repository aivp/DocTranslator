
from typing import List, Dict, Any
import pymysql
import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 简单的连接池实现
class SimpleConnectionPool:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'dt-mysql'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USERNAME', 'dtuser'),
            'password': os.getenv('DB_PASSWORD', 'dtpwd'),
            'database': os.getenv('DB_DATABASE', 'doctranslator'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = pymysql.connect(**self.connection_params)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def get_status(self):
        """获取连接池状态"""
        return {
            "type": "SimpleConnectionPool",
            "status": "active",
            "connection_params": {
                "host": self.connection_params['host'],
                "port": self.connection_params['port'],
                "database": self.connection_params['database']
            }
        }
    
    def _create_connection(self):
        """创建单个连接（兼容性方法）"""
        return pymysql.connect(**self.connection_params)

# 全局连接池实例
_pool_instance = None

def get_simple_pool():
    """获取简单连接池实例"""
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = SimpleConnectionPool()
    return _pool_instance

def get(sql: str, *params) -> Dict[str, Any]:
    """获取单条记录"""
    try:
        pool = get_simple_pool()
        with pool.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql, params)
            result = cursor.fetchone()
            cursor.close()
            return result or {}
    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        return {}

def get_all(sql: str, *params) -> List[Dict[str, Any]]:
    """获取多条记录"""
    try:
        pool = get_simple_pool()
        with pool.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql, params)
            results = cursor.fetchall()
            cursor.close()
            return results or []
    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        return []

def execute(sql: str, *params) -> bool:
    """
    执行SQL语句（INSERT, UPDATE, DELETE）
    
    注意：此函数每次调用都会创建新连接，适合低频调用。
    如果需要频繁调用，考虑使用批量操作或连接复用。
    """
    try:
        pool = get_simple_pool()
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
    except Exception as e:
        logger.error(f"❌ 执行SQL失败: {e}")
        return False

def health_check() -> Dict[str, Any]:
    """健康检查"""
    try:
        pool = get_simple_pool()
        with pool.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            cursor.close()
            return {"status": "healthy", "result": result}
    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        return {"status": "unhealthy", "error": str(e)}

def get_status() -> Dict[str, Any]:
    """获取状态"""
    try:
        pool = get_simple_pool()
        return pool.get_status()
    except Exception as e:
        return {"error": str(e)}

# 兼容性函数
def get_conn():
    logger.warning("⚠️ 使用过时的get_conn()")
    pool = get_simple_pool()
    return pool._create_connection()

def get_conn1():
    logger.warning("⚠️ 使用过时的get_conn1()")
    return get_conn()

if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 简化Docker连接池测试...")
    
    # 健康检查
    health = health_check()
    print(f"🏥 健康检查: {health}")
    
    # 基本查询
    result = get("SELECT 1 as test")
    print(f"✅ 查询测试: {result}")
    
    # 状态检查
    status = get_status()
    print(f"📊 状态: {status}")
    
    print("🎉 简化连接池测试完成！")
