import os


class Config:
    """基础配置：Flask + MySQL 8.0.

    默认使用本地 MySQL 数据库 bishe，账号 root/114856，
    可以通过环境变量覆盖：
      MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB
    """

    DEBUG = True
    JSON_AS_ASCII = False  # 返回 JSON 时保留中文

    MYSQL = {
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "PORT": int(os.getenv("MYSQL_PORT", "3306")),
        "USER": os.getenv("MYSQL_USER", "root"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD", "114856"),
        "DB": os.getenv("MYSQL_DB", "bishe"),
        "CHARSET": "utf8mb4",
    }

    @staticmethod
    def init_app(app):
        """预留扩展点，目前无需额外初始化逻辑。"""
        pass

