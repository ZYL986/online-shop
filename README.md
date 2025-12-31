# 简单在线购物网站（实验项目）

## 基本信息
- 学号：202330452351
- 姓名：张钰麟
- 项目完成时间：2025-12-29
- 项目部署地址：http://139.9.215.106/（华为云Flexus应用服务器L实例）
- 测试账户（已创建）：
  - 顾客账户：username=admin/3569664879, password=1175345276
  - 管理员账户：zyl/1175345276@qq.com, password=789789asd

## 项目介绍
本项目是基于Python Flask框架开发的简单在线购物网站，满足实验要求的顾客端和销售管理端全部功能，数据库采用MySQL，支持在线部署到阿里云ECS。

## 技术栈
- 后端：Python 3.8+、Flask 2.3.3、SQLAlchemy 3.1.1
- 前端：HTML5、CSS3、Bootstrap 5
- 数据库：MySQL 8.0
- 部署：Gunicorn、Nginx

## 本地部署

### 步骤 1：环境准备
1. **安装 Python 3.8+**
   - 下载地址：https://www.python.org/downloads/
   - 安装时勾选「Add Python to PATH」（Windows）
   - Linux/Mac 一般自带 Python 3，需确保版本≥3.8

2. **安装 MySQL 8.0**
   - 下载地址：https://dev.mysql.com/downloads/mysql/
   - 安装步骤：
     - Windows：下一步安装，设置 root 密码（建议 123456，方便测试），记住端口 3306
     - 将 MySQL 的可执行文件路径加入系统环境变量：`D:\MySQL\bin`（需根据实际安装路径调整）
   - 验证 MySQL：登录 `mysql -u root -p`，输入密码能成功进入即安装完成

### 步骤 2：项目初始化
1. **创建项目目录**
   - 按照提供源代码创建文件夹和文件

2. **创建虚拟环境（隔离项目依赖）**
   - 以管理员身份打开 PowerShell
   - 右键点击"开始菜单"，选择"Windows PowerShell (管理员)"（或"终端 (管理员)"）
   - 修改 PowerShell 执行策略，在管理员 PowerShell 中执行命令：
     ```powershell
     Set-ExecutionPolicy RemoteSigned
     ```
   - 出现确认提示时，输入 `Y` 并回车
   - 打开命令行，进入项目根目录 `online-shop`
   - 执行创建命令：`python -m venv venv`
   - 激活虚拟环境：
     - Windows：`venv\Scripts\activate`（命令行前缀出现 `(venv)` 即激活成功）

3. **安装项目依赖**
   - 执行命令：`pip install -r requirements.txt`
   - 等待依赖包安装完成，无报错即成功

### 步骤 3：MySQL 数据库配置
1. **创建数据库**
   - 启动 MySQL 服务：
     - 方式1（图形界面）：按下 `Win+R` → 输入 `services.msc` → 找到"MySQL80"（或对应版本的服务名）→ 右键选择"启动"
   - 登录 MySQL：`mysql -u root -p`，输入 root 密码
   - 执行创建数据库命令：
     ```sql
     CREATE DATABASE online_shopping CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```
   - 退出 MySQL：`exit`

2. **修改项目数据库配置**
   - 打开 `app/config.py` 文件
   - 修改 `SQLALCHEMY_DATABASE_URI` 中的用户名和密码，确保与你的 MySQL 配置一致：
     ```python
     SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:789789asd@localhost:3306/online_shopping'
     ```

3. **配置邮件发送（可选，测试邮件功能）**
   - 以 QQ 邮箱为例，开启 SMTP 服务：
     - 登录 QQ 邮箱 → 设置 → 账户 → 开启「POP3/SMTP 服务」
     - 获取授权码（不是登录密码）
   - 修改 `app/config.py` 中的邮件配置：
     ```python
     MAIL_USERNAME = '你的QQ邮箱@qq.com'
     MAIL_PASSWORD = '你的QQ邮箱SMTP授权码'
     ```

### 步骤 4：初始化数据库与创建管理员账户
1. **创建数据库表**
   - 项目根目录下，执行命令进入 Flask shell：
     ```bash
     flask shell
     ```
   - 执行命令创建所有数据表：
     ```python
     db.create_all()
     ```
   - 无报错即创建成功，退出 Flask shell：`exit()`

2. **创建管理员账户**
   - 设置 Flask 应用入口环境变量，在当前 PowerShell 窗口中执行：
     ```powershell
     $env:FLASK_APP = "run.py"
     ```
   - 执行命令：`flask create-admin`
   - 按照提示输入管理员用户名、邮箱、密码，完成后即创建成功（该账户 `is_admin=True`，可登录管理后台）

3. **（可选）添加测试商品**
   - 再次进入 Flask shell：`flask shell`
   - 执行以下代码添加测试商品：
     ```python
     from app.models.product import Product
     p1 = Product(name="测试商品1", description="这是第一个测试商品", price=99.99, stock=100)
     p2 = Product(name="测试商品2", description="这是第二个测试商品", price=199.99, stock=50)
     db.session.add(p1)
     db.session.add(p2)
     db.session.commit()
     ```
   - 退出 Flask shell：`exit()`

### 步骤 5：本地运行与功能测试
1. **运行项目**
   - 项目根目录下执行命令：`python run.py`
   - 看到提示 `Running on http://0.0.0.0:5000` 即运行成功

2. **访问项目并测试功能**
   - 打开浏览器，访问 `http://localhost:5000`
   
   **顾客端功能测试：**
   - 点击「注册」，填写信息创建普通顾客账户
   - 登录该账户，浏览商品列表
   - 点击「加入购物车」，将商品添加到购物车
   - 进入「我的购物车」，更新商品数量、删除商品
   - 点击「去结算」，填写收货信息，提交订单
   - 查看「我的订单」，确认订单信息和状态
   - 检查注册邮箱，是否收到发货确认邮件
   
   **管理员端功能测试：**
   - 用之前创建的管理员账户登录
   - 点击「管理后台」，进入仪表盘查看统计数据
   - 进入「商品管理」，添加、编辑、删除商品
   - 进入「订单管理」，更新订单状态（如待付款→已发货）
   - 进入「销售统计」，查看不同时间范围的销售报表

3. **停止项目运行**
   - 命令行中按下 `Ctrl+C`，即可停止项目运行
   - 退出虚拟环境：`deactivate`

## 在线部署
打开浏览器直接访问：[http://139.9.215.106/]