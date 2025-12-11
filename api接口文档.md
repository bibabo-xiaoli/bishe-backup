# API 接口文档（当前已实现部分）

后端技术栈：Python + Flask + PyMySQL  
数据库：MySQL 8.0，数据库名：`bishe`

后端入口：`admin/app.py`  
数据库连接配置：`admin/config.py`

> 说明：以下为当前已实现并与前端管理系统联通的接口；未来扩展接口（订单、积分商城、社区等）可在此文档继续补充。

---

## 1. 健康检查

### `GET /api/health`

- **功能**：检查后端服务是否正常运行。
- **请求参数**：无
- **响应示例**：

```json
{
  "status": "ok"
}
```

---

## 2. 用户列表

### `GET /api/users`

- **功能**：获取用户列表，支持分页、关键字搜索与后续等级筛选。用于 `ui/admin-users.html` 的“用户管理”页面。
- **请求方式**：`GET`
- **请求参数（QueryString）**：

| 参数名     | 类型   | 必填 | 说明                                             |
| ---------- | ------ | ---- | ------------------------------------------------ |
| `page`     | int    | 否   | 页码，默认 `1`，最小为 1                       |
| `per_page` | int    | 否   | 每页数量，默认 `10`，最大 `100`                 |
| `search`   | string | 否   | 关键字（昵称 / 手机号 / 用户 ID 模糊匹配）     |
| `level_id` | int    | 否   | 用户等级 ID（预留，当前前端尚未实际传入）      |

- **业务说明**：
  - 查询来源表：`user`（左联 `user_level`）。
  - `search` 同时匹配 `nickname`、`phone` 以及 `id`（转为字符串）
  - 返回结果按 `created_at` 倒序排列。

- **响应字段说明**：

```json
{
  "total": 100,           // 总记录数
  "page": 1,              // 当前页码
  "per_page": 10,         // 每页数量
  "items": [
    {
      "id": 1,
      "user_code": "U00001",        // 前端显示用的用户编码
      "nickname": "环保小卫士",
      "avatar_url": "https://...",  // 头像 URL，可为空
      "phone": "13800000000",
      "level_name": "Lv.3 绿色达人", // 来自 user_level 表，可为空
      "current_points": 2850,        // 当前积分
      "total_carbon_kg": 45.2,       // 累计减碳量（kg）
      "recycle_count": 28,           // 累计回收次数
      "status": "正常",             // 当前未从表中区分禁用状态，默认“正常”
      "created_at": "2023-08-15 10:30:25" // 注册时间
    }
  ]
}
```

- **前端使用说明（`admin-users.html`）**：
  - 页面加载时调用一次：`GET /api/users?page=1&per_page=10`
  - 点击“查询”按钮时，根据搜索框内容重新请求：`/api/users?search=xxx`
  - 返回的 `items` 用于动态生成用户表格行。

---

## 3. 用户详情

### `GET /api/users/{id}`

- **功能**：获取单个用户的详细信息，包括等级与默认地址信息。预留给“用户详情弹窗”使用。
- **请求方式**：`GET`
- **路径参数**：

| 参数名 | 类型 | 必填 | 说明       |
| ------ | ---- | ---- | ---------- |
| `id`   | int  | 是   | 用户主键ID |

- **数据来源表**：`user`、`user_level`、`user_address`（仅 `is_default = 1` 的地址）。

- **成功响应示例**：

```json
{
  "id": 1,
  "user_code": "U00001",
  "nickname": "环保小卫士",
  "avatar_url": "https://...",
  "phone": "13800000000",
  "level_name": "Lv.3 绿色达人",
  "total_points": 5680,
  "current_points": 2850,
  "total_carbon_kg": 45.2,
  "recycle_count": 28,
  "created_at": "2023-08-15 10:30:25",
  "updated_at": "2023-10-24 09:15:00",
  "status": "正常",
  "default_address": {
    "province": "北京市",
    "city": "朝阳区",
    "district": "XXX街道",
    "address_detail": "阳光100国际公寓A座1202"
  }
}
```

- **错误响应示例**：

```json
{
  "error": "User not found"
}
```

HTTP 状态码：`404`

---

## 4. 仪表盘汇总数据

### `GET /api/dashboard/summary`

- **功能**：为管理后台首页（`ui/admin.html`）以及用户管理页顶部统计卡片提供汇总数据。
- **请求方式**：`GET`
- **请求参数**：无
- **数据来源表**：
  - `user`：用户总数、活跃用户（`recycle_count > 0`）、今日新增用户
  - `recycle_order`：今日订单数量、今日减碳量
  - `points_record`：累计积分发放、今日积分发放

- **响应字段说明与示例**：

```json
{
  "total_users": 12580,          // 用户总数（user 表计数）
  "today_new_users": 156,        // 今日新增用户数
  "active_users": 8420,          // 有回收记录的用户数
  "disabled_users": 0,           // 预留，当前未在表中单独维护禁用状态
  "today_orders": 3842,          // 今日订单数
  "today_carbon_kg": 1256.0,     // 今日减碳量（kg），来源 recycle_order.carbon_saved_kg
  "total_points_earned": 58420,  // 累计积分发放总量（points_record，type = 1）
  "today_points_earned": 1234    // 今日积分发放量（points_record，type = 1，且为今日）
}
```

- **前端使用说明**：
  - `ui/admin.html`
    - 读取以上字段，填充四个大卡片：
      - `total_users` → 注册用户（`#dashboard-total-users`）
      - `today_orders` → 今日订单（`#dashboard-today-orders`）
      - `today_carbon_kg` → 今日减碳量（`#dashboard-today-carbon`）
      - `total_points_earned` → 积分发放（`#dashboard-total-points`）
  - `ui/admin-users.html`
    - 使用：
      - `total_users` → 总用户数（`#user-total`）
      - `today_new_users` → 今日新增（`#user-today-new`）
      - `active_users` → 活跃用户（`#user-active-count`）
      - `disabled_users` → 已禁用（`#user-disabled-count`）

---

## 5. 订单管理

### `GET /api/orders`

- **功能**：订单列表与状态统计，供 `ui/admin-orders.html` 使用。
- **请求参数（QueryString）**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `per_page` | int | 否 | 每页数量，默认 10，最大 100 |
| `search` | string | 否 | 模糊搜索（订单号/用户昵称/手机号）|
| `status` | int | 否 | 订单状态（1待上门/2进行中/3已完成/4已取消/5售后）|
| `date_start` | string | 否 | 预约日期起始（YYYY-MM-DD）|
| `date_end` | string | 否 | 预约日期结束（YYYY-MM-DD）|

- **响应示例**：

```json
{
  "total": 10,
  "page": 1,
  "per_page": 10,
  "items": [...],
  "stats": {
    "total_orders": 10,
    "pending": 2,
    "processing": 2,
    "completed": 5,
    "canceled": 1
  }
}
```

### `GET /api/orders/{id}`

- **功能**：订单详情，含用户、地址、回收员及各品类明细。

---

## 6. 用户等级管理

### `GET /api/user_levels`

- **功能**：用户等级列表及每个等级的用户数，供 `ui/admin-levels.html` 使用。
- **响应示例**：

```json
{
  "total": 5,
  "items": [
    {
      "id": 1,
      "name": "Lv.1 环保新手",
      "min_points": 0,
      "max_points": 500,
      "badge_icon": "ph-plant",
      "description": "刚刚加入环保大家庭",
      "user_count": 3
    }
  ]
}
```

---

## 7. 回收品类管理

### `GET /api/categories`

- **功能**：回收品类列表，供 `ui/admin-categories.html` 使用。
- **请求参数**：`page`, `per_page`, `search`

### `POST /api/categories`

- **功能**：创建新的回收品类。
- **请求体**：`name`(必填), `icon`, `points_per_kg`, `description`, `sort_order`

### `PUT /api/categories/{id}`

- **功能**：更新回收品类配置。

### `DELETE /api/categories/{id}`

- **功能**：删除回收品类（若已被订单引用则返回 400）。

---

## 8. 回收网点管理

### `GET /api/stations`

- **功能**：回收网点列表与统计，供 `ui/admin-stations.html` 使用。
- **请求参数**：`page`, `per_page`, `search`, `type`, `status_id`
- **响应示例**：

```json
{
  "total": 6,
  "page": 1,
  "per_page": 10,
  "items": [...],
  "stats": {
    "total_stations": 6,
    "running": 4,
    "maintenance": 1,
    "disabled": 1
  }
}
```

### `POST /api/stations`

- **功能**：创建新的回收网点。
- **请求体**：`name`(必填), `type`, `status_id`, `province`, `city`, `district`, `address_detail`, `latitude`, `longitude`, `opening_hours`, `contact_phone`, `remark`

---

## 9. 回收员管理

### `GET /api/collectors`

- **功能**：回收员列表与统计，供 `ui/admin-collectors.html` 使用。
- **请求参数**：`page`, `per_page`, `search`, `status`
- **响应示例**：

```json
{
  "total": 6,
  "page": 1,
  "per_page": 10,
  "items": [
    {
      "id": 1,
      "collector_code": "C00001",
      "name": "李师傅",
      "phone": "15800000001",
      "avatar_url": "...",
      "rating": 4.8,
      "status": 1,
      "status_label": "在线",
      "created_at": "2023-08-13 02:23:47"
    }
  ],
  "stats": {
    "total_collectors": 6,
    "online": 4,
    "offline": 1,
    "disabled": 1
  }
}
```

---

## 10. 售后工单管理

### `GET /api/after_sales`

- **功能**：售后工单列表与统计，供 `ui/admin-aftersale.html` 使用。
- **请求参数**：`page`, `per_page`, `search`, `status`, `type`, `date_start`, `date_end`
- **响应示例**：

```json
{
  "total": 6,
  "page": 1,
  "per_page": 10,
  "items": [
    {
      "id": 1,
      "order_id": 1,
      "order_no": "20231201001",
      "user_id": 1,
      "user_nickname": "张三",
      "type": "积分问题",
      "description": "订单完成后积分未到账",
      "status": 3,
      "status_label": "已解决",
      "created_at": "2023-12-07 02:23:47",
      "resolved_at": "2023-12-08 02:23:47"
    }
  ],
  "stats": {
    "total_tickets": 6,
    "pending": 2,
    "processing": 1,
    "resolved": 2,
    "closed": 1,
    "resolve_rate": 33.3
  }
}
```

---

## 11. 用户地址管理

### `GET /api/addresses`

- **功能**：用户地址列表，供 `ui/admin-address.html` 使用。
- **请求参数**：`page`, `per_page`, `search`, `user_id`
- **响应示例**：

```json
{
  "total": 6,
  "page": 1,
  "per_page": 10,
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "user_nickname": "张三",
      "name": "张三",
      "phone": "13800000001",
      "province": "重庆市",
      "city": "渝北区",
      "district": "龙溪街道",
      "address_detail": "金龙路168号龙湖时代天街A座1202",
      "full_address": "重庆市渝北区龙溪街道金龙路168号龙湖时代天街A座1202",
      "tag": "家",
      "is_default": 1,
      "created_at": "2023-11-11 02:23:47"
    }
  ]
}
```

---

## 12. 小程序端 API

### `GET /api/mp/user`

- **功能**：获取当前用户信息（模拟用户ID=1）
- **响应示例**：

```json
{
  "id": 1,
  "nickname": "张三",
  "avatar_url": "https://i.pravatar.cc/100?img=1",
  "phone": "13800000001",
  "level_name": "Lv.2 环保入门",
  "total_points": 1200,
  "current_points": 800,
  "total_carbon_kg": 25.5,
  "recycle_count": 15
}
```

### `GET /api/mp/orders`

- **功能**：获取当前用户的订单列表
- **请求参数**：`user_id`(可选), `status`(可选)
- **响应示例**：

```json
{
  "orders": [
    {
      "id": 1,
      "order_no": "20231201001",
      "status": 3,
      "status_label": "已完成",
      "categories": "纸板箱, 旧衣物",
      "estimated_weight": "5-10 kg",
      "appointment_date": "2025-12-06",
      "time_slot": "09:00-11:00",
      "collector_name": "李师傅",
      "collector_phone": "15800000001",
      "estimated_points": 150,
      "actual_points": 180,
      "carbon_saved_kg": 3.6,
      "created_at": "2025-12-06 02:23",
      "completed_at": "2025-12-06 02:23"
    }
  ]
}
```

### `POST /api/mp/orders`

- **功能**：创建预约回收订单
- **请求体**：

```json
{
  "category_id": 1,
  "appointment_date": "2025-12-15",
  "time_slot": "09:00-11:00",
  "estimated_weight": "5kg",
  "address_id": 1,
  "remark": "请准时上门"
}
```

- **响应示例**：

```json
{
  "success": true,
  "order_id": 11,
  "order_no": "2025121112345",
  "message": "预约成功"
}
```

### `GET /api/mp/ranking`

- **功能**：积分/减碳排行榜
- **请求参数**：`type`(points/carbon), `limit`(默认20)
- **响应示例**：

```json
{
  "type": "points",
  "ranking": [
    {
      "rank": 1,
      "user_id": 9,
      "nickname": "环保达人",
      "avatar_url": "https://i.pravatar.cc/100?img=9",
      "score": 18500,
      "recycle_count": 210
    }
  ]
}
```

---

## 13. 未来规划接口（尚未实现）

### 13.1 小程序端扩展

- `GET /api/stations/nearby`：根据经纬度获取附近回收网点
- `GET /api/mall/products`：积分商城商品列表
- `POST /api/mall/exchange`：积分兑换商品
- `GET /api/community/topics`、`/api/community/posts`：社区模块相关接口
