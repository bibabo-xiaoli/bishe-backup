-- 智能回收小程序 - 测试数据
-- 在执行 schema.sql 后执行此脚本

USE bishe;

-- 1. 用户等级数据
INSERT INTO user_level (id, level_name, min_points, max_points, badge_icon, description) VALUES
(1, 'Lv.1 环保新手', 0, 500, 'ph-plant', '刚刚加入环保大家庭'),
(2, 'Lv.2 环保入门', 501, 1500, 'ph-leaf', '开始养成环保习惯'),
(3, 'Lv.3 环保达人', 1501, 5000, 'ph-tree', '环保意识逐渐增强'),
(4, 'Lv.4 环保专家', 5001, 15000, 'ph-mountains', '环保行动的践行者'),
(5, 'Lv.5 环保大师', 15001, 999999, 'ph-globe-hemisphere-west', '环保事业的推动者')
ON DUPLICATE KEY UPDATE
  level_name = VALUES(level_name),
  min_points = VALUES(min_points),
  max_points = VALUES(max_points);

-- 2. 回收品类数据
INSERT INTO recycle_category (id, name, icon, points_per_kg, description, sort_order) VALUES
(1, '纸板箱', 'ph-package', 15, '各类纸箱、纸板', 1),
(2, '旧衣物', 'ph-t-shirt', 20, '旧衣服、鞋帽、床上用品', 2),
(3, '塑料瓶', 'ph-beer-bottle', 25, 'PET塑料瓶、塑料容器', 3),
(4, '废旧家电', 'ph-monitor', 30, '小家电、电子产品', 4),
(5, '书籍报刊', 'ph-book', 12, '书籍、杂志、报纸', 5),
(6, '金属制品', 'ph-wrench', 35, '易拉罐、金属器具', 6),
(7, '玻璃制品', 'ph-wine', 10, '玻璃瓶、玻璃容器', 7),
(8, '其他', 'ph-squares-four', 10, '其他可回收物品', 8)
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  icon = VALUES(icon),
  points_per_kg = VALUES(points_per_kg);

-- 3. 测试用户数据
INSERT INTO user (id, openid, nickname, avatar_url, phone, total_points, current_points, total_carbon_kg, recycle_count, level_id, created_at) VALUES
(1, 'wx_user_001', '张三', 'https://i.pravatar.cc/100?img=1', '13800000001', 1200, 800, 25.50, 15, 2, DATE_SUB(NOW(), INTERVAL 30 DAY)),
(2, 'wx_user_002', '李四', 'https://i.pravatar.cc/100?img=2', '13800000002', 3500, 2100, 68.30, 42, 3, DATE_SUB(NOW(), INTERVAL 25 DAY)),
(3, 'wx_user_003', '王五', 'https://i.pravatar.cc/100?img=3', '13800000003', 850, 450, 18.20, 10, 2, DATE_SUB(NOW(), INTERVAL 20 DAY)),
(4, 'wx_user_004', '赵六', 'https://i.pravatar.cc/100?img=4', '13800000004', 6200, 4800, 125.80, 78, 4, DATE_SUB(NOW(), INTERVAL 60 DAY)),
(5, 'wx_user_005', '钱七', 'https://i.pravatar.cc/100?img=5', '13800000005', 320, 320, 8.50, 5, 1, DATE_SUB(NOW(), INTERVAL 10 DAY)),
(6, 'wx_user_006', '孙八', 'https://i.pravatar.cc/100?img=6', '13800000006', 2100, 1500, 45.60, 28, 3, DATE_SUB(NOW(), INTERVAL 45 DAY)),
(7, 'wx_user_007', '周九', 'https://i.pravatar.cc/100?img=7', '13800000007', 150, 150, 3.20, 2, 1, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(8, 'wx_user_008', '吴十', 'https://i.pravatar.cc/100?img=8', '13800000008', 4800, 3200, 98.40, 55, 3, DATE_SUB(NOW(), INTERVAL 50 DAY)),
(9, 'wx_user_009', '郑十一', 'https://i.pravatar.cc/100?img=9', '13800000009', 18500, 12000, 380.50, 210, 5, DATE_SUB(NOW(), INTERVAL 180 DAY)),
(10, 'wx_user_010', '冯十二', 'https://i.pravatar.cc/100?img=10', '13800000010', 580, 280, 12.80, 8, 2, DATE_SUB(NOW(), INTERVAL 15 DAY)),
(11, 'wx_user_011', '陈十三', 'https://i.pravatar.cc/100?img=11', '13800000011', 0, 0, 0, 0, 1, NOW()),
(12, 'wx_user_012', '褚十四', 'https://i.pravatar.cc/100?img=12', '13800000012', 50, 50, 1.20, 1, 1, DATE_SUB(NOW(), INTERVAL 2 DAY))
ON DUPLICATE KEY UPDATE nickname = VALUES(nickname);

-- 4. 用户地址数据
INSERT INTO user_address (id, user_id, name, phone, province, city, district, address_detail, tag, is_default) VALUES
(1, 1, '张三', '13800000001', '重庆市', '渝北区', '龙溪街道', '金龙路168号龙湖时代天街A座1202', '家', 1),
(2, 1, '张三', '13800000001', '重庆市', '江北区', '观音桥街道', '北城天街购物中心B栋', '公司', 0),
(3, 2, '李四', '13800000002', '重庆市', '南岸区', '南坪街道', '万达广场3号楼1805', '家', 1),
(4, 3, '王五', '13800000003', '重庆市', '沙坪坝区', '三峡广场街道', '融汇温泉城A区5栋', '家', 1),
(5, 4, '赵六', '13800000004', '重庆市', '九龙坡区', '杨家坪街道', '西城天街2栋2501', '家', 1),
(6, 5, '钱七', '13800000005', '重庆市', '渝中区', '解放碑街道', '国泰广场1栋1001', '家', 1)
ON DUPLICATE KEY UPDATE address_detail = VALUES(address_detail);

-- 5. 回收员数据
INSERT INTO collector (id, name, phone, avatar_url, rating, status, created_at) VALUES
(1, '李师傅', '15800000001', 'https://i.pravatar.cc/100?img=51', 4.8, 1, DATE_SUB(NOW(), INTERVAL 120 DAY)),
(2, '张师傅', '15800000002', 'https://i.pravatar.cc/100?img=52', 4.9, 1, DATE_SUB(NOW(), INTERVAL 100 DAY)),
(3, '王师傅', '15800000003', 'https://i.pravatar.cc/100?img=53', 4.7, 1, DATE_SUB(NOW(), INTERVAL 80 DAY)),
(4, '刘师傅', '15800000004', 'https://i.pravatar.cc/100?img=54', 4.6, 0, DATE_SUB(NOW(), INTERVAL 60 DAY)),
(5, '陈师傅', '15800000005', 'https://i.pravatar.cc/100?img=55', 4.5, 1, DATE_SUB(NOW(), INTERVAL 40 DAY)),
(6, '杨师傅', '15800000006', 'https://i.pravatar.cc/100?img=56', 4.8, 2, DATE_SUB(NOW(), INTERVAL 90 DAY))
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 6. 回收订单数据
INSERT INTO recycle_order (id, order_no, user_id, address_id, collector_id, status, appointment_date, time_slot, estimated_points, actual_points, carbon_saved_kg, remark, created_at, completed_at) VALUES
(1, '20231201001', 1, 1, 1, 3, DATE_SUB(CURDATE(), INTERVAL 5 DAY), '09:00-11:00', 150, 180, 3.60, '请准时上门', DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 5 DAY)),
(2, '20231201002', 2, 3, 2, 3, DATE_SUB(CURDATE(), INTERVAL 4 DAY), '14:00-16:00', 200, 220, 4.40, NULL, DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY)),
(3, '20231202001', 3, 4, 3, 3, DATE_SUB(CURDATE(), INTERVAL 3 DAY), '10:00-12:00', 80, 95, 1.90, '家里有狗', DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY)),
(4, '20231202002', 4, 5, 1, 3, DATE_SUB(CURDATE(), INTERVAL 2 DAY), '09:00-11:00', 350, 380, 7.60, NULL, DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
(5, '20231203001', 1, 1, NULL, 1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00-11:00', 120, NULL, NULL, '纸箱较多', NOW(), NULL),
(6, '20231203002', 2, 3, 2, 2, CURDATE(), '14:00-16:00', 180, NULL, NULL, NULL, DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(7, '20231203003', 5, 6, NULL, 1, DATE_ADD(CURDATE(), INTERVAL 2 DAY), '10:00-12:00', 60, NULL, NULL, '第一次使用', NOW(), NULL),
(8, '20231203004', 6, NULL, 3, 2, CURDATE(), '16:00-18:00', 250, NULL, NULL, '大件家电', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
(9, '20231130001', 7, NULL, NULL, 4, DATE_SUB(CURDATE(), INTERVAL 7 DAY), '09:00-11:00', 50, NULL, NULL, '取消原因：临时有事', DATE_SUB(NOW(), INTERVAL 7 DAY), NULL),
(10, '20231128001', 8, NULL, 1, 3, DATE_SUB(CURDATE(), INTERVAL 10 DAY), '14:00-16:00', 280, 310, 6.20, NULL, DATE_SUB(NOW(), INTERVAL 10 DAY), DATE_SUB(NOW(), INTERVAL 10 DAY))
ON DUPLICATE KEY UPDATE order_no = VALUES(order_no);

-- 7. 订单明细数据
INSERT INTO order_item (id, order_id, category_id, estimated_weight, actual_weight, points_earned) VALUES
(1, 1, 1, '5-10 kg', 8.50, 128),
(2, 1, 2, '2-5 kg', 3.20, 52),
(3, 2, 3, '3-5 kg', 4.80, 120),
(4, 2, 1, '5-10 kg', 6.20, 93),
(5, 3, 5, '3-5 kg', 4.50, 54),
(6, 4, 4, '10-20 kg', 15.80, 474),
(7, 5, 1, '5-10 kg', NULL, NULL),
(8, 6, 2, '5-10 kg', NULL, NULL),
(9, 6, 3, '2-5 kg', NULL, NULL),
(10, 7, 1, '2-5 kg', NULL, NULL),
(11, 8, 4, '10-20 kg', NULL, NULL),
(12, 10, 1, '10-20 kg', 12.50, 188),
(13, 10, 2, '5-10 kg', 8.20, 122)
ON DUPLICATE KEY UPDATE order_id = VALUES(order_id);

-- 8. 积分记录数据
INSERT INTO points_record (id, user_id, points, type, source, related_id, description, created_at) VALUES
(1, 1, 180, 1, 'recycle', 1, '回收订单完成奖励', DATE_SUB(NOW(), INTERVAL 5 DAY)),
(2, 2, 220, 1, 'recycle', 2, '回收订单完成奖励', DATE_SUB(NOW(), INTERVAL 4 DAY)),
(3, 3, 95, 1, 'recycle', 3, '回收订单完成奖励', DATE_SUB(NOW(), INTERVAL 3 DAY)),
(4, 4, 380, 1, 'recycle', 4, '回收订单完成奖励', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(5, 8, 310, 1, 'recycle', 10, '回收订单完成奖励', DATE_SUB(NOW(), INTERVAL 10 DAY)),
(6, 1, -100, 2, 'mall', NULL, '积分商城兑换', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(7, 2, -50, 2, 'mall', NULL, '积分商城兑换', DATE_SUB(NOW(), INTERVAL 2 DAY))
ON DUPLICATE KEY UPDATE points = VALUES(points);

-- 9. 回收网点数据
INSERT INTO recycle_station (id, name, type, status_id, province, city, district, address_detail, latitude, longitude, opening_hours, contact_phone, remark) VALUES
(1, '龙湖时代天街智能回收站', '智能回收柜', 1, '重庆市', '渝北区', '龙溪街道', '龙湖时代天街A区负一楼', 29.5647, 106.5123, '24小时', '023-88880001', '大型商场内'),
(2, '观音桥步行街回收点', '服务站', 1, '重庆市', '江北区', '观音桥街道', '观音桥步行街北城天街入口处', 29.5712, 106.5456, '08:00-20:00', '023-88880002', '人流量大'),
(3, '南坪万达广场智能柜', '智能回收柜', 1, '重庆市', '南岸区', '南坪街道', '万达广场1号门旁', 29.5234, 106.5678, '24小时', '023-88880003', NULL),
(4, '解放碑环保服务站', '服务站', 2, '重庆市', '渝中区', '解放碑街道', '解放碑步行街国泰广场B1', 29.5589, 106.5789, '09:00-21:00', '023-88880004', '维护中'),
(5, '杨家坪智能回收柜', '智能回收柜', 1, '重庆市', '九龙坡区', '杨家坪街道', '杨家坪步行街中心', 29.5012, 106.5234, '24小时', '023-88880005', NULL),
(6, '沙坪坝三峡广场站', '服务站', 3, '重庆市', '沙坪坝区', '三峡广场街道', '三峡广场王府井百货旁', 29.5678, 106.4567, '08:00-18:00', '023-88880006', '已停用')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 10. 售后工单数据
INSERT INTO after_sale (id, order_id, user_id, type, description, status, reply, created_at, resolved_at) VALUES
(1, 1, 1, '积分问题', '订单完成后积分未到账', 3, '已核实并补发积分，请查收', DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY)),
(2, 2, 2, '回收员问题', '回收员迟到30分钟', 3, '已对回收员进行提醒，感谢反馈', DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
(3, 3, 3, '订单问题', '实际重量与预估差异较大', 2, NULL, DATE_SUB(NOW(), INTERVAL 2 DAY), NULL),
(4, 4, 4, '其他问题', '希望增加更多回收品类', 4, '感谢建议，已反馈至产品部门', DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY)),
(5, 10, 8, '积分问题', '积分兑换商品未收到', 1, NULL, NOW(), NULL),
(6, 6, 2, '回收员问题', '回收员态度不好', 1, NULL, NOW(), NULL)
ON DUPLICATE KEY UPDATE description = VALUES(description);

SELECT '测试数据插入完成！' AS message;
