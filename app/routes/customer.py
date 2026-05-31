import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from flask_mail import Message
from app import db, mail
from app.models.product import Product, ProductCategory
from app.models.cart import CartItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.utils.tracking import track_browse
from app.utils.recommendation import (
    get_collaborative_recommendations,
    get_also_bought_recommendations,
    get_browse_based_recommendations,
    get_user_profile,
)

customer = Blueprint("customer", __name__)


@customer.route("/")
def index():
    """首页（商品列表展示）"""
    category_id = request.args.get("category", type=int)
    search = request.args.get("search", "")

    query = Product.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Product.name.contains(search))

    products = query.order_by(Product.updated_at.desc()).all()
    categories = ProductCategory.query.all()
    return render_template("customer/index.html", products=products, categories=categories,
                           current_category=category_id, search=search)


@customer.route("/product/<int:product_id>")
def product_detail(product_id):
    """商品详情页"""
    product = Product.query.get_or_404(product_id)
    product.view_count = (product.view_count or 0) + 1

    user_id = current_user.id if current_user.is_authenticated else None
    track_browse(user_id=user_id, product_id=product_id,
                 category_id=product.category_id, action="view")

    db.session.commit()

    # 推荐："浏览过此商品的人也买了..."
    also_bought = get_also_bought_recommendations(product_id, limit=6)

    # 浏览过此商品的用户还浏览了
    from app.models.tracking import BrowseLog
    from sqlalchemy import func
    viewed_users = db.session.query(BrowseLog.user_id).filter(
        BrowseLog.product_id == product_id, BrowseLog.user_id.isnot(None)
    ).distinct().limit(50).all()
    viewed_user_ids = [r.user_id for r in viewed_users]
    related_products = []
    if viewed_user_ids:
        related_rows = db.session.query(
            BrowseLog.product_id, func.count(BrowseLog.id).label("cnt")
        ).filter(
            BrowseLog.user_id.in_(viewed_user_ids),
            BrowseLog.product_id != product_id,
            BrowseLog.product_id.isnot(None)
        ).group_by(BrowseLog.product_id).order_by(func.count(BrowseLog.id).desc()).limit(6).all()
        related_ids = [r.product_id for r in related_rows]
        if related_ids:
            related_products = Product.query.filter(Product.id.in_(related_ids)).all()
            id_order = {pid: i for i, pid in enumerate(related_ids)}
            related_products.sort(key=lambda p: id_order.get(p.id, 99))

    return render_template("customer/product_detail.html", product=product,
                           also_bought=also_bought, related_products=related_products)


@customer.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def cart_add(product_id):
    """添加商品到购物车"""
    product = Product.query.get_or_404(product_id)
    if product.stock <= 0:
        flash("该商品库存不足，无法添加到购物车", "danger")
        return redirect(url_for("customer.index"))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        if cart_item.quantity + 1 > product.stock:
            flash("该商品库存不足，无法增加数量", "danger")
            return redirect(url_for("customer.cart"))
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)

    # 跟踪加入购物车行为
    track_browse(user_id=current_user.id, product_id=product_id,
                 category_id=product.category_id, action="add_to_cart")

    try:
        db.session.commit()
        flash(f"已将《{product.name}》添加到购物车", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"添加购物车失败：{str(e)}", "danger")

    return redirect(url_for("customer.cart"))


@customer.route("/cart")
@login_required
def cart():
    """查看购物车"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_amount = sum(item.total_price for item in cart_items)

    # 推荐
    recs = get_browse_based_recommendations(current_user.id, limit=4) if cart_items else []

    return render_template("customer/cart.html", cart_items=cart_items,
                           total_amount=total_amount, recommendations=recs)


@customer.route("/cart/update/<int:cart_item_id>", methods=["POST"])
@login_required
def cart_update(cart_item_id):
    """更新购物车商品数量"""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id != current_user.id:
        flash("无权修改该购物车商品", "danger")
        return redirect(url_for("customer.cart"))

    new_quantity = int(request.form.get("quantity", 1))
    if new_quantity < 1:
        flash("商品数量不能小于1", "danger")
        return redirect(url_for("customer.cart"))
    if new_quantity > cart_item.product.stock:
        flash("该商品库存不足，无法设置该数量", "danger")
        return redirect(url_for("customer.cart"))

    cart_item.quantity = new_quantity
    try:
        db.session.commit()
        flash("购物车商品数量已更新", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新购物车失败：{str(e)}", "danger")

    return redirect(url_for("customer.cart"))


@customer.route("/cart/delete/<int:cart_item_id>")
@login_required
def cart_delete(cart_item_id):
    """删除购物车中的商品"""
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id != current_user.id:
        flash("无权删除该购物车商品", "danger")
        return redirect(url_for("customer.cart"))

    try:
        db.session.delete(cart_item)
        db.session.commit()
        flash("已从购物车中删除该商品", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"删除购物车商品失败：{str(e)}", "danger")

    return redirect(url_for("customer.cart"))


@customer.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """结算付款"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("购物车为空，无法结算", "danger")
        return redirect(url_for("customer.cart"))

    total_amount = sum(item.total_price for item in cart_items)

    if request.method == "POST":
        recipient_name = request.form.get("recipient_name")
        recipient_phone = request.form.get("recipient_phone")
        recipient_address = request.form.get("recipient_address")

        if not all([recipient_name, recipient_phone, recipient_address]):
            flash("请填写完整的收货信息", "danger")
            return render_template("customer/checkout.html", cart_items=cart_items, total_amount=total_amount)

        order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8]}"
        new_order = Order(
            user_id=current_user.id,
            order_no=order_no,
            total_amount=total_amount,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            recipient_address=recipient_address,
            status="shipped",
            payment_time=datetime.utcnow(),
            ship_time=datetime.utcnow()
        )
        db.session.add(new_order)
        db.session.flush()

        for cart_item in cart_items:
            product = cart_item.product
            if product.stock < cart_item.quantity:
                db.session.rollback()
                flash(f"《{product.name}》库存不足，无法完成订单", "danger")
                return redirect(url_for("customer.cart"))

            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                unit_price=product.price
            )
            db.session.add(order_item)
            product.stock -= cart_item.quantity

        CartItem.query.filter_by(user_id=current_user.id).delete()

        try:
            db.session.commit()
            send_order_confirmation_email(new_order)
            # 更新用户画像
            get_user_profile(current_user.id)
            flash("订单提交成功，已发送发货确认邮件", "success")
            return redirect(url_for("customer.order_success", order_no=order_no))
        except Exception as e:
            db.session.rollback()
            flash(f"订单提交失败：{str(e)}", "danger")
            return redirect(url_for("customer.cart"))

    return render_template("customer/checkout.html", cart_items=cart_items, total_amount=total_amount)


def send_order_confirmation_email(order):
    """发送订单发货确认邮件"""
    subject = f"【购物网站】您的订单 {order.order_no} 已发货"
    recipients = [order.user.email]
    msg = Message(subject, recipients=recipients)
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
    try:
        mail.send(msg)
    except Exception as e:
        print(f"发送邮件失败：{str(e)}")


@customer.route("/order/success/<order_no>")
@login_required
def order_success(order_no):
    """订单提交成功页面"""
    order = Order.query.filter_by(order_no=order_no, user_id=current_user.id).first_or_404()
    return render_template("customer/order_success.html", order=order)


@customer.route("/orders")
@login_required
def orders():
    """查看订单历史和状态"""
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("customer/orders.html", orders=orders)


@customer.route("/recommendations")
@login_required
def recommendations():
    """个性化推荐页面"""
    collab_recs = get_collaborative_recommendations(current_user.id, limit=8)
    browse_recs = get_browse_based_recommendations(current_user.id, limit=8)
    profile = get_user_profile(current_user.id)
    return render_template("customer/recommendations.html",
                           collab_recs=collab_recs,
                           browse_recs=browse_recs,
                           profile=profile)


@customer.route("/profile")
@login_required
def user_profile_page():
    """用户画像页面"""
    profile = get_user_profile(current_user.id)
    return render_template("customer/profile.html", profile=profile, user=current_user)
