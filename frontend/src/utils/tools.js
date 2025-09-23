export function formatTime(isoTimeString) {
  if (!isoTimeString) return '';
  
  try {
    // 创建一个Date对象
    const date = new Date(isoTimeString);
    
    // 直接使用本地时间，不进行额外的时区转换
    // 因为后端返回的ISO时间字符串已经包含了时区信息
    
    // 获取年、月、日、小时、分钟和秒
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');

    // 返回格式化后的时间字符串
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (error) {
    console.error('时间格式化错误:', error);
    return isoTimeString;
  }
}
// 格式化日期
/**
 * 将ISO时间字符串转换为YYYY-MM-DD HH:MM:SS格式
 * @param {string} isoString - ISO格式的时间字符串
 * @returns {string} 格式化后的时间字符串 (YYYY-MM-DD HH:MM:SS)
 */
export function formatDate(isoString) {
  if (!isoString) return '';
  
  try {
    // 1. 创建Date对象
    const date = new Date(isoString);

    // 2. 验证输入是否为有效日期
    if (isNaN(date.getTime())) {
      throw new Error('Invalid ISO date string');
    }

    // 3. 直接使用本地时间，不进行额外的时区转换
    // 因为后端返回的ISO时间字符串已经包含了时区信息

    // 4. 获取各个时间部分
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    // 5. 拼接成目标格式
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (error) {
    console.error('日期格式化错误:', error);
    return isoString;
  }
}

