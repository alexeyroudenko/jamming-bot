
// const url = document.location.protocol + "//" + document.location.hostname
// const Url = url + ':5000'
// const LegacyUrl = url + ':5000'
// const CloudUrl = url + ":8003/api/v1/tags/tags/group/"

const Url = 'https://jamming-bot.arthew0.online'
const LegacyUrl = 'https://jamming-bot.arthew0.online/app/legacy/'
// Ingress path /tags/api + strip /tags → tags-service sees /api/v1/tags/...
const CloudUrl = `${Url}/tags/api/v1/tags/tags/group/`

export { Url , LegacyUrl, CloudUrl}