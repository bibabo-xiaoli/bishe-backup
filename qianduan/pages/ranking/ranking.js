const app = getApp()
const api = require('../../utils/api')

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    currentTab: 'points',
    topThree: [],
    rankList: [],
    loading: true
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44,
      canGoBack: getCurrentPages().length > 1
    })
    this.loadRanking()
  },

  async loadRanking() {
    try {
      const res = await api.getRanking(this.data.currentTab)
      const ranking = res.ranking || []
      
      // 前三名单独展示
      const topThree = ranking.slice(0, 3)
      const rankList = ranking.slice(3)
      
      this.setData({
        topThree,
        rankList,
        loading: false
      })
    } catch (e) {
      console.error('获取排行榜失败:', e)
      this.setData({ loading: false })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ currentTab: tab })
    this.loadRanking()
  }
})

