from app import db


class CartItem(db.Model):
    """购物车商品模型（用户-商品的中间表，记录购物车商品数量）"""
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 关联用户ID
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)  # 关联商品ID
    quantity = db.Column(db.Integer, nullable=False, default=1)  # 商品数量

    def __repr__(self):
        return f'<CartItem User {self.user_id} - Product {self.product_id} ({self.quantity})>'

    @property
    def total_price(self):
        """计算该购物车商品的总价（数量*商品单价）"""
        return self.quantity * self.product.price