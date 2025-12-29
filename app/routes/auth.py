from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

# 创建蓝图
auth = Blueprint('auth', __name__)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        # 已登录用户直接跳转到首页
        return redirect(url_for('customer.index'))

    if request.method == 'POST':
        # 获取表单数据
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        # 表单验证
        errors = []
        if not username or len(username) < 4:
            errors.append('用户名长度不能少于4位')
        if not email or '@' not in email:
            errors.append('请输入有效的邮箱地址')
        if not password or len(password) < 6:
            errors.append('密码长度不能少于6位')
        if password != password2:
            errors.append('两次输入的密码不一致')

        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            errors.append('该用户名已被注册')
        if User.query.filter_by(email=email).first():
            errors.append('该邮箱已被注册')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')

        # 创建新用户（普通顾客，is_admin=False）
        new_user = User(
            username=username,
            email=email
        )
        new_user.set_password(password)  # 加密存储密码

        # 保存到数据库
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}', 'danger')
            return render_template('auth/register.html')

    # GET请求：返回注册页面
    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录（顾客+管理员通用，根据is_admin跳转不同页面）"""
    if current_user.is_authenticated:
        # 已登录用户：管理员跳转到管理后台，顾客跳转到首页
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('customer.index'))

    if request.method == 'POST':
        # 获取表单数据
        login_param = request.form.get('login_param')  # 用户名/邮箱均可登录
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'  # 是否记住登录

        # 查找用户（按用户名或邮箱）
        user = User.query.filter(
            (User.username == login_param) | (User.email == login_param)
        ).first()

        # 验证用户和密码
        if user and user.check_password(password):
            # 登录用户
            login_user(user, remember=remember)
            # 获取跳转地址（如果是从需要登录的页面跳转过来的）
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            # 按用户类型跳转
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('customer.index'))
        else:
            flash('用户名/邮箱或密码错误', 'danger')
            return render_template('auth/login.html')

    # GET请求：返回登录页面
    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    """用户注销"""
    logout_user()
    flash('已成功注销登录', 'success')
    return redirect(url_for('auth.login'))