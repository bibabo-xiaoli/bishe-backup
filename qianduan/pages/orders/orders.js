const app = getApp()

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    currentTab: 'pending',
    orders: {
      pending: [
        {
          id: '20231024001',
          icon: '/image/package.png',
          title: '纸板箱, 旧衣物',
          weight: '5-10kg',
          time: '明天 09:00-11:00'
        },
        {
          id: '20231025008',
          icon: '/image/monitor.png',
          title: '废旧家电 (微波炉)',
          weight: '<5kg',
          time: '后天 14:00-16:00'
        }
      ],
      processing: [
        {
          id: '20231024099',
          icon: '/image/book.png',
          title: '旧书籍, 报刊',
          collector: '李师傅 139****8888',
          eta: '15分钟后'
        }
      ],
      completed: [
        {
          time: '2023-10-20 15:30',
          icon: '/image/beer-bottle.png',
          title: '塑料瓶, 易拉罐',
          realWeight: '3.5kg',
          points: 85
        },
        {
          time: '2023-10-15 10:00',
          icon: '/image/t-shirt.png',
          title: '旧衣物',
          realWeight: '12.0kg',
          points: 240
        }
      ],
      aftersale: [
        {
          id: '20231010055',
          icon: '/image/package.png',
          title: '混合回收物',
          issue: '积分计算有误',
          status: '客服正在核实中...'
        }
      ]
    }
  },

  onLoad(options) {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44,
      currentTab: options.type || 'pending'
    })
  },

  goBack() {
    wx.navigateBack()
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({
      currentTab: tab
    })
  }
})
