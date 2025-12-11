"""智能回收小程序后台：Flask + MySQL 8.0 RESTful API.

当前实现内容：
- /api/health                健康检查
- /api/users                 用户列表（分页、搜索、等级筛选）
- /api/users/<id>            用户详情
- /api/dashboard/summary     仪表盘汇总数据
"""

from datetime import date
import io
import json
import os

from flask import Flask, jsonify, request
from pymysql.err import IntegrityError

from config import Config
from db import get_db, close_db


ORDER_STATUS_LABELS = {
    1: "待上门",
    2: "进行中",
    3: "已完成",
    4: "已取消",
    5: "售后",
}


AFTER_SALE_STATUS_LABELS = {
    1: "待处理",
    2: "处理中",
    3: "已解决",
    4: "已关闭",
}


COLLECTOR_STATUS_LABELS = {
    0: "离线",
    1: "在线",
    2: "已禁用",
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)

    # 请求结束时自动关闭数据库连接
    @app.teardown_appcontext
    def teardown_db(exception):  # type: ignore[override]
        close_db(exception)

    # 简单的 CORS，便于直接从本地 HTML 访问 API
    @app.after_request
    def add_cors_headers(response):  # type: ignore[override]
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault(
            "Access-Control-Allow-Headers", "Content-Type, Authorization",
        )
        response.headers.setdefault(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        )
        return response

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/users", methods=["GET"])
    def list_users():
        """用户列表，供 admin-users.html 使用。"""
        db = get_db()
        cursor = db.cursor()

        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 10)), 100)
        search = request.args.get("search", "").strip()
        level_id = request.args.get("level_id")

        where = []
        params = []

        if search:
            where.append(
                "(u.nickname LIKE %s OR u.phone LIKE %s OR CAST(u.id AS CHAR) LIKE %s)",
            )
            like = f"%{search}%"
            params.extend([like, like, like])

        if level_id:
            where.append("u.level_id = %s")
            params.append(level_id)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        base_from = " FROM user u LEFT JOIN user_level l ON u.level_id = l.id "

        cursor.execute(f"SELECT COUNT(*) AS total{base_from}{where_sql}", params)
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT u.id, u.nickname, u.avatar_url, u.phone, u.current_points, "
            "u.total_carbon_kg, u.recycle_count, u.created_at, u.status, l.level_name "
            + base_from
            + where_sql
            + " ORDER BY u.created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        rows = cursor.fetchall()

        items = []
        for row in rows:
            carbon = row["total_carbon_kg"]
            items.append(
                {
                    "id": row["id"],
                    "user_code": f"U{row['id']:05d}",
                    "nickname": row["nickname"],
                    "avatar_url": row["avatar_url"],
                    "phone": row["phone"],
                    "level_name": row["level_name"],
                    "current_points": row["current_points"],
                    "total_carbon_kg": float(carbon) if carbon is not None else 0.0,
                    "recycle_count": row["recycle_count"],
                    "status": "正常" if row.get("status", 1) == 1 else "已禁用",
                    "created_at": (
                        row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                        if row["created_at"]
                        else None
                    ),
                },
            )

        return jsonify(
            {"total": total, "page": page, "per_page": per_page, "items": items},
        )

    @app.route("/api/users/<int:user_id>", methods=["GET"])
    def user_detail(user_id: int):
        """用户详情，预留给弹窗使用。"""
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT u.*, l.level_name,
                   addr.province, addr.city, addr.district, addr.address_detail
            FROM user u
            LEFT JOIN user_level l ON u.level_id = l.id
            LEFT JOIN user_address addr
              ON addr.user_id = u.id AND addr.is_default = 1
            WHERE u.id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        carbon = row["total_carbon_kg"]
        data = {
            "id": row["id"],
            "user_code": f"U{row['id']:05d}",
            "nickname": row["nickname"],
            "avatar_url": row["avatar_url"],
            "phone": row["phone"],
            "level_name": row["level_name"],
            "total_points": row["total_points"],
            "current_points": row["current_points"],
            "total_carbon_kg": float(carbon) if carbon is not None else 0.0,
            "recycle_count": row["recycle_count"],
            "created_at": (
                row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                if row["created_at"]
                else None
            ),
            "updated_at": (
                row["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
                if row["updated_at"]
                else None
            ),
            "default_address": None,
            "status": "正常",
        }
        if row.get("address_detail"):
            data["default_address"] = {
                "province": row["province"],
                "city": row["city"],
                "district": row["district"],
                "address_detail": row["address_detail"],
            }
        return jsonify(data)

    @app.route("/api/users/<int:user_id>/toggle-status", methods=["POST"])
    def toggle_user_status(user_id: int):
        """切换用户禁用状态。"""
        db = get_db()
        cursor = db.cursor()

        # 获取当前状态
        cursor.execute("SELECT status FROM user WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        current_status = row.get("status", 1)
        new_status = 0 if current_status == 1 else 1

        cursor.execute(
            "UPDATE user SET status = %s WHERE id = %s",
            (new_status, user_id),
        )
        db.commit()

        return jsonify({
            "success": True,
            "user_id": user_id,
            "status": "正常" if new_status == 1 else "已禁用",
        })

    @app.route("/api/dashboard/summary", methods=["GET"])
    def dashboard_summary():
        """仪表盘汇总数据，供 admin.html 等页面使用。"""
        db = get_db()
        cursor = db.cursor()

        # 用户总数
        cursor.execute("SELECT COUNT(*) AS c FROM user")
        total_users = cursor.fetchone()["c"]

        # 今日新增用户
        cursor.execute(
            "SELECT COUNT(*) AS c FROM user WHERE DATE(created_at) = CURRENT_DATE()",
        )
        today_new_users = cursor.fetchone()["c"]

        # 活跃用户：有过回收记录的用户数量
        cursor.execute("SELECT COUNT(*) AS c FROM user WHERE recycle_count > 0")
        active_users = cursor.fetchone()["c"]

        # 今日订单数量
        cursor.execute(
            "SELECT COUNT(*) AS c FROM recycle_order "
            "WHERE DATE(created_at) = CURRENT_DATE()",
        )
        today_orders = cursor.fetchone()["c"]

        # 今日减碳量（已完成订单）
        cursor.execute(
            "SELECT IFNULL(SUM(carbon_saved_kg), 0) AS s FROM recycle_order "
            "WHERE DATE(completed_at) = CURRENT_DATE()",
        )
        today_carbon = cursor.fetchone()["s"] or 0

        # 历史累计积分发放 & 今日积分发放
        cursor.execute(
            "SELECT IFNULL(SUM(points), 0) AS s FROM points_record WHERE type = 1",
        )
        total_points_earned = cursor.fetchone()["s"] or 0

        cursor.execute(
            "SELECT IFNULL(SUM(points), 0) AS s FROM points_record "
            "WHERE type = 1 AND DATE(created_at) = CURRENT_DATE()",
        )
        today_points_earned = cursor.fetchone()["s"] or 0

        return jsonify(
            {
                "total_users": total_users,
                "today_new_users": today_new_users,
                "active_users": active_users,
                "disabled_users": 0,  # 预留：当前未单独存储用户禁用状态
                "today_orders": today_orders,
                "today_carbon_kg": float(today_carbon),
                "total_points_earned": total_points_earned,
                "today_points_earned": today_points_earned,
            },
        )

    @app.route("/api/user_levels", methods=["GET"])
    def list_user_levels():
        """用户等级列表及每个等级的用户数，供 admin-levels.html 使用。"""

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT
                l.id,
                l.level_name,
                l.min_points,
                l.max_points,
                l.badge_icon,
                l.description,
                COUNT(u.id) AS user_count
            FROM user_level l
            LEFT JOIN user u ON u.level_id = l.id
            GROUP BY
                l.id,
                l.level_name,
                l.min_points,
                l.max_points,
                l.badge_icon,
                l.description
            ORDER BY l.min_points ASC, l.id ASC
            """,
        )
        rows = cursor.fetchall()

        items: list[dict] = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "name": row["level_name"],
                    "min_points": row["min_points"],
                    "max_points": row["max_points"],
                    "badge_icon": row["badge_icon"],
                    "description": row["description"],
                    "user_count": row["user_count"],
                },
            )

        return jsonify({"total": len(items), "items": items})

    @app.route("/api/categories", methods=["GET"])
    def list_categories():
        """回收品类列表，供 admin-categories.html 使用。"""

        db = get_db()
        cursor = db.cursor()

        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 10)), 100)
        search = request.args.get("search", "").strip()

        where: list[str] = []
        params: list[object] = []

        if search:
            where.append("name LIKE %s")
            like = f"%{search}%"
            params.append(like)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        cursor.execute(
            "SELECT COUNT(*) AS total FROM recycle_category" + where_sql,
            params,
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT id, name, icon, points_per_kg, description, sort_order "
            "FROM recycle_category "
            + where_sql
            + " ORDER BY sort_order IS NULL, sort_order, id LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        rows = cursor.fetchall()

        items: list[dict] = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "category_code": f"CAT{row['id']:03d}",
                    "name": row["name"],
                    "icon": row["icon"],
                    "points_per_kg": row["points_per_kg"],
                    "description": row["description"],
                    "sort_order": row["sort_order"],
                },
            )

        return jsonify(
            {"total": total, "page": page, "per_page": per_page, "items": items},
        )

    @app.route("/api/categories", methods=["POST"])
    def create_category():
        """创建新的回收品类。"""

        db = get_db()
        cursor = db.cursor()

        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400

        icon = (data.get("icon") or "").strip() or None
        description = (data.get("description") or "").strip() or None

        points_per_kg_raw = data.get("points_per_kg")
        sort_order_raw = data.get("sort_order")

        points_per_kg = None
        if points_per_kg_raw is not None and points_per_kg_raw != "":
            try:
                points_per_kg = int(points_per_kg_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "points_per_kg must be an integer"}), 400

        sort_order = None
        if sort_order_raw is not None and sort_order_raw != "":
            try:
                sort_order = int(sort_order_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "sort_order must be an integer"}), 400

        cursor.execute(
            "INSERT INTO recycle_category (name, icon, points_per_kg, description, sort_order) "
            "VALUES (%s, %s, %s, %s, %s)",
            (name, icon, points_per_kg, description, sort_order),
        )
        new_id = cursor.lastrowid

        cursor.execute(
            "SELECT id, name, icon, points_per_kg, description, sort_order "
            "FROM recycle_category WHERE id = %s",
            (new_id,),
        )
        row = cursor.fetchone()

        data = {
            "id": row["id"],
            "category_code": f"CAT{row['id']:03d}",
            "name": row["name"],
            "icon": row["icon"],
            "points_per_kg": row["points_per_kg"],
            "description": row["description"],
            "sort_order": row["sort_order"],
        }
        return jsonify(data), 201

    @app.route("/api/categories/<int:category_id>", methods=["PUT"])
    def update_category(category_id: int):
        """更新回收品类配置。"""

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT id FROM recycle_category WHERE id = %s",
            (category_id,),
        )
        if not cursor.fetchone():
            return jsonify({"error": "Category not found"}), 404

        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400

        icon = (data.get("icon") or "").strip() or None
        description = (data.get("description") or "").strip() or None

        points_per_kg_raw = data.get("points_per_kg")
        sort_order_raw = data.get("sort_order")

        points_per_kg = None
        if points_per_kg_raw is not None and points_per_kg_raw != "":
            try:
                points_per_kg = int(points_per_kg_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "points_per_kg must be an integer"}), 400

        sort_order = None
        if sort_order_raw is not None and sort_order_raw != "":
            try:
                sort_order = int(sort_order_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "sort_order must be an integer"}), 400

        cursor.execute(
            "UPDATE recycle_category "
            "SET name = %s, icon = %s, points_per_kg = %s, description = %s, sort_order = %s "
            "WHERE id = %s",
            (name, icon, points_per_kg, description, sort_order, category_id),
        )

        cursor.execute(
            "SELECT id, name, icon, points_per_kg, description, sort_order "
            "FROM recycle_category WHERE id = %s",
            (category_id,),
        )
        row = cursor.fetchone()

        data = {
            "id": row["id"],
            "category_code": f"CAT{row['id']:03d}",
            "name": row["name"],
            "icon": row["icon"],
            "points_per_kg": row["points_per_kg"],
            "description": row["description"],
            "sort_order": row["sort_order"],
        }
        return jsonify(data)

    @app.route("/api/categories/<int:category_id>", methods=["DELETE"])
    def delete_category(category_id: int):
        """删除回收品类。

        若该品类已被订单明细引用，将返回 400，避免破坏外键约束。
        """

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT id FROM recycle_category WHERE id = %s",
            (category_id,),
        )
        if not cursor.fetchone():
            return jsonify({"error": "Category not found"}), 404

        try:
            cursor.execute(
                "DELETE FROM recycle_category WHERE id = %s",
                (category_id,),
            )
        except IntegrityError:
            return (
                jsonify(
                    {
                        "error": "Category is in use and cannot be deleted",
                    },
                ),
                400,
            )

        return jsonify({"success": True})

    @app.route("/api/stations", methods=["GET"])
    def list_stations():
        """回收网点列表与统计，供 admin-stations.html 使用。"""

        db = get_db()
        cursor = db.cursor()

        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 10)), 100)
        search = request.args.get("search", "").strip()
        station_type = request.args.get("type", "").strip() or None
        status_id = request.args.get("status_id")

        where: list[str] = []
        params: list[object] = []

        if search:
            where.append(
                "(s.name LIKE %s OR s.address_detail LIKE %s OR s.city LIKE %s)",
            )
            like = f"%{search}%"
            params.extend([like, like, like])

        if station_type:
            where.append("s.type = %s")
            params.append(station_type)

        if status_id:
            where.append("s.status_id = %s")
            params.append(status_id)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        base_from = (
            " FROM recycle_station s "
            "LEFT JOIN station_status st ON s.status_id = st.id "
        )

        # 统计总数及各状态数量（基于当前筛选条件）
        cursor.execute(
            "SELECT "
            "COUNT(*) AS total, "
            "SUM(CASE WHEN s.status_id = 1 THEN 1 ELSE 0 END) AS running_count, "
            "SUM(CASE WHEN s.status_id = 2 THEN 1 ELSE 0 END) AS maintenance_count, "
            "SUM(CASE WHEN s.status_id = 3 THEN 1 ELSE 0 END) AS disabled_count "
            + base_from
            + where_sql,
            params,
        )
        stat_row = cursor.fetchone() or {}
        total = stat_row.get("total", 0)

        cursor.execute(
            "SELECT "
            "s.id, s.name, s.type, s.status_id, st.name AS status_name, "
            "s.province, s.city, s.district, s.address_detail, "
            "s.latitude, s.longitude, s.opening_hours, s.contact_phone, s.created_at "
            + base_from
            + where_sql
            + " ORDER BY s.created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        rows = cursor.fetchall()

        items: list[dict] = []
        for row in rows:
            address_parts = [
                row.get("province"),
                row.get("city"),
                row.get("district"),
                row.get("address_detail"),
            ]
            full_address = "".join(part for part in address_parts if part) or None
            created_at = row.get("created_at")
            items.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "type": row["type"],
                    "status_id": row["status_id"],
                    "status_name": row["status_name"],
                    "province": row["province"],
                    "city": row["city"],
                    "district": row["district"],
                    "address_detail": row["address_detail"],
                    "full_address": full_address,
                    "latitude": float(row["latitude"]) if row.get("latitude") is not None else None,
                    "longitude": float(row["longitude"]) if row.get("longitude") is not None else None,
                    "opening_hours": row["opening_hours"],
                    "contact_phone": row["contact_phone"],
                    "created_at": (
                        created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if created_at
                        else None
                    ),
                },
            )

        stats = {
            "total_stations": total,
            "running": stat_row.get("running_count", 0),
            "maintenance": stat_row.get("maintenance_count", 0),
            "disabled": stat_row.get("disabled_count", 0),
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

    @app.route("/api/stations", methods=["POST"])
    def create_station():
        """创建新的回收网点，供 admin-stations.html 的“添加网点”使用。"""

        db = get_db()
        cursor = db.cursor()

        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400

        station_type = (data.get("type") or "").strip() or None
        province = (data.get("province") or "").strip() or None
        city = (data.get("city") or "").strip() or None
        district = (data.get("district") or "").strip() or None
        address_detail = (data.get("address_detail") or "").strip() or None
        opening_hours = (data.get("opening_hours") or "").strip() or None
        contact_phone = (data.get("contact_phone") or "").strip() or None
        remark = (data.get("remark") or "").strip() or None

        status_id_raw = data.get("status_id")
        status_id: int | None = 1
        if status_id_raw not in (None, ""):
            try:
                status_id = int(status_id_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "status_id must be an integer"}), 400

        latitude = None
        longitude = None
        lat_raw = data.get("latitude")
        lon_raw = data.get("longitude")
        if lat_raw not in (None, ""):
            try:
                latitude = float(lat_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "latitude must be a number"}), 400
        if lon_raw not in (None, ""):
            try:
                longitude = float(lon_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "longitude must be a number"}), 400

        cursor.execute(
            "INSERT INTO recycle_station (name, type, status_id, province, city, district, "
            "address_detail, latitude, longitude, opening_hours, contact_phone, remark) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                name,
                station_type,
                status_id,
                province,
                city,
                district,
                address_detail,
                latitude,
                longitude,
                opening_hours,
                contact_phone,
                remark,
            ),
        )
        new_id = cursor.lastrowid

        cursor.execute(
            "SELECT "
            "s.id, s.name, s.type, s.status_id, st.name AS status_name, "
            "s.province, s.city, s.district, s.address_detail, "
            "s.latitude, s.longitude, s.opening_hours, s.contact_phone, s.created_at "
            "FROM recycle_station s "
            "LEFT JOIN station_status st ON s.status_id = st.id "
            "WHERE s.id = %s",
            (new_id,),
        )
        row = cursor.fetchone()

        address_parts = [
            row.get("province"),
            row.get("city"),
            row.get("district"),
            row.get("address_detail"),
        ]
        full_address = "".join(part for part in address_parts if part) or None
        created_at = row.get("created_at")

        data = {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "status_id": row["status_id"],
            "status_name": row["status_name"],
            "province": row["province"],
            "city": row["city"],
            "district": row["district"],
            "address_detail": row["address_detail"],
            "full_address": full_address,
            "latitude": float(row["latitude"]) if row.get("latitude") is not None else None,
            "longitude": float(row["longitude"]) if row.get("longitude") is not None else None,
            "opening_hours": row["opening_hours"],
            "contact_phone": row["contact_phone"],
            "created_at": (
                created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else None
            ),
        }
        return jsonify(data), 201

    @app.route("/api/after_sales", methods=["GET"])
    def list_after_sales():
        """售后工单列表与统计，供 admin-aftersale.html 使用。"""

        db = get_db()
        cursor = db.cursor()

        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 10)), 100)
        search = request.args.get("search", "").strip()
        status = request.args.get("status")
        ticket_type = request.args.get("type", "").strip() or None
        date_start = request.args.get("date_start")
        date_end = request.args.get("date_end")

        where: list[str] = []
        params: list[object] = []

        if search:
            where.append(
                "(CAST(a.id AS CHAR) LIKE %s OR o.order_no LIKE %s OR u.nickname LIKE %s)",
            )
            like = f"%{search}%"
            params.extend([like, like, like])

        if status:
            where.append("a.status = %s")
            params.append(status)

        if ticket_type:
            where.append("a.type = %s")
            params.append(ticket_type)

        if date_start:
            where.append("DATE(a.created_at) >= %s")
            params.append(date_start)

        if date_end:
            where.append("DATE(a.created_at) <= %s")
            params.append(date_end)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        base_from = (
            " FROM after_sale a "
            "JOIN user u ON a.user_id = u.id "
            "JOIN recycle_order o ON a.order_id = o.id "
        )

        cursor.execute(
            "SELECT "
            "COUNT(*) AS total, "
            "SUM(CASE WHEN a.status = 1 THEN 1 ELSE 0 END) AS pending_count, "
            "SUM(CASE WHEN a.status = 2 THEN 1 ELSE 0 END) AS processing_count, "
            "SUM(CASE WHEN a.status = 3 THEN 1 ELSE 0 END) AS resolved_count, "
            "SUM(CASE WHEN a.status = 4 THEN 1 ELSE 0 END) AS closed_count "
            + base_from
            + where_sql,
            params,
        )
        stat_row = cursor.fetchone() or {}
        total = stat_row.get("total", 0)

        cursor.execute(
            "SELECT "
            "a.id, a.order_id, a.user_id, a.type, a.description, a.status, "
            "a.created_at, a.resolved_at, "
            "u.nickname, u.avatar_url, "
            "o.order_no "
            + base_from
            + where_sql
            + " ORDER BY a.created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        rows = cursor.fetchall()

        items: list[dict] = []
        for row in rows:
            created_at = row.get("created_at")
            resolved_at = row.get("resolved_at")
            items.append(
                {
                    "id": row["id"],
                    "order_id": row["order_id"],
                    "order_no": row["order_no"],
                    "user_id": row["user_id"],
                    "user_nickname": row["nickname"],
                    "user_avatar_url": row["avatar_url"],
                    "type": row["type"],
                    "description": row["description"],
                    "status": row["status"],
                    "status_label": AFTER_SALE_STATUS_LABELS.get(row["status"], "未知"),
                    "created_at": (
                        created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if created_at
                        else None
                    ),
                    "resolved_at": (
                        resolved_at.strftime("%Y-%m-%d %H:%M:%S")
                        if resolved_at
                        else None
                    ),
                },
            )

        resolved = stat_row.get("resolved_count", 0) or 0
        resolve_rate = float(resolved) / float(total) * 100 if total else 0.0

        stats = {
            "total_tickets": total,
            "pending": stat_row.get("pending_count", 0),
            "processing": stat_row.get("processing_count", 0),
            "resolved": resolved,
            "closed": stat_row.get("closed_count", 0),
            "resolve_rate": round(resolve_rate, 1),
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

	    # ========== 社区帖子管理（管理端） ==========

	    @app.route("/api/admin/posts", methods=["GET"])
	    def admin_list_posts():
	        """社区帖子列表，供 admin-posts.html 使用。"""
	        db = get_db()
	        cursor = db.cursor()

	        page = max(int(request.args.get("page", 1)), 1)
	        per_page = min(int(request.args.get("per_page", 10)), 100)
	        search = request.args.get("search", "").strip()
	        topic_id = request.args.get("topic_id")
	        status = request.args.get("status")

	        where: list[str] = []
	        params: list[object] = []

	        if status not in (None, ""):
	            where.append("p.status = %s")
	            params.append(status)

	        if topic_id:
	            where.append("p.topic_id = %s")
	            params.append(topic_id)

	        if search:
	            where.append("(p.content LIKE %s OR u.nickname LIKE %s)")
	            like = f"%{search}%"
	            params.extend([like, like])

	        where_sql = " WHERE " + " AND ".join(where) if where else ""
	        base_from = (
	            " FROM community_post p "
	            "JOIN user u ON p.user_id = u.id "
	            "LEFT JOIN community_topic t ON p.topic_id = t.id "
	        )

	        cursor.execute(
	            "SELECT COUNT(*) AS total" + base_from + where_sql,
	            params,
	        )
	        total = cursor.fetchone()["total"]

	        cursor.execute(
	            "SELECT "
	            "p.id, p.content, p.image_urls, p.like_count, p.comment_count, p.status, "
	            "p.created_at, "
	            "u.id AS user_id, u.nickname, u.avatar_url, "
	            "t.id AS topic_id, t.name AS topic_name "
	            + base_from
	            + where_sql
	            + " ORDER BY p.created_at DESC LIMIT %s OFFSET %s",
	            params + [per_page, (page - 1) * per_page],
	        )
	        rows = cursor.fetchall()

	        items: list[dict] = []
	        for row in rows:
	            created_at = row.get("created_at")
	            images: list[str] | None = None
	            if row.get("image_urls"):
	                try:
	                    parsed = json.loads(row["image_urls"])
	                    if isinstance(parsed, list):
	                        images = parsed
	                except Exception:
	                    images = None

	            items.append(
	                {
	                    "id": row["id"],
	                    "content": row["content"],
	                    "images": images,
	                    "like_count": row["like_count"],
	                    "comment_count": row["comment_count"],
	                    "status": row["status"],
	                    "status_label": "正常" if row["status"] == 1 else "已删除",
	                    "created_at": (
	                        created_at.strftime("%Y-%m-%d %H:%M:%S")
	                        if created_at
	                        else None
	                    ),
	                    "user": {
	                        "id": row["user_id"],
	                        "nickname": row["nickname"],
	                        "avatar_url": row["avatar_url"],
	                    },
	                    "topic": (
	                        {
	                            "id": row["topic_id"],
	                            "name": row["topic_name"],
	                        }
	                        if row.get("topic_id")
	                        else None
	                    ),
	                },
	            )

	        return jsonify(
	            {"total": total, "page": page, "per_page": per_page, "items": items},
	        )

	    @app.route("/api/admin/posts/<int:post_id>", methods=["DELETE"])
	    def admin_delete_post(post_id: int):
	        """社区帖子删除（逻辑删除，status 置为 0）。"""
	        db = get_db()
	        cursor = db.cursor()

	        cursor.execute(
	            "SELECT id, status FROM community_post WHERE id = %s",
	            (post_id,),
	        )
	        row = cursor.fetchone()
	        if not row:
	            return jsonify({"error": "Post not found"}), 404

	        if row["status"] == 0:
	            # 已经是删除状态，视为成功
	            return jsonify({"success": True, "id": post_id})

	        cursor.execute(
	            "UPDATE community_post SET status = 0 WHERE id = %s",
	            (post_id,),
	        )
	        db.commit()
	        return jsonify({"success": True, "id": post_id})

    @app.route("/api/orders", methods=["GET"])
    def list_orders():
        """订单列表与状态统计，供 admin-orders.html 使用。

        支持的查询参数（全部可选）：
        - page: 页码，默认 1
        - per_page: 每页数量，默认 10，最大 100
        - search: 模糊搜索，匹配订单号 / 用户昵称 / 手机号
        - status: 订单状态（1待上门/2进行中/3已完成/4已取消/5售后）
        - date_start, date_end: 预约日期范围过滤（YYYY-MM-DD）
        """

        db = get_db()
        cursor = db.cursor()

        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 10)), 100)
        search = request.args.get("search", "").strip()
        status = request.args.get("status")
        date_start = request.args.get("date_start")
        date_end = request.args.get("date_end")

        where = []
        params: list[object] = []

        if search:
            where.append(
                "(o.order_no LIKE %s OR u.nickname LIKE %s OR u.phone LIKE %s)",
            )
            like = f"%{search}%"
            params.extend([like, like, like])

        if status:
            where.append("o.status = %s")
            params.append(status)

        if date_start:
            where.append("o.appointment_date >= %s")
            params.append(date_start)

        if date_end:
            where.append("o.appointment_date <= %s")
            params.append(date_end)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        base_from = (
            " FROM recycle_order o "
            "JOIN user u ON o.user_id = u.id "
            "LEFT JOIN user_address a ON o.address_id = a.id "
            "LEFT JOIN collector c ON o.collector_id = c.id "
        )

        # 统计总数及各状态数量（基于当前筛选条件）
        cursor.execute(
            "SELECT "
            "COUNT(*) AS total, "
            "SUM(CASE WHEN o.status = 1 THEN 1 ELSE 0 END) AS pending_count, "
            "SUM(CASE WHEN o.status = 2 THEN 1 ELSE 0 END) AS processing_count, "
            "SUM(CASE WHEN o.status = 3 THEN 1 ELSE 0 END) AS completed_count, "
            "SUM(CASE WHEN o.status = 4 THEN 1 ELSE 0 END) AS canceled_count "
            + base_from
            + where_sql,
            params,
        )
        stat_row = cursor.fetchone() or {}
        total = stat_row.get("total", 0)

        # 查询当前页订单
        cursor.execute(
            "SELECT "
            "o.id, o.order_no, o.status, o.appointment_date, o.time_slot, "
            "o.estimated_points, o.actual_points, o.carbon_saved_kg, o.created_at, "
            "u.nickname AS user_name, u.phone AS user_phone, "
            "a.province, a.city, a.district, a.address_detail, "
            "c.name AS collector_name, c.phone AS collector_phone "
            + base_from
            + where_sql
            + " ORDER BY o.created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        rows = cursor.fetchall()

        order_ids = [row["id"] for row in rows]
        items_by_order: dict[int, list[dict]] = {}

        if order_ids:
            placeholders = ",".join(["%s"] * len(order_ids))
            cursor.execute(
                "SELECT "
                "i.order_id, i.estimated_weight, i.actual_weight, i.points_earned, "
                "rc.name AS category_name "
                "FROM order_item i "
                "JOIN recycle_category rc ON i.category_id = rc.id "
                f"WHERE i.order_id IN ({placeholders})",
                order_ids,
            )
            for item in cursor.fetchall():
                items_by_order.setdefault(item["order_id"], []).append(item)

        items: list[dict] = []
        for row in rows:
            order_items = items_by_order.get(row["id"], [])
            categories = [it["category_name"] for it in order_items]
            estimated_weight = order_items[0]["estimated_weight"] if order_items else None

            address_parts = [
                row.get("province"),
                row.get("city"),
                row.get("district"),
                row.get("address_detail"),
            ]
            address = "".join(part for part in address_parts if part) or None

            carbon = row["carbon_saved_kg"]

            items.append(
                {
                    "id": row["id"],
                    "order_no": row["order_no"],
                    "status": row["status"],
                    "status_label": ORDER_STATUS_LABELS.get(row["status"], "未知"),
                    "user_name": row["user_name"],
                    "user_phone": row["user_phone"],
                    "categories": categories,
                    "estimated_weight": estimated_weight,
                    "appointment_date": (
                        row["appointment_date"].strftime("%Y-%m-%d")
                        if row["appointment_date"]
                        else None
                    ),
                    "time_slot": row["time_slot"],
                    "address": address,
                    "collector_name": row["collector_name"],
                    "collector_phone": row["collector_phone"],
                    "estimated_points": row["estimated_points"],
                    "actual_points": row["actual_points"],
                    "carbon_saved_kg": float(carbon) if carbon is not None else 0.0,
                    "created_at": (
                        row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                        if row["created_at"]
                        else None
                    ),
                },
            )

        stats = {
            "total_orders": total,
            "pending": stat_row.get("pending_count", 0),
            "processing": stat_row.get("processing_count", 0),
            "completed": stat_row.get("completed_count", 0),
            "canceled": stat_row.get("canceled_count", 0),
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

    @app.route("/api/orders/<int:order_id>", methods=["GET"])
    def order_detail(order_id: int):
        """订单详情，含用户、地址、回收员及各品类明细。"""

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT
              o.*, u.nickname AS user_name, u.phone AS user_phone,
              a.province, a.city, a.district, a.address_detail,
              c.name AS collector_name, c.phone AS collector_phone
            FROM recycle_order o
            JOIN user u ON o.user_id = u.id
            LEFT JOIN user_address a ON o.address_id = a.id
            LEFT JOIN collector c ON o.collector_id = c.id
            WHERE o.id = %s
            """,
            (order_id,),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Order not found"}), 404

        cursor.execute(
            """
            SELECT
              i.order_id, i.category_id, i.estimated_weight, i.actual_weight,
              i.points_earned, rc.name AS category_name
            FROM order_item i
            JOIN recycle_category rc ON i.category_id = rc.id
            WHERE i.order_id = %s
            ORDER BY i.id
            """,
            (order_id,),
        )
        item_rows = cursor.fetchall()

        address_parts = [
            row.get("province"),
            row.get("city"),
            row.get("district"),
            row.get("address_detail"),
        ]
        address = "".join(part for part in address_parts if part) or None

        carbon = row["carbon_saved_kg"]

        photo_urls: list[str] | None = None
        if row.get("photo_urls"):
            try:
                parsed = json.loads(row["photo_urls"])
                if isinstance(parsed, list):
                    photo_urls = parsed
            except Exception:
                photo_urls = None

        items = [
            {
                "category_id": it["category_id"],
                "category_name": it["category_name"],
                "estimated_weight": it["estimated_weight"],
                "actual_weight": float(it["actual_weight"])
                if it["actual_weight"] is not None
                else None,
                "points_earned": it["points_earned"],
            }
            for it in item_rows
        ]

        data = {
            "id": row["id"],
            "order_no": row["order_no"],
            "status": row["status"],
            "status_label": ORDER_STATUS_LABELS.get(row["status"], "未知"),
            "user": {
                "id": row["user_id"],
                "nickname": row["user_name"],
                "phone": row["user_phone"],
            },
            "appointment_date": (
                row["appointment_date"].strftime("%Y-%m-%d")
                if row["appointment_date"]
                else None
            ),
            "time_slot": row["time_slot"],
            "address": address,
            "collector": (
                {
                    "id": row["collector_id"],
                    "name": row["collector_name"],
                    "phone": row["collector_phone"],
                }
                if row.get("collector_id")
                else None
            ),
            "estimated_points": row["estimated_points"],
            "actual_points": row["actual_points"],
            "carbon_saved_kg": float(carbon) if carbon is not None else 0.0,
            "remark": row["remark"],
            "photo_urls": photo_urls,
            "created_at": (
                row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                if row["created_at"]
                else None
            ),
            "updated_at": (
                row["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
                if row["updated_at"]
                else None
            ),
            "completed_at": (
                row["completed_at"].strftime("%Y-%m-%d %H:%M:%S")
                if row["completed_at"]
                else None
            ),
            "items": items,
        }

        return jsonify(data)

    # ========== 回收员管理接口 ==========
    @app.route("/api/collectors", methods=["GET"])
    def list_collectors():
        """回收员列表与统计，供 admin-collectors.html 使用。"""
        db = get_db()
        cursor = db.cursor()

        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 10)), 100)
        search = request.args.get("search", "").strip()
        status = request.args.get("status")

        where: list[str] = []
        params: list[object] = []

        if search:
            where.append("(name LIKE %s OR phone LIKE %s)")
            like = f"%{search}%"
            params.extend([like, like])

        if status is not None and status != "":
            where.append("status = %s")
            params.append(status)

        where_sql = " WHERE " + " AND ".join(where) if where else ""

        # 统计
        cursor.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS online_count, "
            "SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS offline_count, "
            "SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS disabled_count "
            "FROM collector" + where_sql,
            params,
        )
        stat_row = cursor.fetchone() or {}
        total = stat_row.get("total", 0)

        cursor.execute(
            "SELECT id, name, phone, avatar_url, rating, status, created_at "
            "FROM collector" + where_sql +
            " ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        rows = cursor.fetchall()

        items: list[dict] = []
        for row in rows:
            created_at = row.get("created_at")
            items.append({
                "id": row["id"],
                "collector_code": f"C{row['id']:05d}",
                "name": row["name"],
                "phone": row["phone"],
                "avatar_url": row["avatar_url"],
                "rating": float(row["rating"]) if row.get("rating") else None,
                "status": row["status"],
                "status_label": COLLECTOR_STATUS_LABELS.get(row["status"], "未知"),
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else None,
            })

        stats = {
            "total_collectors": total,
            "online": stat_row.get("online_count", 0) or 0,
            "offline": stat_row.get("offline_count", 0) or 0,
            "disabled": stat_row.get("disabled_count", 0) or 0,
        }

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": items,
            "stats": stats,
        })

    # ========== 用户地址管理接口 ==========
    @app.route("/api/addresses", methods=["GET"])
    def list_addresses():
        """用户地址列表，供 admin-address.html 使用。"""
        db = get_db()
        cursor = db.cursor()

        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(int(request.args.get("per_page", 10)), 100)
        search = request.args.get("search", "").strip()
        user_id = request.args.get("user_id")

        where: list[str] = []
        params: list[object] = []

        if search:
            where.append(
                "(a.name LIKE %s OR a.phone LIKE %s OR a.address_detail LIKE %s OR u.nickname LIKE %s)"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like])

        if user_id:
            where.append("a.user_id = %s")
            params.append(user_id)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        base_from = " FROM user_address a JOIN user u ON a.user_id = u.id "

        cursor.execute(
            "SELECT COUNT(*) AS total" + base_from + where_sql,
            params,
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT a.id, a.user_id, a.name, a.phone, a.province, a.city, a.district, "
            "a.address_detail, a.tag, a.is_default, a.created_at, u.nickname AS user_nickname "
            + base_from + where_sql +
            " ORDER BY a.created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, (page - 1) * per_page],
        )
        rows = cursor.fetchall()

        items: list[dict] = []
        for row in rows:
            address_parts = [row.get("province"), row.get("city"), row.get("district"), row.get("address_detail")]
            full_address = "".join(part for part in address_parts if part) or None
            created_at = row.get("created_at")
            items.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "user_nickname": row["user_nickname"],
                "name": row["name"],
                "phone": row["phone"],
                "province": row["province"],
                "city": row["city"],
                "district": row["district"],
                "address_detail": row["address_detail"],
                "full_address": full_address,
                "tag": row["tag"],
                "is_default": row["is_default"],
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else None,
            })

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": items,
        })

    # ========== 小程序端 API ==========

    @app.route("/api/mp/user", methods=["GET"])
    def mp_get_user():
        """小程序端：获取当前用户信息（模拟，实际需要登录态）"""
        db = get_db()
        cursor = db.cursor()
        # 模拟返回第一个用户作为当前用户
        cursor.execute("""
            SELECT u.*, l.level_name
            FROM user u
            LEFT JOIN user_level l ON u.level_id = l.id
            WHERE u.id = 1
        """)
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        carbon = row["total_carbon_kg"]
        return jsonify({
            "id": row["id"],
            "nickname": row["nickname"],
            "avatar_url": row["avatar_url"],
            "phone": row["phone"],
            "level_name": row["level_name"],
            "total_points": row["total_points"],
            "current_points": row["current_points"],
            "total_carbon_kg": float(carbon) if carbon else 0.0,
            "recycle_count": row["recycle_count"],
        })

	    @app.route("/api/mp/community/topics", methods=["GET"])
	    def mp_list_topics():
	        """
  """
	        
	        
	        
	        
	        db = get_db()
	        cursor = db.cursor()

	        cursor.execute(
	            "SELECT id, name, description, is_hot, sort_order "
	            "FROM community_topic ORDER BY sort_order IS NULL, sort_order, id",
	        )
	        rows = cursor.fetchall()

	        items: list[dict] = []
	        for row in rows:
	            items.append(
	                {
	                    "id": row["id"],
	                    "name": row["name"],
	                    "description": row["description"],
	                    "is_hot": bool(row["is_hot"]),
	                    "sort_order": row["sort_order"],
	                },
	            )

	        return jsonify({"items": items})

	    @app.route("/api/mp/community/posts", methods=["GET"])
	    def mp_list_posts():
	        """

	        """
	        
	        db = get_db()
	        cursor = db.cursor()

	        page = max(int(request.args.get("page", 1)), 1)
	        per_page = min(int(request.args.get("per_page", 10)), 20)
	        topic_id = request.args.get("topic_id")
	        search = request.args.get("search", "").strip()

	        where: list[str] = ["p.status = 1"]
	        params: list[object] = []

	        if topic_id:
	            where.append("p.topic_id = %s")
	            params.append(topic_id)

	        if search:
	            where.append("p.content LIKE %s")
	            params.append(f"%{search}%")

	        where_sql = " WHERE " + " AND ".join(where) if where else ""
	        base_from = (
	            " FROM community_post p "
	            "JOIN user u ON p.user_id = u.id "
	            "LEFT JOIN community_topic t ON p.topic_id = t.id "
	        )

	        cursor.execute(
	            "SELECT COUNT(*) AS total" + base_from + where_sql,
	            params,
	        )
	        total = cursor.fetchone()["total"]

	        cursor.execute(
	            "SELECT "
	            "p.id, p.content, p.image_urls, p.like_count, p.comment_count, p.created_at, "
	            "u.id AS user_id, u.nickname, u.avatar_url, "
	            "t.id AS topic_id, t.name AS topic_name "
	            + base_from
	            + where_sql
	            + " ORDER BY p.created_at DESC LIMIT %s OFFSET %s",
	            params + [per_page, (page - 1) * per_page],
	        )
	        rows = cursor.fetchall()

	        items: list[dict] = []
	        for row in rows:
	            created_at = row.get("created_at")
	            images: list[str] | None = None
	            if row.get("image_urls"):
	                try:
	                    parsed = json.loads(row["image_urls"])
	                    if isinstance(parsed, list):
	                        images = parsed
	                except Exception:
	                    images = None

	            items.append(
	                {
	                    "id": row["id"],
	                    "content": row["content"],
	                    "images": images,
	                    "like_count": row["like_count"],
	                    "comment_count": row["comment_count"],
	                    "created_at": (
	                        created_at.strftime("%Y-%m-%d %H:%M")
	                        if created_at
	                        else None
	                    ),
	                    "user": {
	                        "id": row["user_id"],
	                        "nickname": row["nickname"],
	                        "avatar_url": row["avatar_url"],
	                    },
	                    "topic": (
	                        {
	                            "id": row["topic_id"],
	                            "name": row["topic_name"],
	                        }
	                        if row.get("topic_id")
	                        else None
	                    ),
	                },
	            )

	        return jsonify(
	            {"total": total, "page": page, "per_page": per_page, "items": items},
	        )

	    @app.route("/api/mp/community/posts", methods=["POST"])
	    def mp_create_post():
	        """

	        """
	        db = get_db()
	        cursor = db.cursor()

	        data = request.get_json(silent=True) or {}
	        user_id = data.get("user_id") or 1  # TODO: 
	        content = (data.get("content") or "").strip()
	        if not content:
	            return jsonify({"error": ""}), 400

	        topic_id = data.get("topic_id")
	        images = data.get("images") or data.get("image_urls")
	        image_urls = None
	        if isinstance(images, list) and images:
	            try:
	                image_urls = json.dumps(images, ensure_ascii=False)
	            except Exception:
	                image_urls = None

	        cursor.execute(
	            "INSERT INTO community_post (user_id, topic_id, content, image_urls) "
	            "VALUES (%s, %s, %s, %s)",
	            (user_id, topic_id, content, image_urls),
	        )
	        post_id = cursor.lastrowid
	        db.commit()

	        return jsonify({"success": True, "id": post_id}), 201

    @app.route("/api/mp/orders", methods=["GET"])
    def mp_list_orders():
        """小程序端：获取当前用户的订单列表"""
        db = get_db()
        cursor = db.cursor()

        user_id = request.args.get("user_id", 1)  # 模拟当前用户
        status = request.args.get("status")

        where = ["o.user_id = %s"]
        params: list[object] = [user_id]

        if status:
            where.append("o.status = %s")
            params.append(status)

        where_sql = " WHERE " + " AND ".join(where)

        cursor.execute(
            "SELECT o.id, o.order_no, o.status, o.appointment_date, o.time_slot, "
            "o.estimated_points, o.actual_points, o.carbon_saved_kg, o.created_at, o.completed_at, "
            "c.name AS collector_name, c.phone AS collector_phone "
            "FROM recycle_order o "
            "LEFT JOIN collector c ON o.collector_id = c.id "
            + where_sql + " ORDER BY o.created_at DESC",
            params,
        )
        rows = cursor.fetchall()

        # 获取订单明细
        order_ids = [row["id"] for row in rows]
        items_by_order: dict[int, list] = {}
        if order_ids:
            placeholders = ",".join(["%s"] * len(order_ids))
            cursor.execute(
                f"SELECT i.order_id, rc.name AS category_name, i.estimated_weight, i.actual_weight "
                f"FROM order_item i JOIN recycle_category rc ON i.category_id = rc.id "
                f"WHERE i.order_id IN ({placeholders})",
                order_ids,
            )
            for item in cursor.fetchall():
                items_by_order.setdefault(item["order_id"], []).append(item)

        orders = []
        for row in rows:
            order_items = items_by_order.get(row["id"], [])
            categories = ", ".join([it["category_name"] for it in order_items])
            weight = order_items[0]["estimated_weight"] if order_items else None

            orders.append({
                "id": row["id"],
                "order_no": row["order_no"],
                "status": row["status"],
                "status_label": ORDER_STATUS_LABELS.get(row["status"], "未知"),
                "categories": categories,
                "estimated_weight": weight,
                "appointment_date": row["appointment_date"].strftime("%Y-%m-%d") if row["appointment_date"] else None,
                "time_slot": row["time_slot"],
                "collector_name": row["collector_name"],
                "collector_phone": row["collector_phone"],
                "estimated_points": row["estimated_points"],
                "actual_points": row["actual_points"],
                "carbon_saved_kg": float(row["carbon_saved_kg"]) if row["carbon_saved_kg"] else 0.0,
                "created_at": row["created_at"].strftime("%Y-%m-%d %H:%M") if row["created_at"] else None,
                "completed_at": row["completed_at"].strftime("%Y-%m-%d %H:%M") if row["completed_at"] else None,
            })

        return jsonify({"orders": orders})

    @app.route("/api/mp/orders", methods=["POST"])
    def mp_create_order():
        """小程序端：创建预约回收订单"""
        db = get_db()
        cursor = db.cursor()

        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id", 1)  # 模拟当前用户
        category_id = data.get("category_id")
        estimated_weight = data.get("estimated_weight", "5-10kg")
        appointment_date = data.get("appointment_date")
        time_slot = data.get("time_slot")
        address_id = data.get("address_id")
        remark = data.get("remark", "")

        if not category_id or not appointment_date or not time_slot:
            return jsonify({"error": "缺少必填参数"}), 400

        # 生成订单号
        import time
        order_no = time.strftime("%Y%m%d") + str(int(time.time() * 1000) % 100000).zfill(5)

        # 计算预估积分
        cursor.execute("SELECT points_per_kg FROM recycle_category WHERE id = %s", (category_id,))
        cat_row = cursor.fetchone()
        points_per_kg = cat_row["points_per_kg"] if cat_row else 10
        estimated_points = points_per_kg * 5  # 假设5kg

        cursor.execute(
            "INSERT INTO recycle_order (order_no, user_id, address_id, status, appointment_date, "
            "time_slot, estimated_points, remark) VALUES (%s, %s, %s, 1, %s, %s, %s, %s)",
            (order_no, user_id, address_id, appointment_date, time_slot, estimated_points, remark),
        )
        order_id = cursor.lastrowid

        # 插入订单明细
        cursor.execute(
            "INSERT INTO order_item (order_id, category_id, estimated_weight) VALUES (%s, %s, %s)",
            (order_id, category_id, estimated_weight),
        )

        return jsonify({
            "success": True,
            "order_id": order_id,
            "order_no": order_no,
            "message": "预约成功",
        }), 201

    @app.route("/api/mp/orders/<int:order_id>/cancel", methods=["POST"])
    def mp_cancel_order(order_id):
        """小程序端：取消订单"""
        db = get_db()
        cursor = db.cursor()
        user_id = 1  # 模拟当前用户

        # 检查订单是否存在且属于当前用户
        cursor.execute(
            "SELECT id, status FROM recycle_order WHERE id = %s AND user_id = %s",
            (order_id, user_id)
        )
        order = cursor.fetchone()
        if not order:
            return jsonify({"error": "订单不存在"}), 404

        if order["status"] != 1:
            return jsonify({"error": "只能取消待上门的订单"}), 400

        # 更新订单状态为已取消 (status=4)
        cursor.execute(
            "UPDATE recycle_order SET status = 4 WHERE id = %s",
            (order_id,)
        )

        return jsonify({"success": True, "message": "订单已取消"})

    @app.route("/api/mp/ranking", methods=["GET"])
    def mp_ranking():
        """小程序端：积分/减碳排行榜"""
        db = get_db()
        cursor = db.cursor()

        rank_type = request.args.get("type", "points")  # points 或 carbon
        limit = min(int(request.args.get("limit", 20)), 50)

        if rank_type == "carbon":
            order_by = "total_carbon_kg DESC"
            score_field = "total_carbon_kg"
        else:
            order_by = "total_points DESC"
            score_field = "total_points"

        cursor.execute(
            f"SELECT id, nickname, avatar_url, {score_field} AS score, recycle_count "
            f"FROM user ORDER BY {order_by} LIMIT %s",
            (limit,),
        )
        rows = cursor.fetchall()

        ranking = []
        for idx, row in enumerate(rows):
            score = row["score"]
            ranking.append({
                "rank": idx + 1,
                "user_id": row["id"],
                "nickname": row["nickname"],
                "avatar_url": row["avatar_url"],
                "score": float(score) if score else 0,
                "recycle_count": row["recycle_count"],
            })

        return jsonify({"type": rank_type, "ranking": ranking})

    @app.route("/api/mp/identify", methods=["POST"])
    def mp_identify_rubbish():
        """小程序端：智能拍照垃圾分类识别

        请求：multipart/form-data，字段名为 ``file``。
        返回：
        {
          "success": true,
          "name": "PET 塑料瓶",
          "category": "可回收物",
          "confidence": 0.98,
          "points": 10,
          "tip": "请倒空液体，压扁投放"
        }
        """

        if "file" not in request.files:
            return jsonify({"success": False, "error": "缺少图片文件"}), 400

        image_file = request.files["file"]
        if image_file.filename == "":
            return jsonify({"success": False, "error": "空文件名"}), 400

        # 从环境变量读取阿里云 AccessKey，避免写死在代码里
        access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        if not access_key_id or not access_key_secret:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "阿里云访问密钥未配置，请在服务器环境变量中设置 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET",
                    }
                ),
                500,
            )

        try:
            # 延迟导入阿里云 SDK，避免在未安装依赖时应用无法启动
            from alibabacloud_imagerecog20190930.client import (  # type: ignore[import]
                Client as ImagerecogClient,
            )
            from alibabacloud_imagerecog20190930.models import (  # type: ignore[import]
                ClassifyingRubbishAdvanceRequest,
            )
            from alibabacloud_tea_openapi.models import (  # type: ignore[import]
                Config as AliyunConfig,
            )
            from alibabacloud_tea_util.models import RuntimeOptions  # type: ignore[import]
        except ImportError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "服务器未安装阿里云识别 SDK，请先在虚拟环境中执行 'pip install alibabacloud_imagerecog20190930'",
                    }
                ),
                500,
            )

        # 读取上传的图片为二进制流
        image_bytes = image_file.read()
        if not image_bytes:
            return jsonify({"success": False, "error": "图片内容为空"}), 400

        img_stream = io.BytesIO(image_bytes)

        # 构造阿里云客户端
        config = AliyunConfig(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="imagerecog.cn-shanghai.aliyuncs.com",
            region_id="cn-shanghai",
        )

        try:
            client = ImagerecogClient(config)

            request_model = ClassifyingRubbishAdvanceRequest()
            # 按官方示例使用 image_urlobject 传入二进制流
            request_model.image_urlobject = img_stream

            runtime = RuntimeOptions()
            response = client.classifying_rubbish_advance(request_model, runtime)

            body = response.body
            category = None
            rubbish_name = None
            confidence = None

            # 尽量从返回结构中解析出我们需要的字段
            try:
                if hasattr(body, "to_map"):
                    data_map = body.to_map()  # type: ignore[no-untyped-call]
                else:
                    data_map = None
            except Exception:
                data_map = None

            if isinstance(data_map, dict):
                elements = (
                    (data_map.get("Data") or {}).get("Elements")  # type: ignore[assignment]
                    or []
                )
                if elements:
                    first = elements[0] or {}
                    category = first.get("Category")
                    # 不同版本字段名可能不同，做兼容处理
                    rubbish_name = (
                        first.get("Rubbish")
                        or first.get("Name")
                        or first.get("ItemName")
                    )
                    confidence = first.get("Score") or first.get("Confidence")

            # 根据类别简单映射一个项目内使用的积分和提示语
            tip = "请根据提示正确投放"
            points = 5
            if category in ("可回收物", "recyclable"):
                points = 10
                tip = "请清空残留物并压扁后投放至可回收物桶"
            elif category in ("厨余垃圾", "household_food_waste"):
                points = 8
                tip = "请沥干水分后投放至厨余垃圾桶"
            elif category in ("有害垃圾", "hazardous"):
                points = 0
                tip = "请密封包装后投放至有害垃圾桶，避免破损泄漏"
            elif category in ("其他垃圾", "residual_waste"):
                points = 5
                tip = "请尽量减少此类垃圾产生，按指引投放"

            result = {
                "success": True,
                "name": rubbish_name or "未知物品",
                "category": category or "未知分类",
                "confidence": float(confidence) if confidence is not None else None,
                "points": points,
                "tip": tip,
            }

            return jsonify(result)
        except Exception as exc:  # pragma: no cover - 外部服务异常
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "调用阿里云识别服务失败",
                        "detail": str(exc),
                    }
                ),
                502,
            )

    @app.route("/api/mp/addresses", methods=["GET"])
    def mp_list_addresses():
        """小程序端：获取当前用户地址列表"""
        db = get_db()
        cursor = db.cursor()
        user_id = request.args.get("user_id", 1) # 模拟

        cursor.execute(
            "SELECT * FROM user_address WHERE user_id = %s ORDER BY is_default DESC, created_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row["id"],
                "name": row["name"],
                "phone": row["phone"],
                "province": row["province"],
                "city": row["city"],
                "district": row["district"],
                "address_detail": row["address_detail"],
                "full_address": f"{row['province']}{row['city']}{row['district']}{row['address_detail']}",
                "tag": row["tag"],
                "is_default": row["is_default"]
            })
            
        return jsonify({"items": items})

    @app.route("/api/mp/addresses", methods=["POST"])
    def mp_create_address():
        """小程序端：创建地址"""
        db = get_db()
        cursor = db.cursor()
        data = request.get_json(silent=True) or {}
        user_id = 1 # 模拟

        if data.get("is_default"):
            cursor.execute("UPDATE user_address SET is_default = 0 WHERE user_id = %s", (user_id,))

        cursor.execute(
            "INSERT INTO user_address (user_id, name, phone, province, city, district, address_detail, tag, is_default) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, data.get("name"), data.get("phone"), data.get("province"), data.get("city"), 
             data.get("district"), data.get("address_detail"), data.get("tag"), data.get("is_default", 0))
        )
        return jsonify({"success": True, "id": cursor.lastrowid}), 201

    @app.route("/api/mp/addresses/<int:id>", methods=["PUT"])
    def mp_update_address(id):
        """小程序端：更新地址"""
        db = get_db()
        cursor = db.cursor()
        data = request.get_json(silent=True) or {}
        user_id = 1 # 模拟

        if data.get("is_default"):
            cursor.execute("UPDATE user_address SET is_default = 0 WHERE user_id = %s", (user_id,))

        cursor.execute(
            "UPDATE user_address SET name=%s, phone=%s, province=%s, city=%s, district=%s, "
            "address_detail=%s, tag=%s, is_default=%s WHERE id=%s AND user_id=%s",
            (data.get("name"), data.get("phone"), data.get("province"), data.get("city"), 
             data.get("district"), data.get("address_detail"), data.get("tag"), 
             data.get("is_default", 0), id, user_id)
        )
        return jsonify({"success": True})

    @app.route("/api/mp/addresses/<int:id>", methods=["DELETE"])
    def mp_delete_address(id):
        """小程序端：删除地址"""
        db = get_db()
        cursor = db.cursor()
        user_id = 1 # 模拟
        cursor.execute("DELETE FROM user_address WHERE id=%s AND user_id=%s", (id, user_id))
        return jsonify({"success": True})


app = create_app()


if __name__ == "__main__":
    # 默认在 http://127.0.0.1:5000 监听，便于与前端联调
    app.run(debug=True)

