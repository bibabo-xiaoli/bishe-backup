-- 智能回收小程序 - MySQL 8.0 核心表结构
-- 依据 ui/数据库表.md 设计，覆盖后台当前用到的主要表

CREATE DATABASE IF NOT EXISTS bishe
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE bishe;

-- 1. 用户模块 -----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  openid VARCHAR(64) NOT NULL,
  nickname VARCHAR(50),
  avatar_url VARCHAR(255),
  phone VARCHAR(20),
  total_points INT DEFAULT 0,
  current_points INT DEFAULT 0,
  total_carbon_kg DECIMAL(10,2) DEFAULT 0.00,
  recycle_count INT DEFAULT 0,
  level_id INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_openid (openid),
  KEY idx_user_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_address (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(50),
  phone VARCHAR(20),
  province VARCHAR(50),
  city VARCHAR(50),
  district VARCHAR(50),
  address_detail VARCHAR(255),
  tag VARCHAR(20),
  is_default TINYINT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_address_user (user_id),
  CONSTRAINT fk_user_address_user FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_level (
  id INT PRIMARY KEY AUTO_INCREMENT,
  level_name VARCHAR(50),
  min_points INT,
  max_points INT,
  badge_icon VARCHAR(255),
  description VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 回收订单模块 -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recycle_category (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  icon VARCHAR(100),
  points_per_kg INT,
  description VARCHAR(255),
  sort_order INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS collector (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  phone VARCHAR(20),
  avatar_url VARCHAR(255),
  rating DECIMAL(2,1),
  status TINYINT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recycle_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_no VARCHAR(32) NOT NULL,
  user_id BIGINT NOT NULL,
  address_id BIGINT,
  collector_id BIGINT,
  status TINYINT,
  appointment_date DATE,
  time_slot VARCHAR(20),
  estimated_points INT,
  actual_points INT,
  carbon_saved_kg DECIMAL(10,2),
  photo_urls TEXT,
  remark VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  completed_at DATETIME,
  UNIQUE KEY uk_order_no (order_no),
  KEY idx_order_user (user_id),
  KEY idx_order_status (status),
  CONSTRAINT fk_order_user FOREIGN KEY (user_id) REFERENCES user(id),
  CONSTRAINT fk_order_address FOREIGN KEY (address_id) REFERENCES user_address(id),
  CONSTRAINT fk_order_collector FOREIGN KEY (collector_id) REFERENCES collector(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS order_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  category_id INT NOT NULL,
  estimated_weight VARCHAR(20),
  actual_weight DECIMAL(10,2),
  points_earned INT,
  KEY idx_order_item_order (order_id),
  KEY idx_order_item_category (category_id),
  CONSTRAINT fk_item_order FOREIGN KEY (order_id) REFERENCES recycle_order(id),
  CONSTRAINT fk_item_category FOREIGN KEY (category_id) REFERENCES recycle_category(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 积分记录（用于统计积分发放）---------------------------------------------

CREATE TABLE IF NOT EXISTS points_record (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  points INT NOT NULL,
  type TINYINT NOT NULL, -- 1 获得 / 2 消费
  source VARCHAR(50),
  related_id BIGINT,
  description VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_points_user (user_id),
  KEY idx_points_created_at (created_at),
  CONSTRAINT fk_points_user FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
 
-- 4. 回收网点模块 -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS station_status (
  id TINYINT PRIMARY KEY,
  name VARCHAR(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 预置网点状态：1 运行中 / 2 维护中 / 3 已停用
INSERT INTO station_status (id, name) VALUES
  (1, '运行中'),
  (2, '维护中'),
  (3, '已停用')
ON DUPLICATE KEY UPDATE
  name = VALUES(name);

CREATE TABLE IF NOT EXISTS recycle_station (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  type VARCHAR(20), -- 智能回收柜 / 服务站
  status_id TINYINT,
  province VARCHAR(50),
  city VARCHAR(50),
  district VARCHAR(50),
  address_detail VARCHAR(255),
  latitude DECIMAL(10,6),
  longitude DECIMAL(10,6),
  opening_hours VARCHAR(100),
  contact_phone VARCHAR(20),
  remark VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_station_status (status_id),
  KEY idx_station_type (type),
  KEY idx_station_city (city),
  CONSTRAINT fk_station_status FOREIGN KEY (status_id) REFERENCES station_status(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 售后工单模块 -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS after_sale (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  type VARCHAR(50), -- 积分问题 / 订单问题 / 回收员问题 / 其他问题
  description VARCHAR(255),
  status TINYINT, -- 1 待处理 / 2 处理中 / 3 已解决 / 4 已关闭
  reply TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME,
  KEY idx_after_sale_order (order_id),
  KEY idx_after_sale_user (user_id),
  KEY idx_after_sale_status (status),
  KEY idx_after_sale_created_at (created_at),
  CONSTRAINT fk_after_sale_order FOREIGN KEY (order_id) REFERENCES recycle_order(id),
  CONSTRAINT fk_after_sale_user FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
