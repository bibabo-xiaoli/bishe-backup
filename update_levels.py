import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    user='root',
    password='114856',
    database='bishe',
    charset='utf8mb4'
)
cursor = conn.cursor()

# 更新用户昵称和等级
user_updates = [
    (1, '小辰', 1),    # 萌新豆 - 小辰
    (2, '阿柚', 1),    # 萌新豆 - 阿柚
    (3, '清禾', 1),    # 萌新豆 - 清禾
    (4, '阿泽', 2),    # 活跃星 - 阿泽
    (5, '苏郁', 2),    # 活跃星 - 苏郁
    (6, '乐屿', 2),    # 活跃星 - 乐屿
    (7, '知南', 3),    # 进阶客 - 知南
    (8, '星野', 3),    # 进阶客 - 星野
    (9, '云杉', 3),    # 进阶客 - 云杉
    (10, '晚柠', 1),   # 萌新豆 - 晚柠
    (11, '林一', 2),   # 活跃星 - 林一
    (12, '苏郁', 3),   # 进阶客 - 苏郁
]

for user_id, nickname, level_id in user_updates:
    cursor.execute("UPDATE user SET nickname=%s, level_id=%s WHERE id=%s", (nickname, level_id, user_id))
    print(f"Updated user {user_id} to {nickname} (level {level_id})")

conn.commit()
print("All users updated successfully!")
conn.close()
