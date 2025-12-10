const app = getApp()

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44
    })
  },

  goBack() {
    wx.navigateBack()
  },

  navigateToDetail(e) {
    const type = e.currentTarget.dataset.type
    wx.navigateTo({
      url: `/pages/guide/detail/detail?type=${type}`
    })
  }
})
