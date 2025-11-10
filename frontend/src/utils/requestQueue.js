/**
 * 请求队列工具 - 限制并发数量，避免触发API速率限制
 */

/**
 * 限制并发执行异步任务
 * @param {Array} tasks - 任务数组，每个任务是一个返回Promise的函数
 * @param {Number} concurrency - 最大并发数，默认2
 * @param {Number} delay - 每个请求之间的延迟（毫秒），默认200ms
 * @returns {Promise<Array>} 返回所有任务的结果数组
 */
export async function limitConcurrency(tasks, concurrency = 2, delay = 200) {
  if (!tasks || tasks.length === 0) {
    return []
  }

  const results = []
  const executing = []

  for (let i = 0; i < tasks.length; i++) {
    // 如果当前并发数已达到限制，等待一个任务完成
    if (executing.length >= concurrency) {
      await Promise.race(executing)
      // 移除已完成的任务
      executing.splice(0, executing.length, ...executing.filter(p => {
        return p && !p._completed
      }))
    }

    // 添加延迟（除了第一个请求）
    if (i > 0 && delay > 0) {
      await new Promise(resolve => setTimeout(resolve, delay))
    }

    // 创建任务Promise
    const taskPromise = (async () => {
      try {
        const result = await tasks[i]()
        results[i] = { success: true, data: result }
      } catch (error) {
        results[i] = { success: false, error: error }
      } finally {
        taskPromise._completed = true
      }
    })()

    executing.push(taskPromise)
  }

  // 等待所有任务完成
  await Promise.all(executing)

  return results
}

/**
 * 串行执行任务（一个接一个）
 * @param {Array} tasks - 任务数组
 * @param {Number} delay - 每个请求之间的延迟（毫秒），默认300ms
 * @returns {Promise<Array>} 返回所有任务的结果数组
 */
export async function serialExecute(tasks, delay = 300) {
  if (!tasks || tasks.length === 0) {
    return []
  }

  const results = []
  for (let i = 0; i < tasks.length; i++) {
    try {
      const result = await tasks[i]()
      results.push({ success: true, data: result })
      
      // 添加延迟（除了最后一个请求）
      if (i < tasks.length - 1 && delay > 0) {
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    } catch (error) {
      results.push({ success: false, error: error })
    }
  }

  return results
}
