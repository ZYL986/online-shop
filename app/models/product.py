from datetime import datetime
from app import db

class ProductCategory(db.Model):
    """商品类别模型"""
    __tablename__ = "product_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="category", lazy="dynamic")

    def __repr__(self):
        return f"<ProductCategory {self.name}>"

class Product(db.Model):
    """商品模型"""
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_filename = db.Column(db.String(256), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("product_categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)

    cart_items = db.relationship("CartItem", backref="product", lazy="dynamic", cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem", backref="product", lazy="dynamic", cascade="all, delete-orphan")
    browse_logs = db.relationship("BrowseLog", backref="product", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product {self.name}>"
