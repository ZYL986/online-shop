from app import create_app, db
from app.models.user import User

app = create_app()


@app.cli.command("create-admin")
def create_admin():
    """Create admin account (flask create-admin)"""
    username = input("Admin username: ")
    email = input("Admin email: ")
    password = input("Admin password: ")

    if User.query.filter_by(is_admin=True).first():
        print("Admin account already exists")
        return

    admin = User(username=username, email=email, is_admin=True)
    admin.set_password(password)

    try:
        db.session.add(admin)
        db.session.commit()
        print(f"Admin {username} created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to create admin: {str(e)}")


@app.cli.command("create-sales")
def create_sales():
    """Create sales account (flask create-sales)"""
    username = input("Sales username: ")
    email = input("Sales email: ")
    password = input("Sales password: ")

    sales = User(username=username, email=email, is_sales=True)
    sales.set_password(password)

    try:
        db.session.add(sales)
        db.session.commit()
        print(f"Sales {username} created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to create sales: {str(e)}")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
