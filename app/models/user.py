from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

class User(UserMixin, db.Model):
    """用户模型（继承UserMixin实现Flask-Login所需方法）"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    region = db.Column(db.String(64), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_sales = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cart_items = db.relationship("CartItem", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    browse_logs = db.relationship("BrowseLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    login_logs = db.relationship("LoginLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    operation_logs = db.relationship("OperationLog", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role(self):
        if self.is_admin:
            return "admin"
        if self.is_sales:
            return "sales"
        return "customer"

    @property
    def total_spent(self):
        from app.models.order import Order
        result = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.user_id == self.id,
            Order.status != "cancelled"
        ).scalar()
        return result or 0.0

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
