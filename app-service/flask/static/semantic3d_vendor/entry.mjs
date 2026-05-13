/**
 * Single browser bundle: one Three + 3d-force-graph (no CDN, no three/webgpu).
 * Rebuild: cd semantic3d_vendor && npm i && npm run build
 * build.mjs prepends a banner that clears window.THREE so libs don't pick a hijacked global.
 */
import * as THREE from "three";
import ForceGraph3D from "3d-force-graph";

window.THREE = THREE;
window.ForceGraph3D = ForceGraph3D;
