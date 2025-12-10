const app = getApp()

const categories = {
  recyclable: {
    name: '可回收物',
    enName: 'Recyclable Waste',
    color: 'blue',
    icon: '/image/recycle.png',
    requirements: [
      '轻投轻放',
      '清洁干燥，避免污染',
      '废纸尽量平整',
      '立体包装物请清空内容物，清洁后压扁投放',
      '有尖锐边角的，应包裹后投放'
    ],
    items: [
      { name: '废纸张', icon: '/image/newspaper.png' }, // Need to ensure these icons exist or reuse available ones
      { name: '废塑料', icon: '/image/package.png' },
      { name: '废玻璃制品', icon: '/image/beer-bottle.png' },
      { name: '废金属', icon: '/image/wrench.png' },
      { name: '废织物', icon: '/image/t-shirt.png' }
    ]
  },
  hazardous: {
    name: '有害垃圾',
    enName: 'Hazardous Waste',
    color: 'red',
    icon: '/image/warning-octagon.png',
    requirements: [
      '投放时请注意轻放',
      '易破损的请连带包装或包裹后投放',
      '如易挥发，请密封后投放'
    ],
    items: [
      { name: '废电池', icon: '/image/battery-warning.png' },
      { name: '废灯管', icon: '/image/lightbulb.png' },
      { name: '废药品', icon: '/image/pill.png' },
      { name: '废油漆', icon: '/image/paint-bucket.png' }
    ]
  },
  kitchen: {
    name: '厨余垃圾',
    enName: 'Food Waste',
    color: 'green',
    icon: '/image/fish.png',
    requirements: [
      '厨余垃圾应沥干水分后再投放',
      '有包装物的应将包装物去除后分类投放',
      '包装物应投放到对应的可回收物或其他垃圾容器中'
    ],
    items: [
      { name: '蔬菜瓜果', icon: '/image/carrot.png' },
      { name: '骨骼内脏', icon: '/image/bone.png' },
      { name: '剩菜剩饭', icon: '/image/bowl-food.png' }
    ]
  },
  other: {
    name: '其他垃圾',
    enName: 'Residual Waste',
    color: 'gray',
    icon: '/image/trash.png',
    requirements: [
      '尽量沥干水分',
      '难以辨识类别的生活垃圾投入其他垃圾容器内'
    ],
    items: [
      { name: '卫生纸巾', icon: '/image/toilet-paper.png' },
      { name: '碎陶瓷', icon: '/image/egg-crack.png' },
      { name: '烟蒂', icon: '/image/cigarette.png' }
    ]
  }
}

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    type: 'recyclable',
    info: categories.recyclable
  },

  onLoad(options) {
    const sysInfo = wx.getSystemInfoSync()
    const type = options.type || 'recyclable'
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: 44,
      type,
      info: categories[type]
    })
  },

  goBack() {
    wx.navigateBack()
  }
})
