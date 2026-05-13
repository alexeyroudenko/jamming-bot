import * as esbuild from "esbuild";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outfile = join(__dirname, "..", "semantic3d_force_graph.iife.js");

/* three-forcegraph uses `window.THREE ? window.THREE : bundled`; MetaMask/SES often pre-injects a fake THREE — clear before bundle body. */
await esbuild.build({
    entryPoints: [join(__dirname, "entry.mjs")],
    outfile,
    bundle: true,
    minify: true,
    format: "iife",
    platform: "browser",
    target: ["es2020"],
    logLevel: "info",
    banner: {
        js: "try{delete window.THREE}catch(e){}try{window.THREE=void 0}catch(e){}",
    },
});
