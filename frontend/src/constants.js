
// const url = document.location.protocol + "//" + document.location.hostname
// const Url = url + ':5000'
// const LegacyUrl = url + ':5000'
// const CloudUrl = url + ":8003/api/v1/tags/tags/group/"

const Url = 'https://jamming-bot.arthew0.online'
const LegacyUrl = 'https://jamming-bot.arthew0.online/app/legacy/'
// Ingress path /tags/api + strip /tags → tags-service sees /api/v1/tags/...
const CloudUrl = `${Url}/tags/api/v1/tags/tags/group/`

/** Origin for tag HTML UI (iframes under /tags/...), not tags-service REST. */
function getTagsUiOrigin() {
  const env = process.env.REACT_APP_TAGS_UI_BASE
  if (env && String(env).trim()) {
    return String(env).replace(/\/+$/, '')
  }
  // ENVIRONMENT_DATA=prod форсит прод-домен даже из dev-фронта (localhost:3000):
  // iframe пойдёт на https://jamming-bot.arthew0.online/tags/..., внутренние fetch
  // вроде /api/tags/get/ автоматически уйдут туда же.
  const envData = String(process.env.REACT_APP_ENVIRONMENT_DATA || '').trim().toLowerCase()
  if (envData === 'prod') {
    return Url.replace(/\/+$/, '')
  }
  if (typeof window !== 'undefined') {
    const { hostname, port, protocol } = window.location
    if (hostname === 'localhost' && port === '3000') {
      return `${protocol}//${hostname}:5000`
    }
  }
  return Url.replace(/\/+$/, '')
}

/** Full URL for a tag UI path, e.g. `/tags/3d/`. */
function tagsEmbedUrl(path) {
  const origin = getTagsUiOrigin()
  let p = String(path).trim()
  if (!p.startsWith('/')) p = `/${p}`
  if (!p.endsWith('/')) p = `${p}/`
  return `${origin}${p}`
}

export { Url , LegacyUrl, CloudUrl, getTagsUiOrigin, tagsEmbedUrl }