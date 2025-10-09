import request from '@/utils/request'

// 修改密码
export function changePassword(data) {
    return request({
        url: '/change',
        method: 'POST',
        data
    });
}

/**
 * 获取存储空间
 */
export function storage() {
    return request({
        url: '/storage',
        method: 'GET'
    });
}

/**
 * 登录用户基本信息
 */
export function authInfo() {
    return request({
        url: '/user-info',
        method: 'GET',
    });
}


