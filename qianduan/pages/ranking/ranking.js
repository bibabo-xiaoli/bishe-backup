const app = getApp()

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    currentTab: 'week',
    rankList: [
      {
        rank: 4,
        name: '赵六',
        avatar: 'https://images.unsplash.com/photo-1527980965255-d3b416303d12?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
        score: '1800',
        tag: '减碳达人'
      },
      {
        rank: 5,
        name: '钱七',
        avatar: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
        score: '1650'
      },
      {
        rank: 6,
        name: '孙八',
        avatar: 'https://images.unsplash.com/photo-1633332755192-727a05c4013d?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
        score: '1520'
      },
      {
        rank: 7,
        name: '周九',
        avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
        score: '1400'
      },
      {
        rank: 8,
        name: '吴十',
        avatar: 'https://images.unsplash.com/photo-1531427186611-ecfd6d936c79?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
        score: '1350'
      },
      {
        rank: 9,
        name: '郑十一',
        avatar: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
        score: '1300'
      }
    ]
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44,
      canGoBack: getCurrentPages().length > 1
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

