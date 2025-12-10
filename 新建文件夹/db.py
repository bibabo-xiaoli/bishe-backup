"""简单的 MySQL 访问封装，基于 PyMySQL 和 Flask 的应用上下文。"""

import pymysql
import pymysql.cursors
from flask import current_app, g


def get_db():
    """在当前请求上下文中获取一个共享的数据库连接。"""
    if "db" not in g:
        cfg = current_app.config["MYSQL"]
        g.db = pymysql.connect(
            host=cfg["HOST"],
            port=cfg["PORT"],
            user=cfg["USER"],
            password=cfg["PASSWORD"],
            database=cfg["DB"],
            charset=cfg.get("CHARSET", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    return g.db


def close_db(e=None):
    """在请求结束时关闭连接。"""
    db = g.pop("db", None)
    if db is not None:
        db.close()

