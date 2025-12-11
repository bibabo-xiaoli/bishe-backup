Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    faqs: [
      { q: '回收积分如何计算？', a: '不同品类积分规则不同，可在"回收品类"页面查看具体单价。' },
      { q: '预约后多久上门？', a: '回收员将在您预约的时间段内上门，出发前会电话联系。' },
      { q: '支持哪些区域回收？', a: '目前已覆盖北京市朝阳区、海淀区等核心区域。' }
    ]
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

  callPhone() {
    wx.makePhoneCall({
      phoneNumber: '400-123-4567'
    })
  }
})
