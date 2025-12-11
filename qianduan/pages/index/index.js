// index.js
const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    userInfo: null,
    dashboard: null,
    categories: [],
    loading: true
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44
    })
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  async loadData() {
    try {
      const [userRes, dashboardRes, categoriesRes] = await Promise.all([
        api.getUserInfo(),
        api.getDashboard(),
        api.getCategories()
      ])
      
      this.setData({
        userInfo: userRes,
        dashboard: dashboardRes,
        categories: (categoriesRes.items || []).slice(0, 6),
        loading: false
      })
    } catch (e) {
      console.error('加载首页数据失败:', e)
      this.setData({ loading: false })
    }
  },
  
  navigateTo(e) {
    const url = e.currentTarget.dataset.url
    if (url) wx.navigateTo({ url })
  },

  scanCode() {
    wx.scanCode({
      success(res) {
        console.log(res)
      }
    })
  }
})
