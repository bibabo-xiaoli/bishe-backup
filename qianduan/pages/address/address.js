const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    addresses: [],
    loading: true
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44
    })
  },

  onShow() {
    this.loadAddresses()
  },

  async loadAddresses() {
    try {
      const res = await api.get('/api/mp/addresses')
      this.setData({
        addresses: res.items || [],
        loading: false
      })
    } catch (e) {
      console.error('获取地址失败:', e)
      this.setData({ loading: false })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  addAddress() {
    wx.navigateTo({
      url: './edit/edit'
    })
  },

  editAddress(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `./edit/edit?id=${id}`
    })
  }
})
