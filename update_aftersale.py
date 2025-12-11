# -*- coding: utf-8 -*-
import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    user='root',
    password='114856',
    database='bishe',
    charset='utf8mb4'
)
cursor = conn.cursor()

# 更新售后数据
updates = [
    (1, '重量争议', '回收员称重与实际重量不符，少了约2公斤', '已核实并补发积分差额'),
    (2, '积分未到账', '回收完成后30分钟积分仍未到账', '系统延迟已修复，积分已补发'),
    (3, '服务态度', '回收员态度不好，催促太急', None),
    (4, '预约取消', '回收员未按时上门导致取消', '已对回收员进行提醒处理'),
    (5, '物品损坏', '回收过程中物品被损坏', None),
    (6, '价格问题', '回收价格与标价不一致', None),
]

for id, type_val, desc, reply in updates:
    if reply:
        cursor.execute(
            "UPDATE after_sale SET type=%s, description=%s, reply=%s WHERE id=%s",
            (type_val, desc, reply, id)
        )
    else:
        cursor.execute(
            "UPDATE after_sale SET type=%s, description=%s WHERE id=%s",
            (type_val, desc, id)
        )
    print(f"Updated after_sale {id}: {type_val}")

conn.commit()
print("All after_sale records updated successfully!")
conn.close()
