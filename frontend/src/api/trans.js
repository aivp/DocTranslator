import request from '@/utils/request'

// 检查是否可用
export function checkOpenAI(params) {
    return request({
        url: `/check/openai`,
        method: 'POST',
        data: params
    });
}

// 检查是否可用
export function checkDocx(params) {
    return request({
        url: `/check/doc2x`,
        method: 'POST',
        data: params
    });
}

// 检查pdf是否是扫描件
export function checkPdf(file_path) {
    return request({
        url: `/check/pdf`,
        method: 'POST',
        data: { file_path }
    });
}

export function delFile(data) {
    return request({
        url: `/delFile`,
        method: 'POST',
        data: data
    });
}


export function transalteFile(params) {
    return request({
        url: `/translate`,
        method: 'POST',
        data: params
    });
}
// 进度查询
export function transalteProcess(params) {
    return request({
        url: `/process`,
        method: 'POST',
        data: params
    });
}

// 专门的进度查询API（只返回进度信息，不返回完整任务信息）
export function getTranslateProgress(params) {
    return request({
        url: `/translate/progress`,
        method: 'POST',
        data: params
    });
}

/**
 * 翻译
 */
export function translates(params) {
    return request({
        url: `/translates`,
        method: 'get',
        params
    });
}



export function delTranslate(id) {
    return request({
        url: `/translate/${id}`,
        method: 'delete'
    });
}

/**
 * 删除所有翻译文件记录
 */
export function delAllTranslate() {
    return request({
        url: '/translate/all',
        method: 'delete'
    });
}

/**
 * 下载所有翻译文件记录
 */
export function downAllTranslate() {
    return request({
        url: '/translate/download/all',
        method: 'get'
    });
}


/**
 * 获取文件统计
 */
export function getFinishCount() {
    return request({
        url: '/translate/finish/count',
        method: 'get'
    });
}

// doc2x 启动pdf翻译
export function doc2xStartService(data) {
    return request({
        url: '/doc2x/start',
        method: 'post',
        data
    });
}

// doc2x查询任务状态
export function doc2xQueryStatusService(data) {
    return request({
        url: '/doc2x/status',
        method: 'post',
        data: data
    });
}

