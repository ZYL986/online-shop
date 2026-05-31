"""跟踪中间件：记录浏览行为、登录日志、操作日志"""
import uuid
from datetime import datetime
from flask import request, session, g
from app import db
from app.models.tracking import BrowseLog, LoginLog, OperationLog
from app.models.product import Product


def get_client_ip():
    """获取客户端真实IP"""
    if request.headers.get("X-Forwarded-For"):
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def get_or_create_session_id():
    if "session_uuid" not in session:
        session["session_uuid"] = uuid.uuid4().hex
    return session["session_uuid"]


def track_browse(user_id, product_id=None, category_id=None, action="view"):
    """记录浏览行为"""
    sid = get_or_create_session_id()
    log = BrowseLog(
        user_id=user_id,
        product_id=product_id,
        category_id=category_id,
        action=action,
        ip_address=get_client_ip(),
        user_agent=request.headers.get("User-Agent", "")[:512],
        session_id=sid,
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def track_login(user, success=True):
    """记录登录行为"""
    log = LoginLog(
        user_id=user.id,
        ip_address=get_client_ip(),
        user_agent=request.headers.get("User-Agent", "")[:512],
        login_time=datetime.utcnow(),
        success=success
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def track_operation(user, action, content="", target_type=None, target_id=None):
    """记录管理员/销售人员操作"""
    log = OperationLog(
        user_id=user.id,
        action=action,
        content=str(content)[:1024],
        target_type=target_type,
        target_id=target_id,
        ip_address=get_client_ip(),
        created_at=datetime.utcnow()
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
