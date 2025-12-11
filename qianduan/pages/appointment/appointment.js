const api = require('../../utils/api')

Page({
  data: {
    selectedCategory: 1,
    categories: [],
    weight: 5,
    date: '',
    time: '',
    timeSlots: ['09:00-11:00', '11:00-13:00', '14:00-16:00', '16:00-18:00'],
    timeIndex: 0,
    imageSrc: '',
    loading: true
  },

  onLoad() {
    const today = new Date().toISOString().split('T')[0]
    this.setData({ date: today })
    this.loadCategories()
  },

  async loadCategories() {
    try {
      const res = await api.getCategories()
      const categories = (res.items || []).map(item => ({
        id: item.id,
        name: item.name,
        icon: item.icon,
        points_per_kg: item.points_per_kg
      }))
      this.setData({
        categories,
        selectedCategory: categories.length > 0 ? categories[0].id : 1,
        loading: false
      })
    } catch (e) {
      console.error('获取品类失败:', e)
      this.setData({ loading: false })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  selectCategory(e) {
    const id = e.currentTarget.dataset.id
    this.setData({
      selectedCategory: id
    })
  },

  bindDateChange(e) {
    this.setData({
      date: e.detail.value
    })
  },

  bindTimeChange(e) {
    this.setData({
      time: e.detail.value
    })
  },

  increaseWeight() {
    this.setData({
      weight: this.data.weight + 1
    })
  },

  decreaseWeight() {
    if (this.data.weight > 1) {
      this.setData({
        weight: this.data.weight - 1
      })
    }
  },

  chooseImage() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFiles[0].tempFilePath
        this.setData({
          imageSrc: tempFilePath
        })
      }
    })
  },

  bindTimePickerChange(e) {
    this.setData({
      timeIndex: e.detail.value,
      time: this.data.timeSlots[e.detail.value]
    })
  },

  async submitOrder() {
    const { selectedCategory, date, time, weight } = this.data
    
    if (!time) {
      wx.showToast({ title: '请选择预约时间', icon: 'none' })
      return
    }
    
    wx.showLoading({ title: '提交中...' })

    try {
      const res = await api.createOrder({
        category_id: selectedCategory,
        appointment_date: date,
        time_slot: time,
        estimated_weight: weight + 'kg'
      })
      
      wx.hideLoading()
      wx.showToast({
        title: res.message || '预约成功',
        icon: 'success',
        duration: 2000
      })
      
      setTimeout(() => {
        wx.navigateBack()
      }, 2000)
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '预约失败，请重试', icon: 'none' })
      console.error('创建订单失败:', e)
    }
  }
})
