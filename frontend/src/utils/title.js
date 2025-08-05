// 从本地存储获取标题配置
function getSiteTitle() {
  try {
    const stored = localStorage.getItem('system-store')
    const config = stored ? JSON.parse(stored) : null
    return config?.site_settings.site_title || 'DocTranslator AI文档翻译'
  } catch {
    return 'DocTranslator AI文档翻译'
  }
}

// 设置页面标题
export function setPageTitle(title) {
  const baseTitle = getSiteTitle()
  document.title = title ? `${baseTitle} | ${title}` : baseTitle
}

/**
 * 设置网站图标
 * @param {string} [customUrl] 直接传入的图标URL
 */
export function setFavicon(customUrl) {
  // 优先级：自定义传入 > 本地存储 > 默认值
  const url = customUrl || getStoredIconUrl() || '/favicon.ico'
  const link = document.querySelector("link[rel='icon']") || createLinkElement()
  link.href = url
}

function getStoredIconUrl() {
  try {
    const settings = JSON.parse(localStorage.getItem('site-settings'))
    return settings?.site_settings.site_logo
  } catch {
    return null
  }
}

function createLinkElement() {
  const link = document.createElement('link')
  link.rel = 'icon'
  document.head.appendChild(link)
  return link
}
