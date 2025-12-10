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

## 5. 未来规划接口（尚未实现）

> 以下接口尚未在后端代码中实现，需根据 `ui/数据库表.md` 及各前端页面继续设计。

### 5.1 订单管理相关

- `GET /api/orders`：订单列表，支持按订单号 / 用户 / 手机号 / 类别 / 回收员 / 状态 / 时间范围等筛选；对接 `ui/admin-orders.html`。
- `GET /api/orders/{id}`：订单详情，包括各分类重量、积分、照片、地址等。
- `PUT /api/orders/{id}`：更新订单状态（接单、上门中、已完成、已取消等）。

### 5.2 用户积分与排行榜

- `GET /api/users/top-points`：积分排行榜，用于首页“积分排行榜”模块。
- `GET /api/users/top-carbon`：减碳量排行榜（如需要）。

### 5.3 小程序端业务接口（示例）

- `POST /api/miniprogram/orders`：用户发起预约回收订单。
- `GET /api/stations/nearby`：根据经纬度获取附近回收网点。
- `GET /api/mall/products`：积分商城商品列表。
- `POST /api/mall/exchange`：积分兑换商品。
- `GET /api/community/topics`、`/api/community/posts` 等：社区模块相关接口。

---

如需，我可以在后续步骤中继续为上述“未来规划接口”设计详细字段和示例请求/响应。
