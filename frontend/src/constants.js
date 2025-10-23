
// Force HTTPS for API calls when in production
console.log("========================")
console.log("🔥 HOT RELOAD TEST - This message confirms hot-reloading is working!")

const protocol = document.location.protocol;
const hostname = document.location.hostname;

console.log("Hostname:", hostname)

let Url, LegacyUrl, CloudUrl;

if (hostname === 'localhost') {
    console.log("Running in development mode");
    const url = protocol + "//" + hostname;
    Url = url + ':5000';
    LegacyUrl = url + ':5000';
    CloudUrl = url + ":8003/api/v1/tags/tags/group/";
} else {
    console.log("Running in production mode");
    const url = protocol + "//" + hostname;
    Url = url;
    LegacyUrl = url + '/app/legacy/';
    CloudUrl = url + "/api/v1/tags/tags/group/";
}

console.log("Using URLs:", { Url, LegacyUrl, CloudUrl });

export { Url , LegacyUrl, CloudUrl}