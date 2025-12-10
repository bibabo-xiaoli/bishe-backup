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
  }
})
