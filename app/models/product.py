from datetime import datetime
from app import db

class Product(db.Model):
    """商品模型"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)  # 商品名称
    description = db.Column(db.Text, nullable=True)   # 商品描述
    price = db.Column(db.Float, nullable=False)       # 商品价格
    stock = db.Column(db.Integer, nullable=False, default=0)  # 商品库存
    image_filename = db.Column(db.String(256), nullable=True)  # 商品图片文件名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 更新时间

    # 关联关系：一个商品对应多个购物车商品、多个订单项
    cart_items = db.relationship('CartItem', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Product {self.name}>'