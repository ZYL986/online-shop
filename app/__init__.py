from flask import Flask, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from app.config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
mail = Mail()


def create_app(config_class=Config):
    """创建并初始化Flask应用实例"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # 注册蓝图
    from app.routes.auth import auth as auth_blueprint
    from app.routes.customer import customer as customer_blueprint
    from app.routes.admin import admin as admin_blueprint
    from app.routes.analytics import analytics as analytics_blueprint

    app.register_blueprint(auth_blueprint, url_prefix="/auth")
    app.register_blueprint(customer_blueprint, url_prefix="/")
    app.register_blueprint(admin_blueprint, url_prefix="/admin")
    app.register_blueprint(analytics_blueprint, url_prefix="/analytics")

    # 反爬虫中间件
    from app.utils.anti_crawler import anti_crawler_middleware
    app.before_request(anti_crawler_middleware)

    # 429 错误处理
    @app.errorhandler(429)
    def too_many_requests(e):
        return abort(429, description=str(e.description))

    # 创建数据库表
    with app.app_context():
        db.create_all()

    return app
