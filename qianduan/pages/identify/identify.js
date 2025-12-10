const app = getApp()

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    showResult: false
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

  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => {
        // Simulate recognition
        this.showRecognitionResult()
      }
    })
  },

  takePhoto() {
    // Simulate taking photo and recognition
    wx.showLoading({ title: '识别中...' })
    setTimeout(() => {
      wx.hideLoading()
      this.showRecognitionResult()
    }, 1500)
  },

  toggleFlash() {
    wx.showToast({
      title: '闪光灯已切换',
      icon: 'none'
    })
  },

  showRecognitionResult() {
    this.setData({ showResult: true })
  },

  closeResult() {
    this.setData({ showResult: false })
  },

  confirmRecycle() {
    wx.showToast({
      title: '已加入回收单',
      icon: 'success'
    })
    this.setData({ showResult: false })
  }
})
