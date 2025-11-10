/**
 * 格式化日期时间（默认GMT+8，识别浏览器时区，失败则用GMT+8）
 * 格式：xxxx年xx月xx日 时分秒
 */
export function formatTime(dateTimeStr) {
  if (!dateTimeStr) return '-'
  try {
    // 解析时间字符串
    const date = new Date(dateTimeStr)
    
    if (isNaN(date.getTime())) {
      return String(dateTimeStr)
    }
    
    // 获取浏览器时区偏移（分钟），默认GMT+8（480分钟 = 8小时）
    let timezoneOffsetMinutes = 480
    
    try {
      // 尝试获取浏览器时区偏移
      // getTimezoneOffset返回UTC时间与本地时间的差值（分钟）
      // 例如：GMT+8时区返回-480，GMT-5时区返回300
      // 我们需要的是：GMT+8需要+480分钟，所以取反
      const browserOffset = -new Date().getTimezoneOffset()
      if (!isNaN(browserOffset)) {
        timezoneOffsetMinutes = browserOffset
      }
    } catch (e) {
      // 获取失败，使用默认GMT+8
      console.warn('无法获取浏览器时区，使用默认GMT+8')
    }
    
    // 将UTC时间转换为目标时区
    // 1. 获取UTC时间戳（毫秒）
    const utcTimestamp = date.getTime()
    // 2. 计算UTC时间的本地表示（去除Date对象自动应用的本地时区）
    // getTimezoneOffset返回的是本地时区与UTC的差值，单位是分钟
    const localTimezoneOffset = date.getTimezoneOffset() * 60000 // 转为毫秒
    // 3. 获取纯UTC时间戳
    const pureUtcTimestamp = utcTimestamp - localTimezoneOffset
    // 4. 加上目标时区的偏移，得到目标时区的时间
    const targetTimestamp = pureUtcTimestamp + (timezoneOffsetMinutes * 60000)
    const targetTime = new Date(targetTimestamp)
    
    // 使用UTC方法读取，因为我们已经手动转换了时区
    const year = targetTime.getUTCFullYear()
    const month = String(targetTime.getUTCMonth() + 1).padStart(2, '0')
    const day = String(targetTime.getUTCDate()).padStart(2, '0')
    const hours = String(targetTime.getUTCHours()).padStart(2, '0')
    const minutes = String(targetTime.getUTCMinutes()).padStart(2, '0')
    const seconds = String(targetTime.getUTCSeconds()).padStart(2, '0')
    return `${year}年${month}月${day}日 ${hours}:${minutes}:${seconds}`
  } catch (e) {
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

