// index.js
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
