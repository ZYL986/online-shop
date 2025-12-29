import os
from dotenv import load_dotenv

# 加载环境变量（本地开发可创建.env文件存储敏感信息）
load_dotenv()


class Config:
    """项目基础配置"""
    # Flask密钥（用于会话加密、CSRF保护，可自定义随机字符串）
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_123456_abcdef')

    # MySQL数据库配置（格式：mysql+pymysql://用户名:密码@主机:端口/数据库名）
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'mysql+pymysql://root:789789asd@localhost:3306/online_shopping')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 关闭不必要的数据库修改跟踪

    # 邮件发送配置（以QQ邮箱为例，需开启SMTP服务并获取授权码）
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '1175345276@qq.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'medythqvuyorjjhe')
    MAIL_DEFAULT_SENDER = MAIL_USERNAME