import request from '@/utils/request'
/**
 * 获取环境配置信息
 */
// 版本信息
export function getVersionSetting() {
  return request({
    url: '/common/version',
    method: 'GET',
  });
}
// 获取系统设置
export function getSystemSetting() {
  return request({
    url: '/common/all_settings',
    method: 'GET',
  });
}
/**
 * 获取翻译设置
 */
export function getTranslateSetting() {
  return request({
    url: '/translate/setting',
    method: 'get',
  });
}