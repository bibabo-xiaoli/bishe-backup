const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    stations: [],
    loading: true
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44
    })
    this.loadStations()
  },

  async loadStations() {
    try {
      const res = await api.getStations()
      const stations = (res.items || []).map(item => ({
        id: item.id,
        name: item.name,
        type: item.type,
        address: item.full_address,
        opening_hours: item.opening_hours,
        status: item.status_id,
        status_name: item.status_name,
        latitude: item.latitude,
        longitude: item.longitude
      }))
      this.setData({ stations, loading: false })
    } catch (e) {
      console.error('获取网点失败:', e)
      this.setData({ loading: false })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  openLocation(e) {
    const { lat, lng, name, address } = e.currentTarget.dataset
    if (lat && lng) {
      wx.openLocation({
        latitude: parseFloat(lat),
        longitude: parseFloat(lng),
        name: name,
        address: address
      })
    }
  }
})
