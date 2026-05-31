"""推荐引擎：协同过滤 + 基于物品的推荐 + 浏览历史推荐"""
from app import db
from app.models.product import Product, ProductCategory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.tracking import BrowseLog
from sqlalchemy import func


def get_collaborative_recommendations(user_id, limit=6):
    """
    协同过滤推荐：找到相似用户，推荐他们买过但当前用户没买过的商品
    """
    # 当前用户购买过的商品ID
    bought = db.session.query(OrderItem.product_id).join(Order).filter(
        Order.user_id == user_id, Order.status != "cancelled"
    ).distinct().all()
    bought_ids = set(r.product_id for r in bought)

    if not bought_ids:
        return _fallback_popular(limit)

    # 找到也买过这些商品的其他用户
    similar_user_rows = db.session.query(Order.user_id).join(OrderItem).filter(
        OrderItem.product_id.in_(bought_ids),
        Order.user_id != user_id,
        Order.status != "cancelled"
    ).distinct().limit(50).all()

    similar_user_ids = [r.user_id for r in similar_user_rows]
    if not similar_user_ids:
        return _fallback_popular(limit)

    # 相似用户买过的商品（排除当前用户已买的）
    rec_rows = db.session.query(
        OrderItem.product_id,
        func.count(OrderItem.id).label("freq")
    ).join(Order).filter(
        Order.user_id.in_(similar_user_ids),
        ~OrderItem.product_id.in_(bought_ids) if bought_ids else True,
        Order.status != "cancelled"
    ).group_by(OrderItem.product_id).order_by(func.count(OrderItem.id).desc()).limit(limit).all()

    rec_ids = [r.product_id for r in rec_rows]
    if rec_ids:
        products = Product.query.filter(Product.id.in_(rec_ids)).all()
        id_order = {pid: i for i, pid in enumerate(rec_ids)}
        products.sort(key=lambda p: id_order.get(p.id, 99))
        return products

    return _fallback_popular(limit)


def get_also_bought_recommendations(product_id, limit=6):
    """
    "浏览过此商品的人也买了..." 推荐
    """
    # 找到买过此商品的用户
    user_rows = db.session.query(Order.user_id).join(OrderItem).filter(
        OrderItem.product_id == product_id,
        Order.status != "cancelled"
    ).distinct().limit(100).all()

    user_ids = [r.user_id for r in user_rows]
    if not user_ids:
        return _fallback_popular(limit)

    # 这些用户还买了什么
    rec_rows = db.session.query(
        OrderItem.product_id,
        func.count(OrderItem.id).label("freq")
    ).join(Order).filter(
        Order.user_id.in_(user_ids),
        OrderItem.product_id != product_id,
        Order.status != "cancelled"
    ).group_by(OrderItem.product_id).order_by(func.count(OrderItem.id).desc()).limit(limit).all()

    rec_ids = [r.product_id for r in rec_rows]
    if rec_ids:
        products = Product.query.filter(Product.id.in_(rec_ids)).all()
        id_order = {pid: i for i, pid in enumerate(rec_ids)}
        products.sort(key=lambda p: id_order.get(p.id, 99))
        return products

    return _fallback_popular(limit)


def get_browse_based_recommendations(user_id, limit=6):
    """基于浏览历史的推荐"""
    # 用户浏览过的商品类别
    viewed_cats = db.session.query(
        BrowseLog.category_id,
        func.count(BrowseLog.id).label("cnt")
    ).filter(
        BrowseLog.user_id == user_id,
        BrowseLog.category_id.isnot(None)
    ).group_by(BrowseLog.category_id).order_by(func.count(BrowseLog.id).desc()).first()

    if viewed_cats and viewed_cats.category_id:
        # 浏览过的商品ID
        viewed_ids = set(
            r[0] for r in db.session.query(BrowseLog.product_id).filter(
                BrowseLog.user_id == user_id, BrowseLog.product_id.isnot(None)
            ).all()
        )
        bought_rows = db.session.query(OrderItem.product_id).join(Order).filter(
            Order.user_id == user_id, Order.status != "cancelled"
        ).all()
        bought_ids = set(r.product_id for r in bought_rows)

        exclude_ids = viewed_ids | bought_ids
        products = Product.query.filter(
            Product.category_id == viewed_cats.category_id,
            ~Product.id.in_(exclude_ids) if exclude_ids else True
        ).order_by(Product.view_count.desc()).limit(limit).all()

        if products:
            return products

    return _fallback_popular(limit)


def get_user_profile(user_id):
    """生成或更新用户画像"""
    from app.models.tracking import UserProfile
    from app.models.user import User

    user = User.query.get(user_id)
    if not user:
        return None

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    # 总订单数和总消费
    orders = Order.query.filter_by(user_id=user_id).filter(Order.status != "cancelled").all()
    profile.total_orders = len(orders)
    profile.total_spent = sum(o.total_amount for o in orders)
    profile.avg_order_value = profile.total_spent / profile.total_orders if profile.total_orders > 0 else 0

    # 偏好类别
    cat_rows = db.session.query(
        ProductCategory.name,
        func.count(OrderItem.id).label("cnt")
    ).select_from(Product).join(OrderItem).join(Order).join(
        ProductCategory, Product.category_id == ProductCategory.id, isouter=True
    ).filter(
        Order.user_id == user_id,
        Order.status != "cancelled"
    ).group_by(ProductCategory.name).order_by(func.count(OrderItem.id).desc()).first()

    if cat_rows:
        profile.favorite_category_name = cat_rows.name

    # 地域
    profile.region = user.region

    # 购买力
    if profile.total_spent > 10000:
        profile.purchasing_power = "high"
    elif profile.total_spent > 3000:
        profile.purchasing_power = "medium"
    else:
        profile.purchasing_power = "low"

    # 浏览数
    profile.browse_count = BrowseLog.query.filter_by(user_id=user_id).count()

    # 最近购买
    last_order = Order.query.filter_by(user_id=user_id).filter(Order.status != "cancelled").order_by(
        Order.created_at.desc()).first()
    if last_order:
        profile.last_purchase_date = last_order.created_at

    db.session.commit()
    return profile


def _fallback_popular(limit):
    """后备策略：返回热门商品"""
    return Product.query.order_by(Product.view_count.desc()).limit(limit).all()
