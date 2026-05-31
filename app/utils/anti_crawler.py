"""反爬虫检测与应对模块"""
import time
from collections import defaultdict
from flask import request, jsonify, abort

# IP请求记录: {ip: [(timestamp, path), ...]}
_ip_records = defaultdict(list)
# IP黑名单（临时封禁）
_ip_blocked = {}
REQUEST_WINDOW = 10          # 检测窗口（秒）
MAX_REQUESTS_PER_WINDOW = 50  # 窗口内最大请求数
BLOCK_DURATION = 300         # 封禁时长（秒）


def get_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


def check_request():
    """
    检查当前请求是否来自爬虫
    返回 (is_blocked: bool, reason: str|None)
    """
    ip = get_ip()
    now = time.time()

    # 检查封禁
    if ip in _ip_blocked:
        if now - _ip_blocked[ip] < BLOCK_DURATION:
            return True, "IP temporarily blocked"
        del _ip_blocked[ip]

    # 清理过期记录
    _ip_records[ip] = [r for r in _ip_records[ip] if now - r[0] < REQUEST_WINDOW]

    # 记录当前请求
    _ip_records[ip].append((now, request.path))

    # 检查频率
    if len(_ip_records[ip]) > MAX_REQUESTS_PER_WINDOW:
        _ip_blocked[ip] = now
        return True, "Rate limit exceeded"

    # User-Agent 检查
    ua = request.headers.get("User-Agent", "")
    if not ua or len(ua) < 5:
        return True, "Missing or invalid User-Agent"

    blocked_uas = ["scrapy", "curl", "wget", "python-requests", "go-http-client", "libwww", "java/"]
    ua_lower = ua.lower()
    for blocked in blocked_uas:
        if blocked in ua_lower:
            _ip_blocked[ip] = now
            return True, f"Blocked User-Agent: {blocked}"

    return False, None


def anti_crawler_middleware():
    """Flask before_request 中间件"""
    blocked, reason = check_request()
    if blocked:
        abort(429, description=reason)


def get_anti_crawler_stats():
    """获取反爬虫统计"""
    return {
        "blocked_ips": len(_ip_blocked),
        "tracked_ips": len(_ip_records),
        "blocked_list": [
            {"ip": ip, "until": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))}
            for ip, t in _ip_blocked.items()
        ]
    }


def reset_ip(ip):
    """解除单个IP封禁"""
    if ip in _ip_blocked:
        del _ip_blocked[ip]
    if ip in _ip_records:
        del _ip_records[ip]
    return True
