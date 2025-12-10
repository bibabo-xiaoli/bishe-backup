"""智能回收小程序后台：Flask + MySQL 8.0 RESTful API.

当前实现内容：
- /api/health                健康检查
- /api/users                 用户列表（分页、搜索、等级筛选）
- /api/users/<id>            用户详情
- /api/dashboard/summary     仪表盘汇总数据
"""

from datetime import date
import json

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
            "u.total_carbon_kg, u.recycle_count, u.created_at, l.level_name "
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
                    "status": "正常",  # 目前未在表中单独存储状态
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


app = create_app()


if __name__ == "__main__":
    # 默认在 http://127.0.0.1:5000 监听，便于与前端联调
    app.run(debug=True)

