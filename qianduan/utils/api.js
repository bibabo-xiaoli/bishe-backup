/**
 * API 请求封装
 */

const BASE_URL = 'http://127.0.0.1:5000'

/**
 * 通用请求方法
 */
function request(url, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE_URL + url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header
      },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res)
        }
      },
      fail: (err) => {
        console.error('请求失败:', url, err)
        reject(err)
      }
    })
  })
}

/**
 * GET 请求
 */
function get(url, data = {}) {
  return request(url, { method: 'GET', data })
}

/**
 * POST 请求
 */
function post(url, data = {}) {
  return request(url, { method: 'POST', data })
}

// ========== 小程序端 API ==========

// 获取回收品类列表
function getCategories() {
  return get('/api/categories')
}

// 获取回收网点列表
function getStations(params = {}) {
  return get('/api/stations', params)
}

// 获取用户订单列表
function getOrders(params = {}) {
  return get('/api/mp/orders', params)
}

// 创建预约订单
function createOrder(data) {
  return post('/api/mp/orders', data)
}

// 获取用户信息
function getUserInfo() {
  return get('/api/mp/user')
}

// 获取积分排行榜
function getRanking(type = 'week') {
  return get('/api/mp/ranking', { type })
}

// 获取仪表盘数据（首页统计）
function getDashboard() {
  return get('/api/dashboard/summary')
}

module.exports = {
  BASE_URL,
  request,
  get,
  post,
  getCategories,
  getStations,
  getOrders,
  createOrder,
  getUserInfo,
  getRanking,
  getDashboard
}
