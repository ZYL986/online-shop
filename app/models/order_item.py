from app import db


class OrderItem(db.Model):
    """订单项模型（订单-商品的中间表，记录订单中商品的数量和购买单价）"""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)  # 关联订单ID
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)  # 关联商品ID
    quantity = db.Column(db.Integer, nullable=False, default=1)  # 商品数量
    unit_price = db.Column(db.Float, nullable=False)  # 购买时的商品单价（防止后续商品价格变动影响订单）

    def __repr__(self):
        return f'<OrderItem Order {self.order_id} - Product {self.product_id} ({self.quantity})>'

    @property
    def total_price(self):
        """计算该订单项的总价（数量*购买单价）"""
        return self.quantity * self.unit_price