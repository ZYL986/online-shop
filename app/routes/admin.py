import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem

# 创建蓝图
admin = Blueprint('admin', __name__)


def admin_required(func):
    """自定义装饰器：验证是否为管理员"""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash('无权访问管理员页面', 'danger')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)

    return wrapper


@admin.route('/')
@login_required
@admin_required
def dashboard():
    """管理员仪表盘"""
    # 统计基础数据
    product_count = Product.query.count()
    order_count = Order.query.count()
    total_sales = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0.0
    return render_template('admin/dashboard.html',
                           product_count=product_count,
                           order_count=order_count,
                           total_sales=total_sales)


# 商品管理相关路由
@admin.route('/products')
@login_required
@admin_required
def product_list():
    """商品列表（增删改查）"""
    products = Product.query.order_by(Product.updated_at.desc()).all()
    return render_template('admin/products/list.html', products=products)


@admin.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def product_add():
    """添加商品"""
    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0.0))
        stock = int(request.form.get('stock', 0))
        image_file = request.files.get('image')

        # 验证表单数据
        errors = []
        if not name:
            errors.append('商品名称不能为空')
        if price < 0:
            errors.append('商品价格不能为负数')
        if stock < 0:
            errors.append('商品库存不能为负数')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/products/add.html')

        # 处理商品图片（保存到static/images目录）
        image_filename = None
        if image_file and image_file.filename != '':
            # 生成唯一文件名（避免重名）
            ext = os.path.splitext(image_file.filename)[1]
            image_filename = f'product_{datetime.now().strftime("%Y%m%d%H%M%S")}{ext}'
            # 保存文件
            image_path = os.path.join(current_app.root_path, 'app', 'static', 'images', image_filename)
            try:
                image_file.save(image_path)
            except Exception as e:
                flash(f'图片保存失败：{str(e)}', 'danger')
                image_filename = None

        # 创建新商品
        new_product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            image_filename=image_filename
        )

        # 保存到数据库
        try:
            db.session.add(new_product)
            db.session.commit()
            flash('商品添加成功', 'success')
            return redirect(url_for('admin.product_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'商品添加失败：{str(e)}', 'danger')
            return render_template('admin/products/add.html')

    # GET请求：返回添加商品页面
    return render_template('admin/products/add.html')


@admin.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def product_edit(product_id):
    """编辑商品"""
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0.0))
        stock = int(request.form.get('stock', 0))
        image_file = request.files.get('image')

        # 验证表单数据
        errors = []
        if not name:
            errors.append('商品名称不能为空')
        if price < 0:
            errors.append('商品价格不能为负数')
        if stock < 0:
            errors.append('商品库存不能为负数')

        if errors:
            for error in errors:
                flash(error, 'danger')
                return render_template('admin/products/edit.html', product=product)

        # 更新商品基本信息
        product.name = name
        product.description = description
        product.price = price
        product.stock = stock

        # 处理商品图片（可选更新）
        if image_file and image_file.filename != '':
            # 删除旧图片（如果存在）
            if product.image_filename:
                old_image_path = os.path.join(current_app.root_path, 'app', 'static', 'images', product.image_filename)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            # 保存新图片
            ext = os.path.splitext(image_file.filename)[1]
            product.image_filename = f'product_{datetime.now().strftime("%Y%m%d%H%M%S")}{ext}'
            new_image_path = os.path.join(current_app.root_path, 'app', 'static', 'images', product.image_filename)
            try:
                image_file.save(new_image_path)
            except Exception as e:
                flash(f'图片保存失败：{str(e)}', 'danger')

        # 保存到数据库
        try:
            db.session.commit()
            flash('商品编辑成功', 'success')
            return redirect(url_for('admin.product_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'商品编辑失败：{str(e)}', 'danger')
            return render_template('admin/products/edit.html', product=product)

    # GET请求：返回编辑商品页面
    return render_template('admin/products/edit.html', product=product)


@admin.route('/products/delete/<int:product_id>')
@login_required
@admin_required
def product_delete(product_id):
    """删除商品"""
    product = Product.query.get_or_404(product_id)

    # 删除商品图片（如果存在）
    if product.image_filename:
        image_path = os.path.join(current_app.root_path, 'app', 'static', 'images', product.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    # 删除商品
    try:
        db.session.delete(product)
        db.session.commit()
        flash('商品删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'商品删除失败：{str(e)}', 'danger')

    return redirect(url_for('admin.product_list'))


# 订单管理相关路由
@admin.route('/orders')
@login_required
@admin_required
def order_list():
    """订单列表（修改状态、查看详情）"""
    # 获取订单状态筛选条件（可选）
    status = request.args.get('status', '')
    if status:
        orders = Order.query.filter_by(status=status).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.order_by(Order.created_at.desc()).all()

    return render_template('admin/orders/list.html', orders=orders, current_status=status)


@admin.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def order_update(order_id):
    """更新订单状态"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    # 验证订单状态
    valid_statuses = ['pending', 'shipped', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        flash('无效的订单状态', 'danger')
        return redirect(url_for('admin.order_list'))

    # 更新订单状态和对应时间
    order.status = new_status
    if new_status == 'shipped':
        order.ship_time = datetime.utcnow()
    elif new_status == 'completed':
        order.ship_time = order.ship_time or datetime.utcnow()

    # 保存到数据库
    try:
        db.session.commit()
        flash(f'订单 {order.order_no} 状态已更新为 {new_status}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'更新订单状态失败：{str(e)}', 'danger')

    return redirect(url_for('admin.order_list'))


# 销售统计报表相关路由
@admin.route('/reports/sales')
@login_required
@admin_required
def sales_report():
    """销售统计报表"""
    # 时间范围筛选（默认近30天）
    days = int(request.args.get('days', 30))
    start_date = datetime.utcnow() - timedelta(days=days)

    # 1. 总销售额、总订单数、平均订单金额
    orders = Order.query.filter(Order.created_at >= start_date).filter(Order.status != 'cancelled').all()
    total_sales = sum(order.total_amount for order in orders)
    total_orders = len(orders)
    avg_order_amount = total_sales / total_orders if total_orders > 0 else 0.0

    # 2. 销量最高的商品（前10）
    top_products = db.session.query(
        Product,
        db.func.sum(OrderItem.quantity).label('total_quantity'),
        db.func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_sales')
    ).join(OrderItem).join(Order).filter(
        Order.created_at >= start_date,
        Order.status != 'cancelled'
    ).group_by(Product).order_by(db.func.sum(OrderItem.quantity).desc()).limit(10).all()

    return render_template('admin/reports/sales_report.html',
                           days=days,
                           total_sales=total_sales,
                           total_orders=total_orders,
                           avg_order_amount=avg_order_amount,
                           top_products=top_products)