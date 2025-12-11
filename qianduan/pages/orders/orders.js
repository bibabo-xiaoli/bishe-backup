const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    currentTab: 'pending',
    orders: {
      pending: [],
      processing: [],
      completed: [],
      aftersale: []
    },
    loading: true
  },

  onLoad(options) {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44,
      currentTab: options.type || 'pending'
    })
    this.loadOrders()
  },

  onShow() {
    this.loadOrders()
  },

  async loadOrders() {
    try {
      const res = await api.getOrders()
      const allOrders = res.orders || []
      
      // 按状态分组
      const orders = {
        pending: allOrders.filter(o => o.status === 1),
        processing: allOrders.filter(o => o.status === 2),
        completed: allOrders.filter(o => o.status === 3),
        aftersale: allOrders.filter(o => o.status === 4 || o.status === 5)
      }
      
      this.setData({ orders, loading: false })
    } catch (e) {
      console.error('获取订单失败:', e)
      this.setData({ loading: false })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ currentTab: tab })
  },

  cancelOrder(e) {
    const orderId = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认取消',
      content: '确定要取消这个订单吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.post(`/api/mp/orders/${orderId}/cancel`)
            wx.showToast({ title: '已取消' })
            this.loadOrders()
          } catch (e) {
            wx.showToast({ title: '取消失败', icon: 'none' })
          }
        }
      }
    })
  },

  contactCollector(e) {
    const phone = e.currentTarget.dataset.phone
    if (phone) {
      wx.makePhoneCall({ phoneNumber: phone })
    }
  },

  contactService() {
    wx.navigateTo({ url: '/pages/service/service' })
  },

  reorder(e) {
    wx.navigateTo({ url: '/pages/appointment/appointment' })
  }
})
