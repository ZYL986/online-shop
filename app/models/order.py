from datetime import datetime
from app import db

class Order(db.Model):
    """订单模型"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 关联用户ID
    order_no = db.Column(db.String(32), unique=True, nullable=False)  # 订单编号（唯一）
    total_amount = db.Column(db.Float, nullable=False, default=0.0)  # 订单总金额
    recipient_name = db.Column(db.String(64), nullable=False)  # 收件人姓名
    recipient_phone = db.Column(db.String(20), nullable=False)  # 收件人手机号
    recipient_address = db.Column(db.Text, nullable=False)  # 收件人地址
    status = db.Column(db.String(32), nullable=False, default='pending')  # 订单状态：pending(待付款)、shipped(已发货)、completed(已完成)、cancelled(已取消)
    payment_time = db.Column(db.DateTime, nullable=True)  # 付款时间
    ship_time = db.Column(db.DateTime, nullable=True)  # 发货时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 订单创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 订单更新时间

    # 关联关系：一个订单对应多个订单项
    order_items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Order {self.order_no} - User {self.user_id}>'