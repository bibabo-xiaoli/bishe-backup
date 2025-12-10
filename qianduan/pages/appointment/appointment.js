Page({
  data: {
    selectedCategory: 'box',
    weight: 5,
    date: '',
    time: '',
    imageSrc: ''
  },

  onLoad() {
    const today = new Date().toISOString().split('T')[0]
    this.setData({
      date: today
    })
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

  submitOrder() {
    if (!this.data.time) {
      wx.showToast({
        title: '请选择预约时间',
        icon: 'none'
      })
      return
    }
    
    wx.showLoading({
      title: '提交中...',
    })

    setTimeout(() => {
      wx.hideLoading()
      wx.showToast({
        title: '预约成功',
        icon: 'success',
        duration: 2000,
        success: () => {
          setTimeout(() => {
            wx.navigateBack()
          }, 2000)
        }
      })
    }, 1500)
  }
})
