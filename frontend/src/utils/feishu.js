import { feishuInAppAuth, setAuthToken } from '../api/index.js'

const FEISHU_INIT_KEY = 'smartask_feishu_init_done'

export const isInFeishu = () => {
  const ua = navigator.userAgent || ''
  return /Lark|Feishu|LarkLocale|FeishuLocale/i.test(ua) || Boolean(window.tt?.getAuthCode)
}

const getFeishuBridge = () => window.tt || window.h5sdk || null

export async function initFeishuEnv() {
  if (!isInFeishu()) return null
  if (sessionStorage.getItem(FEISHU_INIT_KEY) === '1') return null

  const bridge = getFeishuBridge()
  if (!bridge?.getAuthCode) return null

  try {
    sessionStorage.setItem(FEISHU_INIT_KEY, '1')
    const result = await bridge.getAuthCode()
    const code = result?.code || result?.authCode || ''
    if (!code) return null
    const authData = await feishuInAppAuth(code)
    if (authData?.success && authData?.token) {
      setAuthToken(authData.token)
      localStorage.setItem('auth_user', JSON.stringify(authData.user || {}))
      return authData.user || null
    }
  } catch (error) {
    sessionStorage.removeItem(FEISHU_INIT_KEY)
    console.warn('Feishu auto login failed', error)
  }
  return null
}

