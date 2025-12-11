const api = require('../../../utils/api')

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    id: null,
    form: {
      name: '',
      phone: '',
      region: ['北京市', '北京市', '朝阳区'],
      address_detail: '',
      tag: '家',
      is_default: false
    }
  },

  onLoad(options) {
    const sysInfo = wx.getSystemInfoSync()
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44
    })
    
    if (options.id) {
      this.setData({ id: options.id })
      this.loadAddress(options.id)
    }
  },

  async loadAddress(id) {
    // 实际项目中应调用详情API，这里为演示简化处理
    const res = await api.get('/api/mp/addresses')
    const addr = res.items.find(item => item.id == id)
    if (addr) {
      this.setData({
        form: {
          name: addr.name,
          phone: addr.phone,
          region: [addr.province, addr.city, addr.district],
          address_detail: addr.address_detail,
          tag: addr.tag,
          is_default: !!addr.is_default
        }
      })
    }
  },

  goBack() {
    wx.navigateBack()
  },

  bindRegionChange(e) {
    this.setData({ 'form.region': e.detail.value })
  },

  inputChange(e) {
    const field = e.currentTarget.dataset.field
    this.setData({ [`form.${field}`]: e.detail.value })
  },

  selectTag(e) {
    this.setData({ 'form.tag': e.currentTarget.dataset.tag })
  },

  switchChange(e) {
    this.setData({ 'form.is_default': e.detail.value })
  },

  async save() {
    try {
      const method = this.data.id ? 'PUT' : 'POST'
      const url = this.data.id ? `/api/mp/addresses/${this.data.id}` : '/api/mp/addresses'
      
      await api.request(url, {
        method,
        data: {
          ...this.data.form,
          province: this.data.form.region[0],
          city: this.data.form.region[1],
          district: this.data.form.region[2]
        }
      })
      
      wx.showToast({ title: '保存成功' })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (e) {
      console.error(e)
      wx.showToast({ title: '保存失败', icon: 'none' })
    }
  },

  async deleteAddress() {
    if (!this.data.id) return
    try {
      await api.request(`/api/mp/addresses/${this.data.id}`, { method: 'DELETE' })
      wx.showToast({ title: '已删除' })
      setTimeout(() => wx.navigateBack(), 1500)
    } catch (e) {
      wx.showToast({ title: '删除失败', icon: 'none' })
    }
  }
})
