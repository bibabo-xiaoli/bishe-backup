const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    userInfo: null,
    loading: true
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44
    })
    this.loadUserInfo()
  },

  onShow() {
    this.loadUserInfo()
  },

  async loadUserInfo() {
    try {
      const userInfo = await api.getUserInfo()
      this.setData({
        userInfo,
        loading: false
      })
    } catch (e) {
      console.error('获取用户信息失败:', e)
      this.setData({ loading: false })
    }
  },

  navigateTo(e) {
    const url = e.currentTarget.dataset.url
    if (url) wx.navigateTo({ url })
  }
})
