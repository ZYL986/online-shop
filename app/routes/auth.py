from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.utils.tracking import track_login

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for("customer.index"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        region = request.form.get("region", "")

        errors = []
        if not username or len(username) < 4:
            errors.append("用户名长度不能少于4位")
        if not email or "@" not in email:
            errors.append("请输入有效的邮箱地址")
        if not password or len(password) < 6:
            errors.append("密码长度不能少于6位")
        if password != password2:
            errors.append("两次输入的密码不一致")

        if User.query.filter_by(username=username).first():
            errors.append("该用户名已被注册")
        if User.query.filter_by(email=email).first():
            errors.append("该邮箱已被注册")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/register.html")

        new_user = User(username=username, email=email, region=region if region else None)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("注册成功，请登录", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash(f"注册失败：{str(e)}", "danger")
            return render_template("auth/register.html")

    return render_template("auth/register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        elif current_user.is_sales:
            return redirect(url_for("admin.product_list"))
        else:
            return redirect(url_for("customer.index"))

    if request.method == "POST":
        login_param = request.form.get("login_param")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"

        user = User.query.filter(
            (User.username == login_param) | (User.email == login_param)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            track_login(user, success=True)
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            elif user.is_sales:
                return redirect(url_for("admin.product_list"))
            else:
                return redirect(url_for("customer.index"))
        else:
            if user:
                track_login(user, success=False)
            flash("用户名/邮箱或密码错误", "danger")
            return render_template("auth/login.html")

    return render_template("auth/login.html")


@auth.route("/logout")
@login_required
def logout():
    """用户注销"""
    logout_user()
    flash("已成功注销登录", "success")
    return redirect(url_for("auth.login"))
