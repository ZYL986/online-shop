from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from app import db
from app.models.product import Product, ProductCategory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.tracking import BrowseLog, LoginLog, OperationLog, UserProfile
from app.models.user import User
from sqlalchemy import func, extract, and_

analytics = Blueprint("analytics", __name__)


def admin_or_sales_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "unauthorized"}), 401
        if not (current_user.is_admin or current_user.is_sales):
            return jsonify({"error": "forbidden"}), 403
        return func(*args, **kwargs)
    return wrapper


# ==================== ECharts 数据 API ====================

@analytics.route("/data/sales_trend")
@login_required
@admin_or_sales_required
def sales_trend_data():
    """销售趋势数据 (日/周/月)"""
    period = request.args.get("period", "daily")
    days = int(request.args.get("days", 30))

    now = datetime.utcnow()
    start = now - timedelta(days=days)

    if period == "daily":
        query = db.session.query(
            func.date(Order.created_at).label("label"),
            func.sum(Order.total_amount).label("amount"),
            func.count(Order.id).label("count")
        ).filter(
            Order.created_at >= start,
            Order.status != "cancelled"
        ).group_by(func.date(Order.created_at)).order_by("label")
    elif period == "weekly":
        query = db.session.query(
            func.yearweek(Order.created_at).label("label"),
            func.sum(Order.total_amount).label("amount"),
            func.count(Order.id).label("count")
        ).filter(
            Order.created_at >= start,
            Order.status != "cancelled"
        ).group_by(func.yearweek(Order.created_at)).order_by("label")
    elif period == "monthly":
        query = db.session.query(
            func.date_format(Order.created_at, "%Y-%m").label("label"),
            func.sum(Order.total_amount).label("amount"),
            func.count(Order.id).label("count")
        ).filter(
            Order.created_at >= start,
            Order.status != "cancelled"
        ).group_by(func.date_format(Order.created_at, "%Y-%m")).order_by("label")
    else:
        return jsonify({"error": "invalid period"}), 400

    rows = query.all()
    dates = [str(r.label) for r in rows]
    amounts = [float(r.amount or 0) for r in rows]
    counts = [int(r.count or 0) for r in rows]

    return jsonify({"dates": dates, "amounts": amounts, "counts": counts})


@analytics.route("/data/sales_ranking")
@login_required
@admin_or_sales_required
def sales_ranking_data():
    """商品销售排行榜"""
    days = int(request.args.get("days", 30))
    limit = int(request.args.get("limit", 10))
    start = datetime.utcnow() - timedelta(days=days)

    rows = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label("qty"),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label("sales")
    ).join(OrderItem).join(Order).filter(
        Order.created_at >= start,
        Order.status != "cancelled"
    ).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(limit).all()

    return jsonify({
        "names": [r.name for r in rows],
        "quantities": [int(r.qty or 0) for r in rows],
        "sales": [float(r.sales or 0) for r in rows]
    })


@analytics.route("/data/category_distribution")
@login_required
@admin_or_sales_required
def category_distribution_data():
    """商品类别销售分布"""
    days = int(request.args.get("days", 30))
    start = datetime.utcnow() - timedelta(days=days)

    rows = db.session.query(
        ProductCategory.name,
        func.sum(OrderItem.quantity * OrderItem.unit_price).label("sales"),
        func.sum(OrderItem.quantity).label("qty")
    ).select_from(Product).join(OrderItem).join(Order).join(
        ProductCategory, Product.category_id == ProductCategory.id, isouter=True
    ).filter(
        Order.created_at >= start,
        Order.status != "cancelled"
    ).group_by(ProductCategory.name).all()

    names = [r.name or "Uncategorized" for r in rows]
    sales = [float(r.sales or 0) for r in rows]

    return jsonify({"names": names, "sales": sales})


@analytics.route("/data/user_region")
@login_required
@admin_or_sales_required
def user_region_data():
    """用户地域分布"""
    rows = db.session.query(
        User.region,
        func.count(User.id).label("cnt")
    ).filter(User.region.isnot(None)).group_by(User.region).all()

    return jsonify({
        "regions": [r.region or "Unknown" for r in rows],
        "counts": [int(r.cnt) for r in rows]
    })


@analytics.route("/data/purchasing_power")
@login_required
@admin_or_sales_required
def purchasing_power_data():
    """用户购买力分布"""
    rows = db.session.query(
        UserProfile.purchasing_power,
        func.count(UserProfile.id).label("cnt")
    ).group_by(UserProfile.purchasing_power).all()

    power_map = {"low": "Low", "medium": "Medium", "high": "High"}
    return jsonify({
        "categories": [power_map.get(r.purchasing_power, "Unknown") for r in rows],
        "counts": [int(r.cnt) for r in rows]
    })


@analytics.route("/data/anomaly_check")
@login_required
@admin_or_sales_required
def anomaly_check_data():
    """异常销售检测"""
    days = int(request.args.get("days", 7))
    threshold = float(request.args.get("threshold", 2.0))
    start = datetime.utcnow() - timedelta(days=days)

    # 计算每日销售均值与标准差
    daily_sales = db.session.query(
        func.date(Order.created_at).label("d"),
        func.sum(Order.total_amount).label("amt")
    ).filter(
        Order.created_at >= start,
        Order.status != "cancelled"
    ).group_by(func.date(Order.created_at)).all()

    amounts = [float(r.amt or 0) for r in daily_sales]
    if len(amounts) < 2:
        return jsonify({"anomalies": [], "message": "Not enough data"})

    mean_val = sum(amounts) / len(amounts)
    variance = sum((a - mean_val) ** 2 for a in amounts) / len(amounts)
    std_val = variance ** 0.5

    anomalies = []
    for r in daily_sales:
        amt = float(r.amt or 0)
        z_score = (amt - mean_val) / std_val if std_val > 0 else 0
        if abs(z_score) > threshold:
            anomalies.append({
                "date": str(r.d),
                "amount": amt,
                "z_score": round(z_score, 2),
                "type": "Surge" if z_score > 0 else "Drop"
            })

    # 异常订单检测（短时间内大量订单）
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_orders = db.session.query(
        func.count(Order.id).label("cnt"),
        Order.user_id
    ).filter(
        Order.created_at >= one_hour_ago,
        Order.status != "cancelled"
    ).group_by(Order.user_id).having(func.count(Order.id) >= 5).all()

    order_anomalies = [{"user_id": r.user_id, "order_count": r.cnt, "type": "Bulk order"} for r in recent_orders]

    return jsonify({
        "anomalies": anomalies,
        "order_anomalies": order_anomalies,
        "mean": round(mean_val, 2),
        "std": round(std_val, 2)
    })


@analytics.route("/data/browse_stats")
@login_required
@admin_or_sales_required
def browse_stats_data():
    """浏览统计"""
    days = int(request.args.get("days", 30))
    start = datetime.utcnow() - timedelta(days=days)

    # 热门浏览商品
    top_viewed = db.session.query(
        Product.name,
        func.count(BrowseLog.id).label("cnt")
    ).join(BrowseLog).filter(
        BrowseLog.created_at >= start
    ).group_by(Product.id).order_by(func.count(BrowseLog.id).desc()).limit(10).all()

    # 每日浏览数
    daily_views = db.session.query(
        func.date(BrowseLog.created_at).label("d"),
        func.count(BrowseLog.id).label("cnt")
    ).filter(
        BrowseLog.created_at >= start
    ).group_by(func.date(BrowseLog.created_at)).order_by("d").all()

    return jsonify({
        "top_viewed_names": [r.name for r in top_viewed],
        "top_viewed_counts": [int(r.cnt) for r in top_viewed],
        "daily_dates": [str(r.d) for r in daily_views],
        "daily_counts": [int(r.cnt) for r in daily_views]
    })


@analytics.route("/data/dashboard_summary")
@login_required
@admin_or_sales_required
def dashboard_summary_data():
    """概览仪表板汇总数据"""
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.filter_by(is_admin=False, is_sales=False).count()
    total_sales = db.session.query(func.sum(Order.total_amount)).filter(Order.status != "cancelled").scalar() or 0.0

    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_orders = Order.query.filter(Order.created_at >= today_start, Order.status != "cancelled").count()
    today_sales = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= today_start, Order.status != "cancelled"
    ).scalar() or 0.0

    # 低库存商品
    low_stock = Product.query.filter(Product.stock <= 5, Product.stock > 0).count()
    out_of_stock = Product.query.filter(Product.stock <= 0).count()

    return jsonify({
        "total_products": total_products,
        "total_orders": total_orders,
        "total_users": total_users,
        "total_sales": round(float(total_sales), 2),
        "today_orders": today_orders,
        "today_sales": round(float(today_sales), 2),
        "low_stock": low_stock,
        "out_of_stock": out_of_stock
    })


# ==================== 页面路由 ====================

@analytics.route("/dashboard")
@login_required
@admin_or_sales_required
def dashboard_page():
    """数据分析仪表板页面"""
    return render_template("analytics/dashboard.html")


@analytics.route("/recommendations")
@login_required
def recommendations_page():
    """推荐页面"""
    return render_template("analytics/recommendations.html")
