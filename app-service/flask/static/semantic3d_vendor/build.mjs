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

/* 3d-force-graph init вызывает this._animationCycle() синхронно до debounced update (1 ms) → state.layout undefined.
   Второе вхождение this._animationCycle() — kick-off в конце init. Заменяем на setTimeout(20) > debounce. */
import { readFileSync, writeFileSync } from "node:fs";
let code = readFileSync(outfile, "utf8");
const needle = "this._animationCycle()";
const hits = code.split(needle).length - 1;
if (hits !== 2) {
    throw new Error(`postbuild: expected exactly 2 "${needle}", found ${hits}`);
}
const last = code.lastIndexOf(needle);
const patched =
    code.slice(0, last) +
    "setTimeout(this._animationCycle.bind(this),20)" +
    code.slice(last + needle.length);
writeFileSync(outfile, patched, "utf8");
