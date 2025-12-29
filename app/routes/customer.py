import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from flask_mail import Message
from app import db, mail
from app.models.product import Product
from app.models.cart import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem

# 创建蓝图
customer = Blueprint('customer', __name__)


@customer.route('/')
def index():
    """首页（商品列表展示）"""
    products = Product.query.all()
    return render_template('customer/index.html', products=products)


@customer.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def cart_add(product_id):
    """添加商品到购物车"""
    product = Product.query.get_or_404(product_id)
    if product.stock <= 0:
        flash('该商品库存不足，无法添加到购物车', 'danger')
        return redirect(url_for('customer.index'))

    # 检查购物车中是否已存在该商品
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        # 已存在：增加数量（不超过库存）
        if cart_item.quantity + 1 > product.stock:
            flash('该商品库存不足，无法增加数量', 'danger')
            return redirect(url_for('customer.cart'))
        cart_item.quantity += 1
    else:
        # 不存在：创建新购物车商品
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=1
        )
        db.session.add(cart_item)

    # 保存到数据库
    try:
        db.session.commit()
        flash(f'已将《{product.name}》添加到购物车', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'添加购物车失败：{str(e)}', 'danger')

    return redirect(url_for('customer.cart'))


@customer.route('/cart')
@login_required
def cart():
    """查看购物车"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    # 计算购物车总金额
    total_amount = sum(item.total_price for item in cart_items)
    return render_template('customer/cart.html', cart_items=cart_items, total_amount=total_amount)


@customer.route('/cart/update/<int:cart_item_id>', methods=['POST'])
@login_required
def cart_update(cart_item_id):
    """更新购物车商品数量"""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id != current_user.id:
        flash('无权修改该购物车商品', 'danger')
        return redirect(url_for('customer.cart'))

    # 获取新数量
    new_quantity = int(request.form.get('quantity', 1))
    if new_quantity < 1:
        flash('商品数量不能小于1', 'danger')
        return redirect(url_for('customer.cart'))
    if new_quantity > cart_item.product.stock:
        flash('该商品库存不足，无法设置该数量', 'danger')
        return redirect(url_for('customer.cart'))

    # 更新数量
    cart_item.quantity = new_quantity
    try:
        db.session.commit()
        flash('购物车商品数量已更新', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新购物车失败：{str(e)}', 'danger')

    return redirect(url_for('customer.cart'))


@customer.route('/cart/delete/<int:cart_item_id>')
@login_required
def cart_delete(cart_item_id):
    """删除购物车中的商品"""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id != current_user.id:
        flash('无权删除该购物车商品', 'danger')
        return redirect(url_for('customer.cart'))

    # 删除商品
    try:
        db.session.delete(cart_item)
        db.session.commit()
        flash('已从购物车中删除该商品', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除购物车商品失败：{str(e)}', 'danger')

    return redirect(url_for('customer.cart'))


@customer.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """结算付款（模拟，不接入真实支付接口）"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('购物车为空，无法结算', 'danger')
        return redirect(url_for('customer.cart'))

    # 计算总金额
    total_amount = sum(item.total_price for item in cart_items)

    if request.method == 'POST':
        # 获取收货信息
        recipient_name = request.form.get('recipient_name')
        recipient_phone = request.form.get('recipient_phone')
        recipient_address = request.form.get('recipient_address')

        # 验证收货信息
        if not all([recipient_name, recipient_phone, recipient_address]):
            flash('请填写完整的收货信息', 'danger')
            return render_template('customer/checkout.html', cart_items=cart_items, total_amount=total_amount)

        # 1. 创建订单（生成唯一订单编号）
        order_no = f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}{uuid.uuid4().hex[:8]}'
        new_order = Order(
            user_id=current_user.id,
            order_no=order_no,
            total_amount=total_amount,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            recipient_address=recipient_address,
            status='shipped',  # 模拟付款成功，直接标记为已发货（简化流程）
            payment_time=datetime.utcnow(),
            ship_time=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.flush()  # 刷新会话，获取订单ID（不提交）

        # 2. 创建订单项，扣减商品库存
        for cart_item in cart_items:
            product = cart_item.product
            # 检查库存（防止并发问题）
            if product.stock < cart_item.quantity:
                db.session.rollback()
                flash(f'《{product.name}》库存不足，无法完成订单', 'danger')
                return redirect(url_for('customer.cart'))

            # 创建订单项
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                unit_price=product.price
            )
            db.session.add(order_item)

            # 扣减库存
            product.stock -= cart_item.quantity

        # 3. 清空当前用户购物车
        CartItem.query.filter_by(user_id=current_user.id).delete()

        # 4. 提交所有修改到数据库
        try:
            db.session.commit()
            # 5. 发送发货确认邮件
            send_order_confirmation_email(new_order)
            flash('订单提交成功，已发送发货确认邮件', 'success')
            return redirect(url_for('customer.order_success', order_no=order_no))
        except Exception as e:
            db.session.rollback()
            flash(f'订单提交失败：{str(e)}', 'danger')
            return redirect(url_for('customer.cart'))

    # GET请求：返回结算页面
    return render_template('customer/checkout.html', cart_items=cart_items, total_amount=total_amount)


def send_order_confirmation_email(order):
    """发送订单发货确认邮件"""
    subject = f'【购物网站】您的订单 {order.order_no} 已发货'
    recipients = [order.user.email]
    msg = Message(subject, recipients=recipients)

    # 邮件正文（纯文本，简化版）
    msg.body = f"""
尊敬的 {order.user.username}：

您好！您的订单已成功发货，订单详情如下：
订单编号：{order.order_no}
订单金额：¥{order.total_amount:.2f}
收件人：{order.recipient_name}
收件电话：{order.recipient_phone}
收件地址：{order.recipient_address}

感谢您的购买，祝您购物愉快！
    """

    # 发送邮件（生产环境需确保邮件配置正确）
    try:
        mail.send(msg)
    except Exception as e:
        print(f'发送邮件失败：{str(e)}')


@customer.route('/order/success/<order_no>')
@login_required
def order_success(order_no):
    """订单提交成功页面"""
    order = Order.query.filter_by(order_no=order_no, user_id=current_user.id).first_or_404()
    return render_template('customer/order_success.html', order=order)


@customer.route('/orders')
@login_required
def orders():
    """查看订单历史和状态"""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=orders)