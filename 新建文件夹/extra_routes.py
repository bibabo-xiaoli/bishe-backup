"""Additional API routes for the admin backend.

These routes are separated from :mod:`app` to避免在主文件里做大范围修改，
主要为以下管理页面提供数据：

- admin-address.html  ->  /api/addresses
- admin-collectors.html -> /api/collectors
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from db import get_db


bp = Blueprint("extra_routes", __name__)


COLLECTOR_STATUS_LABELS = {
    0: "离线",
    1: "在线",
    2: "已禁用",
}


@bp.route("/api/addresses", methods=["GET"])
def list_addresses():
    """用户地址列表和统计，供 admin-address.html 使用。

    支持的查询参数（全部可选）：

    - ``page``: 页码，默认为 1
    - ``per_page``: 每页数量，默认 10，最大 100
    - ``search``: 关键字，匹配用户名、手机号、联系人、详细地址
    - ``tag``: 地址标签，如“家”“公司”等
    - ``province``: 省份
    - ``is_default``: 是否默认地址，``1`` 或 ``0``
    """

    db = get_db()
    cursor = db.cursor()

    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("per_page", 10)), 100)
    search = request.args.get("search", "").strip()
    tag = request.args.get("tag")
    province = request.args.get("province")
    is_default = request.args.get("is_default")

    where: list[str] = []
    params: list[object] = []

    if search:
        where.append(
            "(u.nickname LIKE %s OR u.phone LIKE %s "
            "OR a.name LIKE %s OR a.phone LIKE %s OR a.address_detail LIKE %s)",
        )
        like = f"%{search}%"
        params.extend([like, like, like, like, like])

    if tag:
        where.append("a.tag = %s")
        params.append(tag)

    if province:
        where.append("a.province = %s")
        params.append(province)

    if is_default in {"0", "1"}:
        where.append("a.is_default = %s")
        params.append(int(is_default))

    where_sql = " WHERE " + " AND ".join(where) if where else ""
    base_from = " FROM user_address a JOIN user u ON a.user_id = u.id "

    # 统计总数和标签分布
    cursor.execute(
        "SELECT "
        "  COUNT(*) AS total, "
        "  SUM(CASE WHEN a.tag = '家' THEN 1 ELSE 0 END) AS home_count, "
        "  SUM(CASE WHEN a.tag = '公司' THEN 1 ELSE 0 END) AS company_count, "
        "  SUM(CASE WHEN a.is_default = 1 THEN 1 ELSE 0 END) AS default_count "
        + base_from
        + where_sql,
        params,
    )
    stat_row = cursor.fetchone() or {}
    total = stat_row.get("total", 0) or 0

    cursor.execute(
        "SELECT "
        "  a.id, a.user_id, a.name, a.phone, a.province, a.city, a.district, "
        "  a.address_detail, a.tag, a.is_default, a.created_at, "
        "  u.nickname, u.avatar_url "
        + base_from
        + where_sql
        + " ORDER BY a.created_at DESC LIMIT %s OFFSET %s",
        params + [per_page, (page - 1) * per_page],
    )
    rows = cursor.fetchall()

    items: list[dict] = []
    for row in rows:
        full_address = "".join(
            [
                row.get("province") or "",
                row.get("city") or "",
                row.get("district") or "",
                row.get("address_detail") or "",
            ],
        )
        items.append(
            {
                "id": row["id"],
                "address_code": f"A{row['id']:05d}",
                "user_id": row["user_id"],
                "user_nickname": row["nickname"],
                "user_avatar_url": row["avatar_url"],
                "contact_name": row["name"],
                "phone": row["phone"],
                "full_address": full_address,
                "tag": row["tag"],
                "is_default": bool(row["is_default"]),
                "created_at": (
                    row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if row["created_at"]
                    else None
                ),
            },
        )

    stats = {
        "total_addresses": total,
        "home": stat_row.get("home_count", 0) or 0,
        "company": stat_row.get("company_count", 0) or 0,
        "default": stat_row.get("default_count", 0) or 0,
    }

    return jsonify(
        {
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": items,
            "stats": stats,
        },
    )


@bp.route("/api/collectors", methods=["GET"])
def list_collectors():
    """回收员列表与统计，供 admin-collectors.html 使用。

    查询参数：

    - ``page`` / ``per_page``: 分页；
    - ``search``: 按姓名或手机号模糊搜索；
    - ``status``: 按状态筛选（0=离线，1=在线，2=已禁用）。
    """

    db = get_db()
    cursor = db.cursor()

    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("per_page", 10)), 100)
    search = request.args.get("search", "").strip()
    status_param = request.args.get("status")

    # 列表筛选条件
    where: list[str] = []
    params: list[object] = []

    if search:
        where.append("(c.name LIKE %s OR c.phone LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like])

    if status_param in {"0", "1", "2"}:
        where.append("c.status = %s")
        params.append(int(status_param))

    where_sql = " WHERE " + " AND ".join(where) if where else ""
    base_from = " FROM collector c "

    # 全局统计信息（不受筛选影响，用于顶部卡片）
    cursor.execute(
        "SELECT "
        "  COUNT(*) AS total, "
        "  SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS online_count, "
        "  SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS offline_count, "
        "  SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS disabled_count, "
        "  IFNULL(AVG(rating), 0) AS avg_rating "
        "FROM collector",
    )
    global_row = cursor.fetchone() or {}

    cursor.execute(
        """
        SELECT
            COUNT(DISTINCT o.id) AS today_completed_orders,
            IFNULL(SUM(oi.actual_weight), 0) AS today_recycled_kg
        FROM recycle_order o
        LEFT JOIN order_item oi ON oi.order_id = o.id
        WHERE o.status = 3 AND DATE(o.completed_at) = CURRENT_DATE()
        """,
    )
    today_row = cursor.fetchone() or {}

    stats = {
        "total_collectors": global_row.get("total", 0) or 0,
        "online": global_row.get("online_count", 0) or 0,
        "offline": global_row.get("offline_count", 0) or 0,
        "disabled": global_row.get("disabled_count", 0) or 0,
        "today_completed_orders": today_row.get("today_completed_orders", 0) or 0,
        "today_recycled_kg": float(today_row.get("today_recycled_kg", 0) or 0),
        "avg_rating": float(global_row.get("avg_rating", 0) or 0.0),
    }

    # 列表总数（受当前筛选影响）
    cursor.execute("SELECT COUNT(*) AS total" + base_from + where_sql, params)
    total = cursor.fetchone()["total"]

    # 当前页的回收员基础信息
    cursor.execute(
        "SELECT "
        "  c.id, c.name, c.phone, c.avatar_url, c.rating, c.status, c.created_at "
        + base_from
        + where_sql
        + " ORDER BY c.created_at DESC LIMIT %s OFFSET %s",
        params + [per_page, (page - 1) * per_page],
    )
    rows = cursor.fetchall()

    collector_ids = [row["id"] for row in rows]
    orders_by_collector: dict[int, dict[str, int]] = {}
    if collector_ids:
        placeholders = ",".join(["%s"] * len(collector_ids))
        cursor.execute(
            "SELECT "
            "  collector_id, "
            "  COUNT(*) AS total_orders, "
            "  SUM(CASE WHEN status = 3 AND DATE(completed_at) = CURRENT_DATE() "
            "           THEN 1 ELSE 0 END) AS today_orders "
            "FROM recycle_order "
            f"WHERE collector_id IN ({placeholders}) "
            "GROUP BY collector_id",
            collector_ids,
        )
        for r in cursor.fetchall():
            orders_by_collector[r["collector_id"]] = {
                "total_orders": r["total_orders"],
                "today_orders": r["today_orders"],
            }

    items: list[dict] = []
    for row in rows:
        cid = row["id"]
        order_stats = orders_by_collector.get(cid, {})
        items.append(
            {
                "id": cid,
                "collector_code": f"C{cid:05d}",
                "name": row["name"],
                "phone": row["phone"],
                "avatar_url": row["avatar_url"],
                "status": row["status"],
                "status_label": COLLECTOR_STATUS_LABELS.get(row["status"], "未知"),
                # 目前 schema 中未细分服务区域，这里暂时返回空字符串，前端可选择隐藏
                "service_area": "",
                "rating": float(row["rating"] or 0.0),
                "today_orders": order_stats.get("today_orders", 0) or 0,
                "total_orders": order_stats.get("total_orders", 0) or 0,
                "created_at": (
                    row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if row["created_at"]
                    else None
                ),
            },
        )

    return jsonify(
        {
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": items,
            "stats": stats,
        },
    )
