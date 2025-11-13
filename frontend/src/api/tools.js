import request from '@/utils/request'

/**
 * 图片上传
 * @param {FormData} formData - 包含file的表单数据
 * @returns {Promise}
 */
export function uploadImage(formData) {
  return request({
    url: '/api/tools/image-upload',
    method: 'POST',
    data: formData
    // FormData会自动设置Content-Type，不需要手动设置
  })
}

/**
 * 批量提交图片翻译任务（后端控制并发和延迟）
 * @param {Object} params - 翻译参数
 * @param {Array<Number>} params.image_ids - 图片记录ID数组（必填）
 * @param {String} params.source_language - 源语言代码（必填）
 * @param {String} params.target_language - 目标语言代码（必填）
 * @returns {Promise}
 */
export function translateImageBatch(params) {
  return request({
    url: '/api/tools/image-translate/batch',
    method: 'POST',
    data: params,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/**
 * 查询图片翻译状态
 * @param {Number} imageId - 图片记录ID
 * @returns {Promise}
 */
export function getImageTranslateStatus(imageId) {
  return request({
    url: `/api/tools/image-translate/status/${imageId}`,
    method: 'GET'
  })
}

/**
 * 获取图片列表
 * @param {Object} params - 查询参数
 * @param {Number} params.page - 页码
 * @param {Number} params.limit - 每页数量
 * @param {String} params.status - 状态筛选（可选）
 * @returns {Promise}
 */
export function getImageList(params) {
  return request({
    url: '/api/tools/images',
    method: 'GET',
    params: params
  })
}

/**
 * 删除图片
 * @param {Number} imageId - 图片ID
 * @returns {Promise}
 */
export function deleteImage(imageId) {
  return request({
    url: `/api/tools/image/${imageId}`,
    method: 'DELETE'
  })
}

/**
 * 批量删除图片
 * @param {Array<Number>} imageIds - 图片ID数组
 * @returns {Promise}
 */
export function batchDeleteImages(imageIds) {
  return request({
    url: '/api/tools/images/batch-delete',
    method: 'POST',
    data: { image_ids: imageIds },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

/**
 * 重试失败的翻译任务
 * @param {Number} imageId - 图片ID
 * @returns {Promise}
 */
export function retryImageTranslate(imageId) {
  return request({
    url: `/api/tools/image-translate/retry/${imageId}`,
    method: 'POST'
  })
}

/**
 * 批量下载翻译后的图片
 * @param {Array<Number>} imageIds - 图片ID数组
 * @returns {Promise}
 */
export function batchDownloadImages(imageIds) {
  return request({
    url: '/api/tools/images/batch-download',
    method: 'POST',
    data: { image_ids: imageIds },
    headers: {
      'Content-Type': 'application/json'
    },
    responseType: 'blob' // 重要：指定响应类型为blob，用于下载文件
  })
}

/**
 * PDF转图片
 * @param {FormData} formData - 包含file、image_format、dpi、page_range的表单数据
 * @returns {Promise}
 */
export function pdfToImage(formData) {
  return request({
    url: '/api/tools/pdf-to-image',
    method: 'POST',
    data: formData
    // FormData会自动设置Content-Type，不需要手动设置
  })
}

/**
 * 图片合并为PDF
 * @param {FormData} formData - 包含files和data的表单数据
 * @returns {Promise}
 */
export function imagesToPdf(formData) {
  return request({
    url: '/api/tools/images-to-pdf',
    method: 'POST',
    data: formData
    // FormData会自动设置Content-Type，不需要手动设置
  })
}

