import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    user='root',
    password='114856',
    database='bishe',
    charset='utf8mb4'
)
cursor = conn.cursor()

# 添加status字段
cursor.execute('ALTER TABLE user ADD COLUMN status TINYINT DEFAULT 1')
conn.commit()
print('Added status column successfully')
conn.close()
