import { isTauriRuntime } from './tauri'

let convertFileSrcRef = null

async function getConvertFileSrc() {
  if (convertFileSrcRef) {
    return convertFileSrcRef
  }

  const core = await import('@tauri-apps/api/core')
  convertFileSrcRef = core.convertFileSrc
  return convertFileSrcRef
}

export async function resolvePlaybackSource(video, fallbackUrl = '') {
  if (!video?.path || !isTauriRuntime()) {
    return fallbackUrl
  }

  try {
    const convertFileSrc = await getConvertFileSrc()
    return convertFileSrc(video.path)
  } catch (_) {
    return fallbackUrl
  }
}
