#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI 入口文件
用于 Gunicorn 等 WSGI 服务器启动应用
"""
from flask_cors import CORS
from app import create_app

# 创建 Flask 应用实例
app = create_app()

# 配置 CORS（如果需要）
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": "*"
    }
})

