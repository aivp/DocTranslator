import request from '@/utils/request'

//术语-广场列表
export function comparison_share(params) {
  return request({
      url: `/comparison/share`,
      method: 'get',
      params: params
  });
}

//提示词-广场列表
export function prompt_share(params) {
  return request({
      url: `/prompt/share`,
      method: 'get',
      params: params
  });
}

//添加到我的术语
export function comparison_copy(id){
  return request({
      url: `/comparison/copy/${id}`,
      method: 'POST'
  });
}

//添加到我的提示词
export function prompt_copy(id){
  return request({
      url: `/prompt/copy/${id}`,
      method: 'POST'
  });
}

//收藏术语
export function comparison_fav(id){
  return request({
      url: `/comparison/fav/${id}`,
      method: 'POST'
  });
}

//收藏提示词
export function prompt_fav(id){
  return request({
      url: `/prompt/fav/${id}`,
      method: 'POST'
  });
}