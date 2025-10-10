import request from '@/utils/request'

export const videoApi = {
  // 上传视频
  uploadVideo: (formData) => {
    return request({
      url: '/video/upload',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 启动翻译
  startTranslate: (data) => {
    return request({
      url: '/video/translate',
      method: 'post',
      data
    })
  },

  // 查询翻译状态
  getVideoStatus: (videoId) => {
    return request({
      url: `/video/status/${videoId}`,
      method: 'get'
    })
  },

  // 获取视频列表
  getVideoList: (params) => {
    return request({
      url: '/video/list',
      method: 'get',
      params
    })
  },

  // 删除视频
  deleteVideo: (videoId) => {
    return request({
      url: `/video/${videoId}`,
      method: 'delete'
    })
  },

  // 下载视频
  downloadVideo: (videoId) => {
    return request({
      url: `/video/${videoId}/download`,
      method: 'get',
      responseType: 'blob'
    })
  },

  // 获取支持的语言列表
  getLanguages: () => {
    return request({
      url: '/video/languages',
      method: 'get'
    })
  }
}
