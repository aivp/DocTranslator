import request from '@/utils/request'

//术语-添加对照数据
export function comparison(params) {
  return request({
      url: `/comparison`,
      method: 'POST',
      data: params
  });
}

//编辑对照数据
export function comparison_edit(id,params){
  return request({
      url: `/comparison/${id}`,
      method: 'POST',
      data:params
  });
}

//删除对照数据
export function comparison_del(id){
  return request({
      url: `/comparison/${id}`,
      method: 'delete'
  });
}


/**
 * 获取术语表
 */
export function comparison_my(){
  return request({
      url: '/comparison/my',
      method: 'get',
  });
}


//更新分享状态
export function comparison_share(id,params){
  return request({
      url: `/comparison/share/${id}`,
      method: 'POST',
      data:params
  });
}

/**
 * 获取提示词
 */
export function prompt_my(){
  return request({
      url: '/prompt/my',
      method: 'get',
  });
}

//添加提示词
export function prompt_add(params) {
  return request({
      url: `/prompt`,
      method: 'POST',
      data: params
  });
}

//编辑提示词
export function prompt_edit(id,params){
  return request({
      url: `/prompt/${id}`,
      method: 'POST',
      data:params
  });
}

//更新提示词分享状态
export function prompt_share(id,params){
  return request({
      url: `/prompt/share/${id}`,
      method: 'POST',
      data:params
  });
}


//删除提示词
export function prompt_del(id){
  return request({
      url: `/prompt/${id}`,
      method: 'delete'
  });
}