/**
 * 格式化日期时间（直接使用后端返回的时间，不进行时区转换）
 * 格式：xxxx年xx月xx日 时分秒
 * 
 * 后端返回的时间格式：'YYYY-MM-DD HH:mm:ss'
 * 前端直接格式化显示，不进行时区转换
 */
export function formatTime(dateTimeStr) {
  if (!dateTimeStr || dateTimeStr === '--') return '--'
  try {
    // 直接使用后端返回的时间字符串，不进行时区转换
    let dateStr = String(dateTimeStr).trim()
    
    // 如果格式是 'YYYY-MM-DD HH:mm:ss'，直接解析并格式化
    // 不添加时区信息，直接按原样显示
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})$/)
    if (match) {
      const [, year, month, day, hours, minutes, seconds] = match
      return `${year}年${month}月${day}日 ${hours}:${minutes}:${seconds}`
    }
    
    // 如果不是标准格式，尝试用 Date 解析（兼容其他格式）
    const date = new Date(dateStr)
    if (!isNaN(date.getTime())) {
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      const seconds = String(date.getSeconds()).padStart(2, '0')
      return `${year}年${month}月${day}日 ${hours}:${minutes}:${seconds}`
    }
    
    // 如果都解析失败，直接返回原字符串
    return String(dateTimeStr)
  } catch (e) {
    console.error('时间格式化失败:', e, dateTimeStr)
    return String(dateTimeStr)
  }
}

/**
 * 格式化日期（默认GMT+8，识别浏览器时区，失败则用GMT+8）
 * 格式：xxxx年xx月xx日 时分秒
 * @param {string|number|Date|null|undefined} dateTimeStr - 时间字符串或Date对象
 * @returns {string} 格式化后的时间字符串
 */
export function formatDate(dateTimeStr) {
  // formatDate与formatTime使用相同的逻辑
  return formatTime(dateTimeStr)
}

