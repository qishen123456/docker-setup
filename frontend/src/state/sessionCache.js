/**
 * 全局会话缓存 — 使用 sessionStorage 持久化关键状态，
 * 确保页面跳转后输入内容、选中数据集/模型等完美还原。
 */
const CACHE_KEY = 'smartask-session-cache-v1'

function read() {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function write(data) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(data))
  } catch {
    // quota exceeded — ignore
  }
}

export function getSessionCache() {
  return read()
}

export function setSessionCache(partial) {
  const current = read()
  write({ ...current, ...partial })
}

export function clearSessionCache() {
  sessionStorage.removeItem(CACHE_KEY)
}
