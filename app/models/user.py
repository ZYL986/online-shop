from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

class User(UserMixin, db.Model):
    """用户模型（继承UserMixin实现Flask-Login所需方法）"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)  # 用户名（唯一）
    email = db.Column(db.String(120), unique=True, nullable=False)   # 邮箱（唯一，用于登录、收邮件）
    password_hash = db.Column(db.String(128), nullable=False)         # 密码哈希（不存储明文）
    phone = db.Column(db.String(20), nullable=True)                   # 手机号（可选）
    address = db.Column(db.Text, nullable=True)                       # 收货地址（可选）
    is_admin = db.Column(db.Boolean, default=False)                   # 是否为管理员（默认否）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)      # 创建时间

    # 关联关系：一个用户对应多个购物车商品、多个订单
    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """设置密码（生成哈希值）"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码（对比哈希值）"""
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login回调：根据用户ID加载用户"""
    return User.query.get(int(user_id))