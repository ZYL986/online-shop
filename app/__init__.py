from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from app.config import Config

# 初始化数据库ORM
db = SQLAlchemy()
# 初始化用户登录管理
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # 未登录用户跳转的登录页面
login_manager.login_message_category = 'info'  # 登录提示消息类别
# 初始化邮件发送
mail = Mail()

def create_app(config_class=Config):
    """创建并初始化Flask应用实例"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # 注册蓝图（路由模块）
    from app.routes.auth import auth as auth_blueprint
    from app.routes.customer import customer as customer_blueprint
    from app.routes.admin import admin as admin_blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(customer_blueprint, url_prefix='/')  # 根路径为顾客端首页
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    # 应用上下文内创建数据库表
    with app.app_context():
        db.create_all()

    return app