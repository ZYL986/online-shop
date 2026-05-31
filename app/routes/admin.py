import os
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, Response
from flask_login import login_required, current_user
from app import db
from app.models.product import Product, ProductCategory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.models.tracking import BrowseLog, LoginLog, OperationLog, UserProfile
from app.utils.tracking import track_operation
from app.utils.anti_crawler import get_anti_crawler_stats, reset_ip
from sqlalchemy import func

admin = Blueprint("admin", __name__)


def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("无权访问管理员页面", "danger")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)
    return wrapper


def staff_required(func):
    """管理员或销售人员均可访问"""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not (current_user.is_admin or current_user.is_sales):
            flash("无权访问此页面", "danger")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)
    return wrapper


# ==================== Dashboard ====================

@admin.route("/")
@login_required
@staff_required
def dashboard():
    """管理员/销售人员仪表盘"""
    product_count = Product.query.count()
    order_count = Order.query.count()
    total_sales = db.session.query(func.sum(Order.total_amount)).filter(Order.status != "cancelled").scalar() or 0.0
    user_count = User.query.filter_by(is_admin=False, is_sales=False).count()

    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    today_orders = Order.query.filter(Order.created_at >= today_start).count()
    today_sales = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= today_start, Order.status != "cancelled"
    ).scalar() or 0.0

    low_stock_count = Product.query.filter(Product.stock <= 5, Product.stock > 0).count()

    return render_template("admin/dashboard.html",
                           product_count=product_count,
                           order_count=order_count,
                           total_sales=total_sales,
                           user_count=user_count,
                           today_orders=today_orders,
                           today_sales=today_sales,
                           low_stock_count=low_stock_count)


# ==================== 商品类别管理 ====================

@admin.route("/categories")
@login_required
@staff_required
def category_list():
    """商品类别列表"""
    categories = ProductCategory.query.order_by(ProductCategory.created_at.desc()).all()
    return render_template("admin/categories/list.html", categories=categories)


@admin.route("/categories/add", methods=["GET", "POST"])
@login_required
@staff_required
def category_add():
    """添加商品类别"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("类别名称不能为空", "danger")
            return render_template("admin/categories/add.html")
        if ProductCategory.query.filter_by(name=name).first():
            flash("该类别名称已存在", "danger")
            return render_template("admin/categories/add.html")

        cat = ProductCategory(name=name, description=description)
        try:
            db.session.add(cat)
            db.session.commit()
            track_operation(current_user, "add_category", f"Added category: {name}", "category", cat.id)
            flash("类别添加成功", "success")
            return redirect(url_for("admin.category_list"))
        except Exception as e:
            db.session.rollback()
            flash(f"添加失败：{str(e)}", "danger")

    return render_template("admin/categories/add.html")


@admin.route("/categories/edit/<int:cat_id>", methods=["GET", "POST"])
@login_required
@staff_required
def category_edit(cat_id):
    """编辑商品类别"""
    cat = ProductCategory.query.get_or_404(cat_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("类别名称不能为空", "danger")
            return render_template("admin/categories/edit.html", category=cat)
        existing = ProductCategory.query.filter_by(name=name).first()
        if existing and existing.id != cat.id:
            flash("该类别名称已存在", "danger")
            return render_template("admin/categories/edit.html", category=cat)

        cat.name = name
        cat.description = description
        try:
            db.session.commit()
            track_operation(current_user, "edit_category", f"Edited category: {name}", "category", cat.id)
            flash("类别编辑成功", "success")
            return redirect(url_for("admin.category_list"))
        except Exception as e:
            db.session.rollback()
            flash(f"编辑失败：{str(e)}", "danger")

    return render_template("admin/categories/edit.html", category=cat)


@admin.route("/categories/delete/<int:cat_id>")
@login_required
@staff_required
def category_delete(cat_id):
    """删除商品类别"""
    cat = ProductCategory.query.get_or_404(cat_id)
    Product.query.filter_by(category_id=cat_id).update({Product.category_id: None})
    try:
        db.session.delete(cat)
        db.session.commit()
        track_operation(current_user, "delete_category", f"Deleted category: {cat.name}", "category", cat_id)
        flash("类别删除成功（相关商品已移至未分类）", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"删除失败：{str(e)}", "danger")
    return redirect(url_for("admin.category_list"))


# ==================== 商品管理 ====================

@admin.route("/products")
@login_required
@staff_required
def product_list():
    """商品列表"""
    products = Product.query.order_by(Product.updated_at.desc()).all()
    categories = ProductCategory.query.all()
    return render_template("admin/products/list.html", products=products, categories=categories)


@admin.route("/products/add", methods=["GET", "POST"])
@login_required
@staff_required
def product_add():
    """添加商品"""
    categories = ProductCategory.query.all()
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = float(request.form.get("price", 0.0))
        stock = int(request.form.get("stock", 0))
        category_id = request.form.get("category_id", type=int)
        image_file = request.files.get("image")

        errors = []
        if not name:
            errors.append("商品名称不能为空")
        if price < 0:
            errors.append("商品价格不能为负数")
        if stock < 0:
            errors.append("商品库存不能为负数")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("admin/products/add.html", categories=categories)

        image_filename = None
        if image_file and image_file.filename != "":
            ext = os.path.splitext(image_file.filename)[1]
            image_filename = f"product_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            image_path = os.path.join(current_app.root_path, "static", "images", image_filename)
            try:
                image_file.save(image_path)
            except Exception as e:
                flash(f"图片保存失败：{str(e)}", "danger")
                image_filename = None

        new_product = Product(
            name=name, description=description, price=price,
            stock=stock, category_id=category_id if category_id else None,
            image_filename=image_filename
        )

        try:
            db.session.add(new_product)
            db.session.commit()
            track_operation(current_user, "add_product", f"Added product: {name}", "product", new_product.id)
            flash("商品添加成功", "success")
            return redirect(url_for("admin.product_list"))
        except Exception as e:
            db.session.rollback()
            flash(f"商品添加失败：{str(e)}", "danger")

    return render_template("admin/products/add.html", categories=categories)


@admin.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@staff_required
def product_edit(product_id):
    """编辑商品"""
    product = Product.query.get_or_404(product_id)
    categories = ProductCategory.query.all()

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = float(request.form.get("price", 0.0))
        stock = int(request.form.get("stock", 0))
        category_id = request.form.get("category_id", type=int)
        image_file = request.files.get("image")

        errors = []
        if not name:
            errors.append("商品名称不能为空")
        if price < 0:
            errors.append("商品价格不能为负数")
        if stock < 0:
            errors.append("商品库存不能为负数")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("admin/products/edit.html", product=product, categories=categories)

        product.name = name
        product.description = description
        product.price = price
        product.stock = stock
        product.category_id = category_id if category_id else None

        if image_file and image_file.filename != "":
            if product.image_filename:
                old_path = os.path.join(current_app.root_path, "static", "images", product.image_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            ext = os.path.splitext(image_file.filename)[1]
            product.image_filename = f"product_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            new_path = os.path.join(current_app.root_path, "static", "images", product.image_filename)
            try:
                image_file.save(new_path)
            except Exception as e:
                flash(f"图片保存失败：{str(e)}", "danger")

        try:
            db.session.commit()
            track_operation(current_user, "edit_product", f"Edited product: {name}", "product", product.id)
            flash("商品编辑成功", "success")
            return redirect(url_for("admin.product_list"))
        except Exception as e:
            db.session.rollback()
            flash(f"商品编辑失败：{str(e)}", "danger")

    return render_template("admin/products/edit.html", product=product, categories=categories)


@admin.route("/products/delete/<int:product_id>")
@login_required
@staff_required
def product_delete(product_id):
    """删除商品"""
    product = Product.query.get_or_404(product_id)
    if product.image_filename:
        image_path = os.path.join(current_app.root_path, "static", "images", product.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
    try:
        db.session.delete(product)
        db.session.commit()
        track_operation(current_user, "delete_product", f"Deleted product: {product.name}", "product", product_id)
        flash("商品删除成功", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"商品删除失败：{str(e)}", "danger")
    return redirect(url_for("admin.product_list"))


# ==================== 订单管理 ====================

@admin.route("/orders")
@login_required
@staff_required
def order_list():
    """订单列表"""
    status = request.args.get("status", "")
    if status:
        orders = Order.query.filter_by(status=status).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders/list.html", orders=orders, current_status=status)


@admin.route("/orders/update/<int:order_id>", methods=["POST"])
@login_required
@staff_required
def order_update(order_id):
    """更新订单状态"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    valid_statuses = ["pending", "shipped", "completed", "cancelled"]
    if new_status not in valid_statuses:
        flash("无效的订单状态", "danger")
        return redirect(url_for("admin.order_list"))

    old_status = order.status
    order.status = new_status
    if new_status == "shipped":
        order.ship_time = datetime.utcnow()
    elif new_status == "completed":
        order.ship_time = order.ship_time or datetime.utcnow()

    try:
        db.session.commit()
        track_operation(current_user, "update_order", f"Order {order.order_no}: {old_status} -> {new_status}", "order", order.id)
        flash(f"订单 {order.order_no} 状态已更新为 {new_status}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新订单状态失败：{str(e)}", "danger")

    return redirect(url_for("admin.order_list"))


# ==================== 销售统计报表 ====================

@admin.route("/reports/sales")
@login_required
@staff_required
def sales_report():
    """销售统计报表"""
    days = int(request.args.get("days", 30))
    start_date = datetime.utcnow() - timedelta(days=days)

    orders = Order.query.filter(Order.created_at >= start_date).filter(Order.status != "cancelled").all()
    total_sales = sum(order.total_amount for order in orders)
    total_orders = len(orders)
    avg_order_amount = total_sales / total_orders if total_orders > 0 else 0.0

    top_products = db.session.query(
        Product, func.sum(OrderItem.quantity).label("total_quantity"),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_sales")
    ).join(OrderItem).join(Order).filter(
        Order.created_at >= start_date, Order.status != "cancelled"
    ).group_by(Product).order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()

    return render_template("admin/reports/sales_report.html",
                           days=days, total_sales=total_sales,
                           total_orders=total_orders,
                           avg_order_amount=avg_order_amount,
                           top_products=top_products)


# ==================== 用户管理（Admin专属） ====================

@admin.route("/users")
@login_required
@admin_required
def user_list():
    """用户列表管理"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users/list.html", users=users)


@admin.route("/users/toggle_sales/<int:user_id>")
@login_required
@admin_required
def user_toggle_sales(user_id):
    """切换销售人员身份"""
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("不能修改管理员的销售身份", "danger")
        return redirect(url_for("admin.user_list"))
    user.is_sales = not user.is_sales
    try:
        db.session.commit()
        track_operation(current_user, "toggle_sales",
                        f"User {user.username} sales={'ON' if user.is_sales else 'OFF'}", "user", user.id)
        flash(f"用户 {user.username} 销售身份已{'启用' if user.is_sales else '禁用'}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"操作失败：{str(e)}", "danger")
    return redirect(url_for("admin.user_list"))


@admin.route("/users/reset_password/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def user_reset_password(user_id):
    """管理员重置用户密码"""
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "123456")
    user.set_password(new_password)
    try:
        db.session.commit()
        track_operation(current_user, "reset_password", f"Reset password for {user.username}", "user", user.id)
        flash(f"用户 {user.username} 密码已重置", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"重置失败：{str(e)}", "danger")
    return redirect(url_for("admin.user_list"))


# ==================== 操作日志 ====================

@admin.route("/logs")
@login_required
@admin_required
def operation_logs():
    """操作日志查看"""
    page = request.args.get("page", 1, type=int)
    per_page = 50
    pagination = OperationLog.query.order_by(OperationLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    return render_template("admin/logs/list.html", logs=pagination.items, pagination=pagination)


@admin.route("/logs/browse")
@login_required
@staff_required
def browse_logs():
    """浏览日志查看"""
    page = request.args.get("page", 1, type=int)
    per_page = 50
    pagination = BrowseLog.query.order_by(BrowseLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    return render_template("admin/logs/browse.html", logs=pagination.items, pagination=pagination)


@admin.route("/logs/login")
@login_required
@admin_required
def login_logs():
    """登录日志查看"""
    page = request.args.get("page", 1, type=int)
    per_page = 50
    pagination = LoginLog.query.order_by(LoginLog.login_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    return render_template("admin/logs/login.html", logs=pagination.items, pagination=pagination)


# ==================== 反爬虫管理 ====================

@admin.route("/anti_crawler")
@login_required
@admin_required
def anti_crawler_page():
    """反爬虫管理页面"""
    stats = get_anti_crawler_stats()
    return render_template("admin/anti_crawler.html", stats=stats)


@admin.route("/anti_crawler/unblock/<ip>")
@login_required
@admin_required
def anti_crawler_unblock(ip):
    """解除IP封禁"""
    reset_ip(ip)
    flash(f"IP {ip} 已解除封禁", "success")
    return redirect(url_for("admin.anti_crawler_page"))


# ==================== 数据导出 ====================

@admin.route("/export/orders")
@login_required
@admin_required
def export_orders():
    """导出订单为CSV"""
    days = int(request.args.get("days", 30))
    start = datetime.utcnow() - timedelta(days=days)
    orders = Order.query.filter(Order.created_at >= start).order_by(Order.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order No", "User", "Amount", "Status", "Recipient", "Phone", "Address", "Created At"])
    for o in orders:
        writer.writerow([o.order_no, o.user.username, o.total_amount, o.status,
                         o.recipient_name, o.recipient_phone, o.recipient_address,
                         o.created_at.strftime("%Y-%m-%d %H:%M:%S")])

    output.seek(0)
    return Response(
        output.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=orders_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@admin.route("/export/products")
@login_required
@admin_required
def export_products():
    """导出商品为CSV"""
    products = Product.query.order_by(Product.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Category", "Price", "Stock", "Views", "Description"])
    for p in products:
        writer.writerow([p.id, p.name, (p.category.name if p.category else ""), p.price, p.stock,
                         p.view_count or 0, p.description or ""])

    output.seek(0)
    return Response(
        output.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=products_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@admin.route("/export/users")
@login_required
@admin_required
def export_users():
    """导出用户为CSV"""
    users = User.query.order_by(User.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Username", "Email", "Role", "Region", "Total Spent", "Registered"])
    for u in users:
        writer.writerow([u.id, u.username, u.email, u.role, u.region or "",
                         round(u.total_spent, 2), u.created_at.strftime("%Y-%m-%d %H:%M:%S")])

    output.seek(0)
    return Response(
        output.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=users_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


# ==================== 数据导入 ====================

@admin.route("/import/products", methods=["GET", "POST"])
@login_required
@staff_required
def import_products():
    """批量导入商品 CSV"""
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("请选择CSV文件", "danger")
            return render_template("admin/import_products.html")

        try:
            content = file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            count = 0
            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue
                price = float(row.get("price", 0))
                stock = int(row.get("stock", 0))
                cat_name = row.get("category", "").strip()
                description = row.get("description", "").strip()

                category_id = None
                if cat_name:
                    cat = ProductCategory.query.filter_by(name=cat_name).first()
                    if not cat:
                        cat = ProductCategory(name=cat_name)
                        db.session.add(cat)
                        db.session.flush()
                    category_id = cat.id

                product = Product(name=name, description=description, price=price,
                                  stock=stock, category_id=category_id)
                db.session.add(product)
                count += 1

            db.session.commit()
            track_operation(current_user, "import_products", f"Imported {count} products")
            flash(f"成功导入 {count} 个商品", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"导入失败：{str(e)}", "danger")

    return render_template("admin/import_products.html")
