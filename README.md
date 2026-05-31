# 在线购物商城

基于 Python Flask 的电子商务网站，支持用户注册登录、商品浏览搜索、购物车、下单付款、邮件确认，以及销售人员商品管理、管理员数据监控等完整功能。集成协同过滤推荐系统、用户画像分析、反爬虫保护和大数据可视化看板。

## 在线地址

> **http://8.141.97.133/**（阿里云 ECS）

## 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 销售人员 | sales01 | sales123 |
| 顾客 | user01 | user123 |
| 顾客 | user02 | user123 |

## 功能概览

### 顾客端
- 商品浏览（首页列表、分类筛选、关键词搜索）
- 商品详情（浏览记录追踪、关联推荐）
- 购物车（添加、修改数量、删除）
- 下单结算（填写收货信息、付款确认）
- 订单历史与状态查看
- 邮件发货确认
- 个性化推荐（"猜你喜欢"——协同过滤 + 浏览行为推荐）
- 用户画像（地域、购买力、偏好分类）

### 销售人员端
- 商品管理（添加、编辑、删除、CSV 导入）
- 商品分类管理（添加、删除类别）
- 订单管理与状态更新
- 销售报表（按类别、状态、库存统计）
- 浏览/购买日志查看
- 数据可视化（ECharts 图表）
- 库存监控

### 管理员端
- 销售人员账号管理（添加、删除、密码重置）
- 操作日志、登录日志查看
- 销售业绩查询与监控
- 反爬虫统计与 IP 管理
- 数据可视化大屏（销售趋势、排行榜、分类分布、异常检测）
- 数据导出（CSV）

### 数据分析与推荐
- 用户画像（购买力评估、偏好分类、活跃度）
- 销售趋势预测（日/周/月）
- 销售异常实时判别
- 商品销售排行榜
- 协同过滤推荐系统
- "浏览过此商品的人也买了" 关联推荐
- 基于浏览行为的个性化推荐

### 安全与运维
- 反爬虫侦测与应对（频率限制、UA 检测、IP 黑名单）
- 浏览行为、登录日志、操作日志全程追踪
- 移动端适配（Bootstrap 5 响应式）

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端框架 | Python 3.10, Flask 2.3 |
| ORM | SQLAlchemy 2.0, Flask-SQLAlchemy |
| 认证 | Flask-Login |
| 数据库 | MySQL 8.0 |
| 前端 | Bootstrap 5, ECharts 5 |
| 邮件 | Flask-Mail (QQ SMTP) |
| WSGI | Gunicorn |
| 反向代理 | Nginx |
| 可视化 | ECharts, D3.js |

## 本地部署

### 1. 克隆项目

```bash
git clone git@github.com:ZYL986/online-shop.git
cd online-shop
```

### 2. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 MySQL

创建数据库：

```sql
CREATE DATABASE online_shopping CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

修改 `app/config.py` 中的数据库连接串：

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://用户名:密码@localhost:3306/online_shopping?charset=utf8mb4'
```

### 5. 初始化数据库与账号

```bash
set FLASK_APP=run.py          # Windows
export FLASK_APP=run.py       # Linux/Mac

flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

创建管理员和销售人员：

```bash
flask create-admin     # 交互式创建管理员
flask create-sales     # 交互式创建销售人员
```

### 6. 运行

```bash
python run.py
# 访问 http://localhost:5000
```

## 生产部署

使用 Gunicorn + Nginx：

```bash
gunicorn -w 2 -b 127.0.0.1:8000 run:app
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name _;
    client_max_body_size 20M;

    location /static/ {
        alias /opt/online-shop/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 项目结构

```
online-shop/
├── run.py                  # 应用入口
├── requirements.txt        # Python 依赖
├── app/
│   ├── __init__.py         # 应用工厂
│   ├── config.py           # 配置
│   ├── models/             # 数据模型
│   │   ├── user.py         # 用户模型
│   │   ├── product.py      # 商品/分类模型
│   │   ├── cart.py         # 购物车模型
│   │   ├── order.py        # 订单模型
│   │   └── tracking.py     # 日志/画像模型
│   ├── routes/             # 路由蓝图
│   │   ├── auth.py         # 认证（登录/注册）
│   │   ├── customer.py     # 顾客端
│   │   ├── admin.py        # 管理员端
│   │   └── analytics.py    # 数据分析 API
│   ├── utils/              # 工具模块
│   │   ├── anti_crawler.py # 反爬虫
│   │   ├── recommendation.py # 推荐系统
│   │   └── tracking.py     # 行为追踪
│   ├── templates/          # Jinja2 模板
│   └── static/             # 静态资源
└── test_screenshots/       # 测试截图
```
