/* global ForceGraph3D, io, THREE */
/* Jamming Bot semantic demo: same data path as semantic_demo.js, 3D force graph (WebGL). */

var SEMANTIC_FORCE_LS = "jammingSemantic3dForceParams";
var SEMANTIC_FORCE_PANEL_COLLAPSED_LS = "jammingSemantic3dForcePanelCollapsed";

function loadForcePanelCollapsedDefaultTrue() {
    try {
        var v = localStorage.getItem(SEMANTIC_FORCE_PANEL_COLLAPSED_LS);
        if (v === null || v === undefined) {
            return true;
        }
        return v === "1" || v === "true";
    } catch (e) {
        return true;
    }
}

function saveForcePanelCollapsed(collapsed) {
    try {
        localStorage.setItem(SEMANTIC_FORCE_PANEL_COLLAPSED_LS, collapsed ? "1" : "0");
    } catch (e) {
        /* ignore quota */
    }
}

function applyForcePanelCollapsedUi(panel, toggle, body, collapsed) {
    if (!panel || !toggle || !body) {
        return;
    }
    if (collapsed) {
        panel.classList.add("is-collapsed");
        body.setAttribute("hidden", "");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("title", "Показать параметры силы");
    } else {
        panel.classList.remove("is-collapsed");
        body.removeAttribute("hidden");
        toggle.setAttribute("aria-expanded", "true");
        toggle.setAttribute("title", "Скрыть параметры силы");
    }
}

function wireForcePanelCollapse() {
    var panel = document.getElementById("semantic-force-panel");
    var toggle = document.getElementById("semantic-force-toggle");
    var body = document.getElementById("semantic-force-body");
    if (!panel || !toggle || !body) {
        return;
    }
    applyForcePanelCollapsedUi(panel, toggle, body, loadForcePanelCollapsedDefaultTrue());
    toggle.addEventListener("click", function () {
        var collapsed = panel.classList.contains("is-collapsed");
        applyForcePanelCollapsedUi(panel, toggle, body, !collapsed);
        saveForcePanelCollapsed(!collapsed);
    });
}

function isTypingTargetForHotkey(el) {
    if (!el || !el.tagName) {
        return false;
    }
    var tag = el.tagName.toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") {
        return true;
    }
    return el.isContentEditable === true;
}

function wireForcePanelHotkey() {
    document.addEventListener("keydown", function (ev) {
        if (!ev || ev.defaultPrevented) {
            return;
        }
        if (ev.ctrlKey || ev.metaKey || ev.altKey) {
            return;
        }
        if (ev.key !== "s" && ev.key !== "S") {
            return;
        }
        if (isTypingTargetForHotkey(ev.target)) {
            return;
        }
        ev.preventDefault();
        var panel = document.getElementById("semantic-force-panel");
        var toggle = document.getElementById("semantic-force-toggle");
        var body = document.getElementById("semantic-force-body");
        if (!panel || !toggle || !body) {
            return;
        }
        var collapsed = panel.classList.contains("is-collapsed");
        applyForcePanelCollapsedUi(panel, toggle, body, !collapsed);
        saveForcePanelCollapsed(!collapsed);
    });
}

var DEFAULT_FORCE_VALUES = {
    v1: 0.25,
    v2: 0.25,
    v3: 0.25,
    v4: 0.25,
    v5: 0.25,
    theta: 0.8,
    chargeDist: 10000
};

function mergeForceDefaults(over) {
    var o = {};
    var k;
    for (k in DEFAULT_FORCE_VALUES) {
        if (Object.prototype.hasOwnProperty.call(DEFAULT_FORCE_VALUES, k)) {
            o[k] = DEFAULT_FORCE_VALUES[k];
        }
    }
    if (!over || typeof over !== "object") {
        return o;
    }
    for (k in over) {
        if (Object.prototype.hasOwnProperty.call(DEFAULT_FORCE_VALUES, k)) {
            var n = Number(over[k]);
            if (!isNaN(n) && isFinite(n)) {
                o[k] = n;
            }
        }
    }
    return o;
}

function loadForceParamsFromStorage() {
    try {
        var raw = localStorage.getItem(SEMANTIC_FORCE_LS);
        if (!raw) return mergeForceDefaults(null);
        var parsed = JSON.parse(raw);
        return mergeForceDefaults(parsed);
    } catch (e) {
        return mergeForceDefaults(null);
    }
}

function saveForceParamsToStorage() {
    try {
        localStorage.setItem(SEMANTIC_FORCE_LS, JSON.stringify(values));
    } catch (e) {
        /* ignore quota */
    }
}

var values = loadForceParamsFromStorage();

function getLinkDistanceMultiplier() {
    if (window.devicePixelRatio >= 2) {
        return 0.5;
    }
    return 1.0;
}

var graph;

function linkEndpoint(x) {
    if (x && typeof x === "object" && Object.prototype.hasOwnProperty.call(x, "id")) {
        return String(x.id);
    }
    return String(x);
}

/**
 * @param {HTMLElement} containerEl
 * @returns {{ getNodes: Function, addNode: Function, removeNode: Function, addLink: Function, removeallLinks: Function, removeAllNodes: Function, findNode: Function, removeLinksForNode: Function, findNodeIndex: Function, setValues: Function } | null}
 */
function createSemanticGraph3D(containerEl) {
    if (typeof ForceGraph3D !== "function") {
        return null;
    }
    /* Радиус сферы = cbrt(nodeVal) * nodeRelSize; дефолт библиотеки ≈ 4 — здесь 4/3 ≈ в 3 раза меньше радиус */
    var NODE_REL_SIZE = 4 / 3;
    function makeNodeLabelSprite(text) {
        if (typeof THREE === "undefined") {
            return null;
        }
        var label = String(text);
        if (label.length > 36) {
            label = label.slice(0, 35) + "\u2026";
        }
        var canvas = document.createElement("canvas");
        var ctx = canvas.getContext("2d");
        var dpr = Math.min(2, window.devicePixelRatio || 1);
        var fontPx = Math.round(34 * 0.7 * dpr);
        ctx.font =
            '400 ' +
            fontPx +
            'px ui-monospace, "SF Mono", Menlo, Consolas, monospace';
        var w = Math.ceil(ctx.measureText(label).width) + 18 * dpr;
        var h = Math.ceil(fontPx + 14 * dpr);
        canvas.width = w;
        canvas.height = h;
        ctx.font =
            '400 ' +
            fontPx +
            'px ui-monospace, "SF Mono", Menlo, Consolas, monospace';
        ctx.textBaseline = "top";
        var tx = 8 * dpr;
        var ty = 6 * dpr;
        ctx.lineJoin = "round";
        ctx.lineWidth = Math.max(3, 4 * dpr);
        ctx.strokeStyle = "rgba(0, 0, 0, 0.82)";
        ctx.strokeText(label, tx, ty);
        ctx.fillStyle = "#f0f0f0";
        ctx.fillText(label, tx, ty);
        var tex = new THREE.CanvasTexture(canvas);
        tex.needsUpdate = true;
        if (THREE.SRGBColorSpace) {
            tex.colorSpace = THREE.SRGBColorSpace;
        }
        var mat = new THREE.SpriteMaterial({
            map: tex,
            transparent: true,
            depthWrite: false,
            /* Иначе при отдалённой камере (мы умножаем z на 2) подписи превращаются в пиксельные точки */
            sizeAttenuation: false,
            depthTest: true
        });
        var sprite = new THREE.Sprite(mat);
        sprite.renderOrder = 999;
        /* sizeAttenuation: false — k = canvas_px / world_scale; больше k → мельче подпись */
        var k = 1800 / 0.7;
        sprite.scale.set(w / k, h / k, 1);
        return sprite;
    }

    var graphData = { nodes: [], links: [] };
    var fg = ForceGraph3D()(containerEl)
        .graphData(graphData)
        .nodeId("id")
        .nodeLabel("id")
        .nodeVal(function (d) {
            return (d.r || 6) * 2.2;
        })
        .nodeOpacity(1)
        .nodeColor(function () {
            return "#ffffff";
        })
        .nodeThreeObjectExtend(true)
        .nodeRelSize(NODE_REL_SIZE)
        .nodeThreeObject(function (node) {
            var spr = makeNodeLabelSprite(node.id);
            if (!spr) {
                return null;
            }
            /* Как в three-forcegraph: radius = cbrt(nodeVal) * nodeRelSize */
            var nodeVal = (node.r || 6) * 2.2;
            var sphereR = Math.cbrt(nodeVal) * NODE_REL_SIZE;
            var margin = 1.2;
            spr.position.set(sphereR + margin, sphereR * 0.55, 1.2);
            return spr;
        })
        .linkWidth(function (d) {
            var v = d.value != null ? Number(d.value) : 15;
            if (isNaN(v)) v = 15;
            /* ×8 и min 1.1 — в 2 раза толще прежних ×4 / 0.55 (ведро геометрии по-прежнему с шагом 0.1) */
            return Math.max(1.1, (v / 55) * 8);
        })
        .linkColor(function () {
            return "#666666";
        })
        .linkOpacity(0.52)
        .linkDirectionalParticles(0)
        .backgroundColor("#000000")
        .showNavInfo(false);

    /* Вместо FOCUS: каждые 21 с — случайно ±45° по Y сцене или «орбита» камеры вокруг Y (тот же период, что был у random focus) */
    var RANDOM_MOTION_INTERVAL_MS = 21000;
    var ORBIT_ANGLE_RAD = Math.PI / 3;
    /* Орбита камеры: в 2× быстрее прежних 2800 ms */
    var ORBIT_DURATION_MS = 1400;
    var RAD45 = Math.PI / 4;

    var cameraMotionActive = false;
    var cameraMotionClearTimer = null;

    function getCameraLookAt() {
        var p = typeof fg.cameraPosition === "function" ? fg.cameraPosition() : null;
        if (p && p.lookAt && isFinite(p.lookAt.x)) {
            return { x: p.lookAt.x, y: p.lookAt.y, z: p.lookAt.z };
        }
        return { x: 0, y: 0, z: 0 };
    }

    function applyRandomSceneOrOrbit() {
        if (cameraMotionActive) {
            return;
        }
        if (Math.random() < 0.5) {
            var sc = typeof fg.scene === "function" ? fg.scene() : null;
            if (sc) {
                sc.rotation.y += (Math.random() < 0.5 ? 1 : -1) * RAD45;
            }
            return;
        }
        var p = typeof fg.cameraPosition === "function" ? fg.cameraPosition() : null;
        if (!p || !isFinite(p.x) || !isFinite(p.z)) {
            return;
        }
        cameraMotionActive = true;
        bumpGraphActivity();
        var lk = getCameraLookAt();
        var sign = Math.random() < 0.5 ? 1 : -1;
        var angle = sign * ORBIT_ANGLE_RAD;
        var cos = Math.cos(angle);
        var sin = Math.sin(angle);
        var cx = p.x;
        var cy = p.y || 0;
        var cz = p.z;
        var nx = cx * cos + cz * sin;
        var nz = -cx * sin + cz * cos;
        if (typeof fg.cameraPosition === "function") {
            fg.cameraPosition({ x: nx, y: cy, z: nz }, lk, ORBIT_DURATION_MS);
        }
        if (cameraMotionClearTimer) {
            clearTimeout(cameraMotionClearTimer);
        }
        cameraMotionClearTimer = setTimeout(function () {
            cameraMotionActive = false;
            cameraMotionClearTimer = null;
            bumpGraphActivity();
        }, ORBIT_DURATION_MS + 200);
    }

    setTimeout(function () {
        applyRandomSceneOrOrbit();
        setInterval(applyRandomSceneOrOrbit, RANDOM_MOTION_INTERVAL_MS);
    }, RANDOM_MOTION_INTERVAL_MS);

    /* Как tags_3d.html: после паузы ввода — медленный поворот сцены вокруг Y */
    var IDLE_ROTATE_DELAY_MS = 1400;
    /* Поворот сцены вокруг Y при простое: 2× быстрее */
    var IDLE_ROTATE_Y_RAD_PER_SEC = 0.05;
    var lastGraphActivityMs = performance.now();
    var lastEngineTickMs = performance.now();

    function bumpGraphActivity() {
        lastGraphActivityMs = performance.now();
    }

    containerEl.addEventListener("pointerdown", bumpGraphActivity);
    containerEl.addEventListener("wheel", bumpGraphActivity, { passive: true });
    containerEl.addEventListener("touchstart", bumpGraphActivity, { passive: true });

    if (typeof fg.controls === "function") {
        try {
            var ctrls0 = fg.controls();
            if (ctrls0 && typeof ctrls0.addEventListener === "function") {
                ctrls0.addEventListener("change", bumpGraphActivity);
                ctrls0.addEventListener("end", bumpGraphActivity);
            }
        } catch (eCtrl) {
            /* ignore */
        }
    }

    var cam2xApplied = false;
    fg.onEngineTick(function () {
        var now = performance.now();
        var dt = Math.min(0.05, (now - lastEngineTickMs) / 1000);
        lastEngineTickMs = now;

        if (!cam2xApplied) {
            var p = fg.cameraPosition();
            if (p && typeof p.z === "number" && Math.abs(p.z) > 20) {
                fg.cameraPosition({ x: p.x || 0, y: p.y || 0, z: p.z * 2 });
                cam2xApplied = true;
            }
        }

        if (!cameraMotionActive && now - lastGraphActivityMs >= IDLE_ROTATE_DELAY_MS) {
            var sc2 = typeof fg.scene === "function" ? fg.scene() : null;
            if (sc2) {
                sc2.rotation.y += IDLE_ROTATE_Y_RAD_PER_SEC * dt;
            }
        }
    });

    function pushGraph() {
        /* d3-force ожидает, что link.source / link.target — те же объекты, что в nodes[].
           Строковые id после тика симуляции ломают разрешение → «Cannot create property 'vx' on string». */
        var nodeById = {};
        var ni;
        for (ni = 0; ni < graphData.nodes.length; ni++) {
            var n = graphData.nodes[ni];
            nodeById[String(n.id)] = n;
        }
        var nextLinks = [];
        var li;
        for (li = 0; li < graphData.links.length; li++) {
            var l = graphData.links[li];
            var s = linkEndpoint(l.source);
            var t = linkEndpoint(l.target);
            var so = nodeById[s];
            var to = nodeById[t];
            if (so && to) {
                nextLinks.push({ source: so, target: to, value: l.value });
            }
        }
        graphData.links = nextLinks;
        fg.graphData(graphData);
        if (typeof fg.refresh === "function") {
            fg.refresh();
        }
        if (typeof fg.d3ReheatSimulation === "function") {
            fg.d3ReheatSimulation();
        }
    }

    function applyForceLayoutParameters() {
        var linkMultiplier = getLinkDistanceMultiplier();
        var linkF = fg.d3Force("link");
        if (linkF) {
            if (typeof linkF.distance === "function") {
                linkF.distance(function (d) {
                    var raw = d.value != null ? Number(d.value) : 15;
                    if (isNaN(raw)) raw = 15;
                    return raw * 13 * values.v1 * 4 * linkMultiplier * 0.42;
                });
            }
            if (typeof linkF.strength === "function") {
                linkF.strength(function () {
                    return values.v4;
                });
            }
        }
        /* Отталкивание: many-body (charge); v3 — сила, theta — Barnes–Hut, chargeDist — дальность */
        var chargeF = fg.d3Force("charge");
        if (chargeF) {
            if (typeof chargeF.strength === "function") {
                var repel = -(30 + values.v3 * 720);
                chargeF.strength(repel);
            }
            if (typeof chargeF.theta === "function") {
                chargeF.theta(values.theta);
            }
            if (typeof chargeF.distanceMax === "function") {
                var cd = values.chargeDist;
                chargeF.distanceMax(cd >= 8000 ? 1e9 : cd);
            }
        }
        /* Гравитация к центру (0,0,0): v2 — сила притяжения */
        var centerF = fg.d3Force("center");
        if (centerF) {
            if (typeof centerF.strength === "function") {
                centerF.strength(0.04 + values.v2 * 0.48);
            }
            if (typeof centerF.x === "function") {
                centerF.x(0);
                centerF.y(0);
            }
            if (typeof centerF.z === "function") {
                centerF.z(0);
            }
        }
        /* Трение: velocity decay; v5 — ползунок «трение» (чем выше, тем сильнее гашение скорости) */
        if (typeof fg.d3VelocityDecay === "function") {
            var decay = Math.min(0.92, 0.12 + values.v5 * 0.78);
            fg.d3VelocityDecay(decay);
        }
        /* Скорость затухания alpha: связь с длиной рёбер и силой связи (остальные параметры тоже влияют на «живость») */
        if (typeof fg.d3AlphaDecay === "function") {
            var ad = 0.01 + values.v1 * 0.022 + (1 - values.v4) * 0.018;
            fg.d3AlphaDecay(Math.min(0.08, Math.max(0.006, ad)));
        }
        if (typeof fg.d3AlphaMin === "function") {
            fg.d3AlphaMin(0.0008 + values.v2 * 0.004);
        }
        /* После смены сил обязательно разогреть, иначе при alpha≈0 ползунки почти не ощущаются */
        if (typeof fg.d3ReheatSimulation === "function") {
            try {
                fg.d3ReheatSimulation();
            } catch (e) {
                /* при несовместимых версиях three/3d-force-graph reheat может падать до полной инициализации */
                if (window.console && console.warn) console.warn("d3ReheatSimulation:", e);
            }
        }
    }

    function resize() {
        var w = Math.max(2, containerEl.clientWidth || window.innerWidth || 320);
        var h = Math.max(2, containerEl.clientHeight || window.innerHeight || 240);
        fg.width(w).height(h);
        applyForceLayoutParameters();
    }
    window.addEventListener("resize", resize);
    resize();

    applyForceLayoutParameters();

    return {
        getNodes: function () {
            return graphData.nodes;
        },

        addNode: function (id, step, r) {
            if (r === undefined) r = 6;
            graphData.nodes.push({ id: String(id), step: step, r: r });
            pushGraph();
            return id;
        },

        removeNode: function (id) {
            if (this.findNodeIndex(id) < 0) return;
            var sid = String(id);
            graphData.links = graphData.links.filter(function (l) {
                return linkEndpoint(l.source) !== sid && linkEndpoint(l.target) !== sid;
            });
            var idx = this.findNodeIndex(id);
            if (idx >= 0) {
                graphData.nodes.splice(idx, 1);
            }
            pushGraph();
        },

        removeallLinks: function () {
            graphData.links.length = 0;
            pushGraph();
        },

        removeAllNodes: function () {
            graphData.nodes.length = 0;
            graphData.links.length = 0;
            pushGraph();
        },

        addLink: function (source, target, value) {
            var s = this.findNode(source);
            var t = this.findNode(target);
            if (!s || !t) return;
            graphData.links.push({
                source: s,
                target: t,
                value: value
            });
            pushGraph();
        },

        findNode: function (id) {
            var sid = String(id);
            for (var i = 0; i < graphData.nodes.length; i++) {
                if (String(graphData.nodes[i].id) === sid) return graphData.nodes[i];
            }
        },

        removeLinksForNode: function (node_id) {
            var nid = String(node_id);
            graphData.links = graphData.links.filter(function (l) {
                return linkEndpoint(l.source) !== nid && linkEndpoint(l.target) !== nid;
            });
            pushGraph();
        },

        findNodeIndex: function (id) {
            var sid = String(id);
            for (var k = 0; k < graphData.nodes.length; k++) {
                if (String(graphData.nodes[k].id) === sid) {
                    return k;
                }
            }
            return -1;
        },

        setValues: function (v) {
            values = mergeForceDefaults(v);
            applyForceLayoutParameters();
        }
    };
}

function keepNodesOnTop() {
    /* no-op: 2D SVG z-order trick; not used in WebGL graph */
}

var graphInitAttempts = 0;
var maxGraphInitAttempts = 80;

function initGraph() {
    if (typeof ForceGraph3D === "undefined") {
        graphInitAttempts += 1;
        if (graphInitAttempts >= maxGraphInitAttempts) {
            console.error("ForceGraph3D / 3d-force-graph failed to load.");
            var st = document.getElementById("semantic-status");
            if (st) st.textContent = "3d-force-graph load failed";
            return;
        }
        setTimeout(initGraph, 100);
        return;
    }
    var root = document.getElementById("semantic3d-root");
    if (!root) {
        console.error("semantic3d-root missing");
        return;
    }
    try {
        graph = createSemanticGraph3D(root);
    } catch (err) {
        console.error("createSemanticGraph3D:", err);
        graph = null;
    }
    if (!graph) {
        var el = document.getElementById("semantic-status");
        if (el) el.textContent = "graph init failed";
    }
}

var SEMANTIC_MAX_NODES = 100;
var SEMANTIC_REPLAY_MS = 420;

function semanticRandomIntInclusive(min, max) {
    return min + Math.floor(Math.random() * (max - min + 1));
}

var demoEdges = [];
var demoIndex = 0;
var demoTimer = null;
var demoLinkKeys = {};
var demoPlaying = false;
/** До завершения первого автозапуска демо (или явного reset) живые данные не применяются. */
var demoCompleted = false;

var liveCollectTimer = null;
var liveCollectQueue = [];
var liveCollectStepNum = 1;

var SEMANTIC_LOG_MAX_LINES = 400;
var semanticLogLines = [];

function clearSemanticLog() {
    semanticLogLines = [];
    var el = document.getElementById("log_semantic");
    if (el) el.textContent = "";
}

function stopLiveCollectReplay() {
    if (liveCollectTimer) {
        clearInterval(liveCollectTimer);
        liveCollectTimer = null;
    }
    liveCollectQueue = [];
}

function appendSemanticLogLine(src, head) {
    var line = String(src) + " > " + String(head);
    semanticLogLines.push(line);
    if (semanticLogLines.length > SEMANTIC_LOG_MAX_LINES) {
        semanticLogLines = semanticLogLines.slice(-SEMANTIC_LOG_MAX_LINES);
    }
    var logEl = document.getElementById("log_semantic");
    if (logEl) {
        logEl.textContent = semanticLogLines.join("\n");
        logEl.scrollTop = logEl.scrollHeight;
    }
}

function semanticTrimNodes() {
    if (!graph) return;
    while (graph.getNodes().length > SEMANTIC_MAX_NODES) {
        graph.removeNode(graph.getNodes()[0].id);
    }
}

function semanticEnsureNode(step, token) {
    if (!graph) return;
    if (!graph.findNode(token)) {
        graph.addNode(token, step, 8);
    }
}

function appendDependencyEdge(src, head, stepNum) {
    if (!graph) return false;
    var key = String(src) + "\u0000" + String(head);
    if (demoLinkKeys[key]) {
        return false;
    }
    demoLinkKeys[key] = true;
    semanticEnsureNode(stepNum, src);
    semanticEnsureNode(stepNum, head);
    graph.addLink(src, head, "15");
    appendSemanticLogLine(src, head);
    keepNodesOnTop();
    semanticTrimNodes();
    return true;
}

function semanticApplyEdge(edge) {
    if (!graph) return;
    appendDependencyEdge(edge.src, edge.head, edge.step);
}

function semanticUpdateStatus() {
    var el = document.getElementById("semantic-status");
    if (!el) return;
    el.textContent = demoEdges.length
        ? "edge " + String(demoIndex) + " / " + String(demoEdges.length)
        : "no edges";
}

function semanticStepOnce() {
    if (!graph) return;
    if (demoIndex >= demoEdges.length) {
        semanticPause();
        return;
    }
    semanticApplyEdge(demoEdges[demoIndex]);
    demoIndex += 1;
    semanticUpdateStatus();
}

function semanticPause() {
    demoPlaying = false;
    if (demoTimer) {
        clearInterval(demoTimer);
        demoTimer = null;
    }
    var playBtn = document.getElementById("semantic-play");
    if (playBtn) playBtn.textContent = "play";
    if (!demoCompleted && demoEdges.length && demoIndex >= demoEdges.length) {
        demoCompleted = true;
        startSemanticLastCollectPoll();
    }
}

function semanticPlay() {
    stopLiveCollectReplay();
    if (!demoEdges.length || !graph) return;
    if (demoIndex >= demoEdges.length) {
        demoIndex = 0;
        demoLinkKeys = {};
        clearSemanticLog();
        graph.removeallLinks();
        graph.removeAllNodes();
    }
    demoPlaying = true;
    var playBtn = document.getElementById("semantic-play");
    if (playBtn) playBtn.textContent = "pause";
    if (demoTimer) clearInterval(demoTimer);
    demoTimer = setInterval(semanticStepOnce, SEMANTIC_REPLAY_MS);
}

function semanticTogglePlay() {
    if (demoPlaying) {
        semanticPause();
    } else {
        semanticPlay();
    }
}

function semanticReset() {
    semanticPause();
    stopLiveCollectReplay();
    semanticWorkerApplySinceClear = 0;
    semanticWorkerClearEvery = semanticRandomIntInclusive(10, 20);
    demoIndex = 0;
    demoLinkKeys = {};
    clearSemanticLog();
    if (!graph) {
        semanticUpdateStatus();
        return;
    }
    graph.removeallLinks();
    graph.removeAllNodes();
    semanticUpdateStatus();
}

function semanticStepManual() {
    if (!graph) return;
    if (demoIndex >= demoEdges.length) {
        stopLiveCollectReplay();
        demoIndex = 0;
        demoLinkKeys = {};
        clearSemanticLog();
        graph.removeallLinks();
        graph.removeAllNodes();
    }
    semanticStepOnce();
}

function wireDemoControls() {
    var playBtn = document.getElementById("semantic-play");
    var stepBtn = document.getElementById("semantic-step-once");
    var resetBtn = document.getElementById("semantic-reset");
    if (playBtn) playBtn.addEventListener("click", semanticTogglePlay);
    if (stepBtn) stepBtn.addEventListener("click", function () {
        semanticPause();
        semanticStepManual();
    });
    if (resetBtn) resetBtn.addEventListener("click", semanticReset);
}

function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, n));
}

function readForceSlidersIntoValues() {
    function num(sel) {
        var el = document.querySelector('[data-force-key="' + sel + '"]');
        if (!el) return null;
        return parseInt(el.value, 10);
    }
    var a = num("v1");
    if (a != null && !isNaN(a)) values.v1 = clamp(a, 5, 100) / 100;
    a = num("v2");
    if (a != null && !isNaN(a)) values.v2 = clamp(a, 5, 100) / 100;
    a = num("v3");
    if (a != null && !isNaN(a)) values.v3 = clamp(a, 5, 100) / 100;
    a = num("v4");
    if (a != null && !isNaN(a)) values.v4 = clamp(a, 5, 100) / 100;
    a = num("v5");
    if (a != null && !isNaN(a)) values.v5 = clamp(a, 5, 100) / 100;
    a = num("theta");
    if (a != null && !isNaN(a)) values.theta = clamp(a, 15, 95) / 100;
    a = num("chargeDist");
    if (a != null && !isNaN(a)) values.chargeDist = clamp(a, 400, 10000);
}

function syncForceSliderUi() {
    function setInput(key, sliderVal) {
        var el = document.querySelector('[data-force-key="' + key + '"]');
        if (el) el.value = String(sliderVal);
    }
    setInput("v1", clamp(Math.round(values.v1 * 100), 5, 100));
    setInput("v2", clamp(Math.round(values.v2 * 100), 5, 100));
    setInput("v3", clamp(Math.round(values.v3 * 100), 5, 100));
    setInput("v4", clamp(Math.round(values.v4 * 100), 5, 100));
    setInput("v5", clamp(Math.round(values.v5 * 100), 5, 100));
    setInput("theta", clamp(Math.round(values.theta * 100), 15, 95));
    var cd = values.chargeDist;
    if (cd >= 8000 || !isFinite(cd)) cd = 10000;
    setInput("chargeDist", clamp(Math.round(cd), 400, 10000));

    var displays = document.querySelectorAll("[data-force-display]");
    for (var i = 0; i < displays.length; i++) {
        var d = displays[i];
        var k = d.getAttribute("data-force-display");
        if (!k) continue;
        if (k === "chargeDist") {
            d.textContent = values.chargeDist >= 8000 ? "∞" : String(Math.round(values.chargeDist));
        } else if (k === "theta") {
            d.textContent = values.theta.toFixed(2);
        } else {
            d.textContent = values[k].toFixed(2);
        }
    }
}

var _forceSliderSaveTimer = null;

function onForceSliderInput() {
    readForceSlidersIntoValues();
    syncForceSliderUi();
    if (graph && typeof graph.setValues === "function") {
        graph.setValues(values);
    }
    if (_forceSliderSaveTimer) clearTimeout(_forceSliderSaveTimer);
    _forceSliderSaveTimer = setTimeout(function () {
        saveForceParamsToStorage();
        _forceSliderSaveTimer = null;
    }, 120);
}

function resetForceParamsToDefaults() {
    try {
        localStorage.removeItem(SEMANTIC_FORCE_LS);
    } catch (e) { /* ignore */ }
    values = mergeForceDefaults(null);
    syncForceSliderUi();
    if (graph && typeof graph.setValues === "function") {
        graph.setValues(values);
    }
}

function wireForceSliders() {
    syncForceSliderUi();
    var inputs = document.querySelectorAll("#semantic-force-panel input[type=range][data-force-key]");
    for (var i = 0; i < inputs.length; i++) {
        inputs[i].addEventListener("input", onForceSliderInput);
        inputs[i].addEventListener("change", function () {
            readForceSlidersIntoValues();
            saveForceParamsToStorage();
        });
    }
    var resetBtn = document.getElementById("semantic-force-reset");
    if (resetBtn) resetBtn.addEventListener("click", resetForceParamsToDefaults);
}

var semanticSocket = null;
var semanticPingTimer = null;
var semanticPingCounter = 0;
var semanticPingStartMs = 0;

var lastAppliedCollectFp = null;
var semanticLastCollectPollTimer = null;
var semanticLastCollectPollCount = 0;

var lastAppliedMoodFp = null;
var semanticMoodPollTimer = null;

var semanticWorkerApplySinceClear = 0;
var semanticWorkerClearEvery = semanticRandomIntInclusive(10, 20);

function stopSemanticPingLoop() {
    if (semanticPingTimer) {
        clearInterval(semanticPingTimer);
        semanticPingTimer = null;
    }
}

function setSemanticWorkerHint(text) {
    var el = document.getElementById("semantic-worker-hint");
    if (el) {
        el.textContent = text;
    }
}

function semanticCollectFingerprint(data) {
    if (!data || typeof data !== "object") {
        return "";
    }
    var lines = data.dependency_lines;
    var n = Array.isArray(lines) ? lines.length : 0;
    return [
        data.received_at || "",
        String(data.number || ""),
        String(n),
        String((data.error || "")).slice(0, 120),
    ].join("\u0001");
}

function applySemanticCollectPayload(data, sourceTag) {
    if (!demoCompleted) {
        return;
    }
    if (!data || typeof data !== "object") {
        return;
    }
    var fp = semanticCollectFingerprint(data);
    if (fp && fp === lastAppliedCollectFp) {
        return;
    }

    stopLiveCollectReplay();
    semanticPause();

    if (!graph) {
        return;
    }

    var lines = data.dependency_lines;
    var stepLabel = data.number != null ? String(data.number) : "?";
    var src = sourceTag || "event";

    if (!Array.isArray(lines) || !lines.length) {
        if (fp) {
            lastAppliedCollectFp = fp;
        }
        setSemanticWorkerHint(
            src + ": шаг " + stepLabel + " — нет dependency_lines (проверьте логи / semantic-service)"
        );
        return;
    }

    semanticWorkerApplySinceClear += 1;
    var doFullClear = semanticWorkerApplySinceClear >= semanticWorkerClearEvery;
    if (doFullClear) {
        graph.removeallLinks();
        graph.removeAllNodes();
        demoLinkKeys = {};
        clearSemanticLog();
        semanticWorkerApplySinceClear = 0;
        semanticWorkerClearEvery = semanticRandomIntInclusive(10, 20);
    }

    liveCollectStepNum = parseInt(data.number, 10);
    if (!liveCollectStepNum || isNaN(liveCollectStepNum)) {
        liveCollectStepNum = 1;
    }

    liveCollectQueue = [];
    for (var i = 0; i < lines.length; i++) {
        var line = String(lines[i]);
        var ix = line.indexOf(">");
        if (ix < 0) {
            continue;
        }
        var s = line.slice(0, ix).trim();
        var h = line.slice(ix + 1).trim();
        if (!s || !h) {
            continue;
        }
        liveCollectQueue.push({ src: s, head: h });
    }

    if (!liveCollectQueue.length) {
        if (fp) {
            lastAppliedCollectFp = fp;
        }
        setSemanticWorkerHint(src + ": шаг " + stepLabel + " — строки не распарсились (ожидается token>head)");
        return;
    }

    if (fp) {
        lastAppliedCollectFp = fp;
    }
    var ra = data.received_at ? " @ " + data.received_at : "";
    var packHint = doFullClear
        ? " · граф очищен; следующий через " + String(semanticWorkerClearEvery) + " пак."
        : " · накопление, полный сброс через ~" +
          String(semanticWorkerClearEvery - semanticWorkerApplySinceClear) +
          " пак.";
    setSemanticWorkerHint(
        src + ": шаг " + stepLabel + ", рёбер " + String(liveCollectQueue.length) + ra + packHint
    );

    liveCollectTimer = setInterval(function () {
        if (!graph) {
            stopLiveCollectReplay();
            return;
        }
        if (!liveCollectQueue.length) {
            clearInterval(liveCollectTimer);
            liveCollectTimer = null;
            return;
        }
        var e = liveCollectQueue.shift();
        appendDependencyEdge(e.src, e.head, liveCollectStepNum);
    }, SEMANTIC_REPLAY_MS);
}

function pollSemanticLastCollect() {
    semanticLastCollectPollCount += 1;
    fetch("/api/semantic/last-collect/", { credentials: "same-origin", cache: "no-store" })
        .then(function (r) {
            return r.json();
        })
        .then(function (j) {
            if (!j) {
                return;
            }
            if (j.empty || !j.ok) {
                if (j.empty && semanticLastCollectPollCount <= 1 && !lastAppliedCollectFp) {
                    setSemanticWorkerHint(
                        "HTTP: на сервере ещё не было semantic_collect. " +
                            "Шаги silent=1 не запускают цепочку; пустой snippet после analyze тоже."
                    );
                }
                return;
            }
            if (j.data) {
                applySemanticCollectPayload(j.data, "HTTP");
            }
        })
        .catch(function () {
            /* ignore transient errors */
        });
}

function moodCollectFingerprint(data) {
    if (!data || typeof data !== "object") {
        return "";
    }
    return [
        data.received_at || "",
        String(data.step_number || ""),
        String(data.timestamp || ""),
        String((data.error || "")).slice(0, 80),
    ].join("\u0001");
}

function normalizeHex(h) {
    if (!h) {
        return "#333333";
    }
    var s = String(h).trim();
    if (s.charAt(0) !== "#") {
        s = "#" + s;
    }
    return s.length === 4 ? s : s.slice(0, 7);
}

function applyMoodCollectPayload(data, sourceTag) {
    if (!demoCompleted) {
        return;
    }
    if (!data || typeof data !== "object") {
        return;
    }
    var fp = moodCollectFingerprint(data);
    if (fp && fp === lastAppliedMoodFp) {
        return;
    }
    if (fp) {
        lastAppliedMoodFp = fp;
    }

    var pals = Array.isArray(data.palette) ? data.palette : [];
    var root = document.documentElement;
    for (var i = 0; i < 5; i++) {
        var hex = pals[i] && pals[i].hex ? normalizeHex(pals[i].hex) : "#1a1a1a";
        root.style.setProperty("--mood-c" + String(i), hex);
    }

    var bg = document.getElementById("semantic-mood-bg");
    if (bg) {
        bg.style.opacity = data.error ? "0.25" : "0.52";
    }

    var logEl = document.getElementById("log_mood");
    if (logEl) {
        var words = [];
        if (data.dominant_mood) {
            words.push(String(data.dominant_mood));
        }
        if (data.full_description) {
            words.push(String(data.full_description));
        }
        for (var pi = 0; pi < pals.length; pi++) {
            if (pals[pi].name) {
                words.push(String(pals[pi].name));
            }
        }
        var line =
            "[" +
            (sourceTag || "mood") +
            "] " +
            (data.timestamp || data.received_at || "") +
            " step=" +
            (data.step_number != null ? String(data.step_number) : "—") +
            "\n" +
            words.join(" · ") +
            "\n" +
            pals
                .map(function (p) {
                    return (p.hex || "") + " " + (p.mood || "");
                })
                .join(" | ");
        logEl.textContent = line + "\n\n" + logEl.textContent;
        if (logEl.textContent.length > 12000) {
            logEl.textContent = logEl.textContent.slice(0, 12000);
        }
    }
}

function pollMoodLastCollect() {
    fetch("/api/semantic/mood-last/", { credentials: "same-origin", cache: "no-store" })
        .then(function (r) {
            return r.json();
        })
        .then(function (j) {
            if (j && j.ok && j.data) {
                applyMoodCollectPayload(j.data, "HTTP");
            }
        })
        .catch(function () {
            /* ignore */
        });
}

function startSemanticLastCollectPoll() {
    if (semanticLastCollectPollTimer) {
        return;
    }
    pollSemanticLastCollect();
    semanticLastCollectPollTimer = setInterval(pollSemanticLastCollect, 3000);
    pollMoodLastCollect();
    if (!semanticMoodPollTimer) {
        semanticMoodPollTimer = setInterval(pollMoodLastCollect, 3500);
    }
}

function paintSemanticSocketMetrics(latencyMs) {
    var cEl = document.getElementById("semantic-socket-counter");
    var lEl = document.getElementById("semantic-socket-latency");
    if (cEl) {
        cEl.textContent = String(semanticPingCounter).padStart(4, "0");
    }
    if (lEl) {
        lEl.textContent =
            latencyMs == null ? "—" : String(latencyMs).padStart(4, "0");
    }
}

function initSemanticSocket() {
    if (typeof io === "undefined") {
        return;
    }
    semanticSocket = io({ path: "/socket.io" });

    semanticSocket.on("connect", function () {
        stopSemanticPingLoop();
        semanticPingTimer = setInterval(function () {
            semanticPingCounter += 1;
            semanticPingStartMs = Date.now();
            semanticSocket.emit("my_ping");
        }, 250);
    });

    semanticSocket.on("disconnect", function () {
        stopSemanticPingLoop();
    });

    semanticSocket.on("my_pong", function () {
        var lat = Date.now() - semanticPingStartMs;
        paintSemanticSocketMetrics(lat);
    });

    semanticSocket.on("semantic_collect", function (data) {
        applySemanticCollectPayload(data, "Socket.IO");
    });

    semanticSocket.on("mood_collect", function (data) {
        applyMoodCollectPayload(data, "Socket.IO");
    });
}

function loadDemoPayload() {
    return fetch("/api/semantic/demo-edges/", { credentials: "same-origin", cache: "no-store" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            demoEdges = Array.isArray(data.edges) ? data.edges : [];
            var srcPanel = document.getElementById("semantic-source-panel");
            if (srcPanel && data.source_text) {
                srcPanel.textContent = data.source_text;
            }
            semanticReset();
            if (!demoEdges.length) {
                var el = document.getElementById("semantic-status");
                if (el) el.textContent = "no data (semantic/semantic.txt)";
                demoCompleted = true;
                startSemanticLastCollectPoll();
                return;
            }
            semanticPlay();
        })
        .catch(function (err) {
            console.error(err);
            var el = document.getElementById("semantic-status");
            if (el) el.textContent = "load failed";
        });
}

function startWhenGraphReady(attempts) {
    if (graph) {
        if (typeof graph.setValues === "function") {
            graph.setValues(values);
        }
        loadDemoPayload();
        return;
    }
    if (attempts > 150) {
        loadDemoPayload();
        return;
    }
    setTimeout(function () {
        startWhenGraphReady(attempts + 1);
    }, 40);
}

setTimeout(function () {
    initGraph();
    wireDemoControls();
    wireForcePanelCollapse();
    wireForcePanelHotkey();
    wireForceSliders();
    initSemanticSocket();
    startWhenGraphReady(0);
}, 50);
