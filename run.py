from app import create_app, db
from app.models.user import User

app = create_app()


# 命令行上下文：创建管理员账户（可选，方便快速初始化）
@app.cli.command("create-admin")
def create_admin():
    """创建管理员账户（命令行执行：flask create-admin）"""
    username = input("请输入管理员用户名：")
    email = input("请输入管理员邮箱：")
    password = input("请输入管理员密码：")

    # 检查是否已存在管理员
    if User.query.filter_by(is_admin=True).first():
        print("已存在管理员账户，无需重复创建")
        return

    # 创建管理员
    admin = User(
        username=username,
        email=email,
        is_admin=True
    )
    admin.set_password(password)

    try:
        db.session.add(admin)
        db.session.commit()
        print(f"管理员 {username} 创建成功")
    except Exception as e:
        db.session.rollback()
        print(f"管理员创建失败：{str(e)}")


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)