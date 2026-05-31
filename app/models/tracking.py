from datetime import datetime
from app import db

class BrowseLog(db.Model):
    """用户浏览行为日志"""
    __tablename__ = "browse_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("product_categories.id"), nullable=True)
    action = db.Column(db.String(32), nullable=False, default="view")
    duration_seconds = db.Column(db.Integer, default=0)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BrowseLog user={self.user_id} product={self.product_id} action={self.action}>"


class LoginLog(db.Model):
    """用户登录日志"""
    __tablename__ = "login_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<LoginLog user={self.user_id} success={self.success}>"


class OperationLog(db.Model):
    """管理员/销售人员操作日志"""
    __tablename__ = "operation_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text, nullable=True)
    target_type = db.Column(db.String(32), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<OperationLog user={self.user_id} action={self.action}>"


class UserProfile(db.Model):
    """用户画像数据"""
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    avg_order_value = db.Column(db.Float, default=0.0)
    favorite_category_id = db.Column(db.Integer, db.ForeignKey("product_categories.id"), nullable=True)
    favorite_category_name = db.Column(db.String(64), nullable=True)
    purchase_frequency_days = db.Column(db.Float, nullable=True)
    last_purchase_date = db.Column(db.DateTime, nullable=True)
    browse_count = db.Column(db.Integer, default=0)
    cart_abandon_count = db.Column(db.Integer, default=0)
    region = db.Column(db.String(64), nullable=True)
    purchasing_power = db.Column(db.String(16), default="medium")
    preference_tags = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("profile", uselist=False))
    favorite_category = db.relationship("ProductCategory")

    def __repr__(self):
        return f"<UserProfile user={self.user_id}>"
