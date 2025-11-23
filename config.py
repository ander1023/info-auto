# config.py
import os
from datetime import datetime, timedelta


class Config:
    # JWT配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-key-change-in-production'
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ['cookies', 'headers']  # 允许从cookie和header获取token
    JWT_COOKIE_CSRF_PROTECT = False  # 简化开发，生产环境应该为True

    # 用户配置
    USERS = {
        'admin': 'password123'  # 用户名:密码 - 在生产环境中使用更复杂的密码
    }

    # 文件配置
    EXCEL_FILE = 'info-auto.xlsx'
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}