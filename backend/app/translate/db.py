import sqlite3
from urllib.parse import urlparse

import pymysql
import os
from dotenv import load_dotenv, find_dotenv
from threading import Lock

_ = load_dotenv(find_dotenv()) # read local .env file

def get_conn():
    try:
        # 获取数据库 URL
        db_url = os.environ.get('PROD_DATABASE_URL')
        if not db_url:
            raise ValueError("Database URL not found in environment variables.")

        # 判断是否是 SQLite 链接
        if db_url.startswith('sqlite:///'):
            # 保留原有的 SQLite 逻辑
            sqlite_db_path = db_url[len('sqlite:///'):]
            conn = sqlite3.connect(sqlite_db_path)
            print('数据库链接')
            # conn = sqlite3.connect(db_url)
            return conn

        # 判断是否是 MySQL 链接
        elif db_url.startswith('mysql+pymysql://'):
            # 解析 MySQL URL
            parsed_url = urlparse(db_url)
            mysql_host = parsed_url.hostname
            mysql_port = parsed_url.port or 3306  # 默认端口 3306
            mysql_db = parsed_url.path.lstrip('/')
            mysql_user = parsed_url.username
            mysql_password = parsed_url.password

            # 连接到 MySQL 数据库
            conn = pymysql.connect(
                host=mysql_host,
                port=mysql_port,
                user=mysql_user,
                password=mysql_password,
                db=mysql_db,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return conn

        else:
            raise ValueError(f"Unsupported database URL: {db_url}")

    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise



def get_conn1():
    mysql_host=os.environ['DB_HOST']
    mysql_port=os.environ['DB_PORT']
    mysql_db=os.environ['DB_DATABASE']
    mysql_user=os.environ['DB_USERNAME']
    mysql_password=os.environ['DB_PASSWORD']
    return pymysql.connect(host=mysql_host, port=int(mysql_port), user=mysql_user, passwd=mysql_password, db=mysql_db, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

def execute(sql, *params):
    conn = get_conn()
    lock=Lock()
    lock.acquire()
    cursor=conn.cursor() 
    try:               
        cursor.execute(sql, params)
        conn.commit()
        lock.release()
        cursor.close()
        conn.close()
    except:
        lock.release()
        conn.rollback()


def get(sql, *params):
    conn=get_conn()
    lock=Lock()
    lock.acquire()
    try:
        cursor=conn.cursor(cursor=pymysql.cursors.DictCursor)        
        cursor.execute(sql, params)
        result=cursor.fetchone()
        lock.release()
        cursor.close()
        conn.close()
        return result
    except:
        lock.release()
        return []

def get_all(sql, *params):
    conn=get_conn()
    lock=Lock()
    lock.acquire()
    try:
        cursor=conn.cursor(cursor=pymysql.cursors.DictCursor)        
        cursor.execute(sql, params)
        result=cursor.fetchall()
        lock.release()
        cursor.close()
        conn.close()
        return result
    except:
        lock.release()
        return []
