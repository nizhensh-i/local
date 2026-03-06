import { isTauriRuntime } from './tauri'

const AUTH_FILE_NAME = 'auth.json'
const AUTH_TEMP_FILE_NAME = 'auth.json.tmp'
const AUTH_STORAGE_KEY = 'local_v_auth_config'
const DEFAULT_PASSWORD = import.meta.env.VITE_LOGIN_PASSWORD || '123456'

function normalizePassword(value) {
  return typeof value === 'string' ? value : ''
}

async function readDesktopConfig() {
  const { exists, readTextFile, remove } = await import('@tauri-apps/plugin-fs')
  const { BaseDirectory } = await import('@tauri-apps/plugin-fs')

  const fileExists = await exists(AUTH_FILE_NAME, { baseDir: BaseDirectory.AppData })
  if (!fileExists) {
    return null
  }

  try {
    const text = await readTextFile(AUTH_FILE_NAME, { baseDir: BaseDirectory.AppData })
    const parsed = JSON.parse(text)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    await remove(AUTH_FILE_NAME, { baseDir: BaseDirectory.AppData })
    return null
  }
}

async function writeDesktopConfig(config) {
  const { exists, remove, rename, writeTextFile } = await import('@tauri-apps/plugin-fs')
  const { BaseDirectory } = await import('@tauri-apps/plugin-fs')
  const payload = JSON.stringify(config, null, 2)
  const tempExists = await exists(AUTH_TEMP_FILE_NAME, { baseDir: BaseDirectory.AppData })
  if (tempExists) {
    await remove(AUTH_TEMP_FILE_NAME, { baseDir: BaseDirectory.AppData })
  }

  await writeTextFile(AUTH_TEMP_FILE_NAME, payload, { baseDir: BaseDirectory.AppData })

  const targetExists = await exists(AUTH_FILE_NAME, { baseDir: BaseDirectory.AppData })
  if (targetExists) {
    await remove(AUTH_FILE_NAME, { baseDir: BaseDirectory.AppData })
  }

  await rename(AUTH_TEMP_FILE_NAME, AUTH_FILE_NAME, { oldPathBaseDir: BaseDirectory.AppData, newPathBaseDir: BaseDirectory.AppData })
}

function readWebConfig() {
  const text = localStorage.getItem(AUTH_STORAGE_KEY)
  if (!text) {
    return null
  }

  try {
    const parsed = JSON.parse(text)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    return null
  }
}

function writeWebConfig(config) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(config))
}

async function readAuthConfig() {
  if (isTauriRuntime()) {
    try {
      return await readDesktopConfig()
    } catch {
      return null
    }
  }

  return readWebConfig()
}

async function writeAuthConfig(config) {
  if (isTauriRuntime()) {
    await writeDesktopConfig(config)
    return
  }

  writeWebConfig(config)
}

export async function getEffectivePassword() {
  const config = await readAuthConfig()
  return normalizePassword(config?.password) || DEFAULT_PASSWORD
}

export async function updatePassword(currentPassword, nextPassword) {
  const effectivePassword = await getEffectivePassword()

  if (normalizePassword(currentPassword) !== effectivePassword) {
    throw new Error('当前密码不正确')
  }

  const normalizedNextPassword = normalizePassword(nextPassword).trim()
  if (!normalizedNextPassword) {
    throw new Error('新密码不能为空')
  }

  await writeAuthConfig({ password: normalizedNextPassword })
}
