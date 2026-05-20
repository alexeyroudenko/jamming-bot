/* global ForceGraph3D, io, THREE */
/* Jamming Bot semantic demo: same data path as semantic_demo.js, 3D force graph (WebGL). */

function semanticPeriodicLog(name, detail) {
    try {
        if (typeof console !== "undefined" && console.log) {
            if (detail !== undefined && detail !== null && detail !== "") {
                console.log("[semantic3d] " + name, detail);
            } else {
                console.log("[semantic3d] " + name);
            }
        }
    } catch (eLog) {
        /* ignore */
    }
}

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

/** Доля расстояния |якорь| от центра сцены → амплитуда случайного смещения новой ноды */
var SEMANTIC_SPAWN_JITTER_FRAC = 0.3;
/** Макс. угол поворота вектора 3×якорь вокруг случайной оси: доля π (30% → 0.3π рад ≈ 54°) */
var SEMANTIC_SPAWN_ROT_FRAC = 0.3;

function semanticRandomUnitSphere3() {
    var u = Math.random() * 2 * Math.PI;
    var v = Math.random() * 2 - 1;
    var s = Math.sqrt(Math.max(0, 1 - v * v));
    return {
        x: Math.cos(u) * s,
        y: Math.sin(u) * s,
        z: v
    };
}

function semanticVecCross(a, b) {
    return {
        x: a.y * b.z - a.z * b.y,
        y: a.z * b.x - a.x * b.z,
        z: a.x * b.y - a.y * b.x
    };
}

function semanticVecDot(a, b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

function semanticVecScale(a, s) {
    return { x: a.x * s, y: a.y * s, z: a.z * s };
}

function semanticVecAdd(a, b) {
    return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

function semanticRotateRodrigues(v, kUnit, theta) {
    var cosT = Math.cos(theta);
    var sinT = Math.sin(theta);
    var kd = semanticVecDot(kUnit, v);
    var kxv = semanticVecCross(kUnit, v);
    return semanticVecAdd(
        semanticVecAdd(semanticVecScale(v, cosT), semanticVecScale(kxv, sinT)),
        semanticVecScale(kUnit, kd * (1 - cosT))
    );
}

/**
 * База: 3× позиция якоря; слегка: смещение на SEMANTIC_SPAWN_JITTER_FRAC×|якорь| в случайном R³
 * и поворот базового вектора вокруг случайной оси на до ±SEMANTIC_SPAWN_ROT_FRAC×π.
 * @param {number} ax
 * @param {number} ay
 * @param {number} az
 * @returns {{ x: number, y: number, z: number }}
 */
function semanticSpawnJitteredFromAnchor(ax, ay, az) {
    var bx = ax * 3;
    var by = ay * 3;
    var bz = az * 3;
    var rA = Math.sqrt(ax * ax + ay * ay + az * az);
    var jitterR = SEMANTIC_SPAWN_JITTER_FRAC * (rA > 1e-9 ? rA : 1);
    var ju = semanticRandomUnitSphere3();
    var k = semanticRandomUnitSphere3();
    var base = { x: bx, y: by, z: bz };
    var omega = (Math.random() * 2 - 1) * (SEMANTIC_SPAWN_ROT_FRAC * Math.PI);
    var rot = semanticRotateRodrigues(base, k, omega);
    return {
        x: rot.x + ju.x * jitterR,
        y: rot.y + ju.y * jitterR,
        z: rot.z + ju.z * jitterR
    };
}

/** d3-force / 3d-force-graph фиксируют узел через fx,fy,fz при drag — снять, иначе симуляция не тянет узел */
function semanticClearNodeForcePin(node) {
    if (!node || typeof node !== "object") {
        return;
    }
    delete node.fx;
    delete node.fy;
    delete node.fz;
}

/**
 * @param {HTMLElement} containerEl
 * @returns {{ getNodes: Function, addNode: Function, removeNode: Function, addLink: Function, removeallLinks: Function, removeAllNodes: Function, findNode: Function, removeLinksForNode: Function, findNodeIndex: Function, refreshSpawnFromPartner: Function, setValues: Function } | null}
 * addNode(id, step, r, anchorNode?) — при anchor: позиция из semanticSpawnJitteredFromAnchor (3× + джиттер).
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

    if (typeof fg.onNodeDragEnd === "function") {
        fg.onNodeDragEnd(function (node) {
            semanticClearNodeForcePin(node);
        });
    }

    /* Периодический tilt сцены / орбита камеры (applyRandomSceneOrOrbit) — выключено */

    /* После паузы ввода — медленный поворот сцены вокруг горизонтальной оси X */
    var IDLE_ROTATE_DELAY_MS = 1400;
    var IDLE_ROTATE_X_RAD_PER_SEC = 0.05 * 2.5;
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
                /* 'change' часто шлётся каждый кадр при инерции — гасит idle; достаточно 'end' */
                ctrls0.addEventListener("end", bumpGraphActivity);
            }
        } catch (eCtrl) {
            /* ignore */
        }
    }

    var cam2xApplied = false;
    var lastPeriodicIdleLogMs = 0;
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

        if (now - lastGraphActivityMs >= IDLE_ROTATE_DELAY_MS) {
            var sc2 = typeof fg.scene === "function" ? fg.scene() : null;
            if (sc2) {
                sc2.rotation.x += IDLE_ROTATE_X_RAD_PER_SEC * dt;
                if (now - lastPeriodicIdleLogMs >= 2500) {
                    lastPeriodicIdleLogMs = now;
                    semanticPeriodicLog("onEngineTick.idleRotateSceneX");
                }
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

        addNode: function (id, step, r, anchorNode) {
            if (r === undefined) r = 6;
            var node = { id: String(id), step: step, r: r };
            if (
                anchorNode &&
                typeof anchorNode === "object" &&
                isFinite(Number(anchorNode.x)) &&
                isFinite(Number(anchorNode.y)) &&
                isFinite(Number(anchorNode.z))
            ) {
                var ax = Number(anchorNode.x);
                var ay = Number(anchorNode.y);
                var az = Number(anchorNode.z);
                var sp = semanticSpawnJitteredFromAnchor(ax, ay, az);
                node.x = sp.x;
                node.y = sp.y;
                node.z = sp.z;
                node.vx = 0;
                node.vy = 0;
                node.vz = 0;
                semanticClearNodeForcePin(node);
            }
            graphData.nodes.push(node);
            semanticPeriodicLog("createSemanticGraph3D.addNode", String(id));
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

        /**
         * Ставит newId рядом с partnerId: semanticSpawnJitteredFromAnchor (3× + джиттер), когда у партнёра уже есть x,y,z.
         * @returns {boolean} true если применили координаты
         */
        refreshSpawnFromPartner: function (newId, partnerId) {
            var n = this.findNode(newId);
            var p = this.findNode(partnerId);
            if (!n || !p) {
                return false;
            }
            if (
                !isFinite(Number(p.x)) ||
                !isFinite(Number(p.y)) ||
                !isFinite(Number(p.z))
            ) {
                return false;
            }
            var px = Number(p.x);
            var py = Number(p.y);
            var pz = Number(p.z);
            semanticPeriodicLog(
                "createSemanticGraph3D.refreshSpawnFromPartner",
                String(newId) + " ← " + String(partnerId)
            );
            var sp = semanticSpawnJitteredFromAnchor(px, py, pz);
            n.x = sp.x;
            n.y = sp.y;
            n.z = sp.z;
            n.vx = 0;
            n.vy = 0;
            n.vz = 0;
            semanticClearNodeForcePin(n);
            pushGraph();
            if (typeof fg.refresh === "function") {
                fg.refresh();
            }
            if (typeof fg.d3ReheatSimulation === "function") {
                try {
                    fg.d3ReheatSimulation();
                } catch (eRh) {
                    /* ignore */
                }
            }
            return true;
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
            semanticPeriodicLog("initGraph.giveUpForceGraph3D", String(graphInitAttempts));
            return;
        }
        if (graphInitAttempts % 10 === 1) {
            semanticPeriodicLog("initGraph.retryForceGraph3D", String(graphInitAttempts));
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
    } else {
        semanticPeriodicLog("initGraph", "createSemanticGraph3D ok");
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

/** Полный сброс collect-графа только при «толстом» пакете: больше стольки валидных рёбер */
var SEMANTIC_COLLECT_FULL_CLEAR_MIN_EDGES = 20;

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

var SEMANTIC_DEFER_SPAWN_MAX_FRAMES = 24;

/**
 * Если новая нода не получила якорь синхронно (оба конца ребра новые или симуляция ещё не выставила x,y,z),
 * догоняем позицию по rAF.
 */
function scheduleDeferredAnchorSpawn(prevHadSrc, prevHadHead, srcId, headId) {
    if (prevHadSrc && prevHadHead) {
        return;
    }
    semanticPeriodicLog(
        "scheduleDeferredAnchorSpawn",
        String(srcId) + " | " + String(headId) + " prevSrc=" + String(prevHadSrc) + " prevHead=" + String(prevHadHead)
    );
    var frames = 0;
    function tick() {
        if (!graph || typeof graph.refreshSpawnFromPartner !== "function") {
            return;
        }
        frames += 1;
        if (frames === 1) {
            semanticPeriodicLog("scheduleDeferredAnchorSpawn.tick", "rAF start");
        }
        if (frames > SEMANTIC_DEFER_SPAWN_MAX_FRAMES) {
            return;
        }
        var done = false;
        if (!prevHadSrc && prevHadHead) {
            done = graph.refreshSpawnFromPartner(srcId, headId);
        } else if (!prevHadHead) {
            done = graph.refreshSpawnFromPartner(headId, srcId);
        }
        if (done) {
            semanticPeriodicLog("scheduleDeferredAnchorSpawn.done");
            return;
        }
        requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

/**
 * @param {number} step
 * @param {string} token
 * @param {string} [partnerId] — уже существующая нода на другом конце ребра; новая ставится в 3× её координаты.
 */
function semanticEnsureNode(step, token, partnerId) {
    if (!graph) return;
    if (graph.findNode(token)) {
        return;
    }
    var anchor = null;
    if (partnerId != null && partnerId !== "") {
        anchor = graph.findNode(String(partnerId));
    }
    graph.addNode(token, step, 8, anchor);
}

function appendDependencyEdge(src, head, stepNum) {
    if (!graph) return false;
    var key = String(src) + "\u0000" + String(head);
    if (demoLinkKeys[key]) {
        return false;
    }
    var prevHadSrc = !!graph.findNode(src);
    var prevHadHead = !!graph.findNode(head);
    demoLinkKeys[key] = true;
    /* Порядок: сначала конец с уже известной позицией, затем новый — у якоря будут x,y,z после первого add. */
    semanticEnsureNode(stepNum, src, head);
    semanticEnsureNode(stepNum, head, src);
    graph.addLink(src, head, "15");
    scheduleDeferredAnchorSpawn(prevHadSrc, prevHadHead, src, head);
    appendSemanticLogLine(src, head);
    keepNodesOnTop();
    semanticTrimNodes();
    semanticPeriodicLog("appendDependencyEdge", String(src) + " > " + String(head) + " step=" + String(stepNum));
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
    semanticPeriodicLog("semanticStepOnce", "demoIndex=" + String(demoIndex));
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
    semanticPeriodicLog("semanticPause");
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
    semanticPeriodicLog("semanticPlay");
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
    semanticPeriodicLog("semanticReset");
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
    semanticPeriodicLog("semanticStepManual");
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
        semanticPeriodicLog("onForceSliderInput.debouncedSaveLocalStorage");
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

    var parsedEdges = [];
    var pi;
    for (pi = 0; pi < lines.length; pi++) {
        var line0 = String(lines[pi]);
        var ix0 = line0.indexOf(">");
        if (ix0 < 0) {
            continue;
        }
        var s0 = line0.slice(0, ix0).trim();
        var h0 = line0.slice(ix0 + 1).trim();
        if (!s0 || !h0) {
            continue;
        }
        parsedEdges.push({ src: s0, head: h0 });
    }

    if (!parsedEdges.length) {
        if (fp) {
            lastAppliedCollectFp = fp;
        }
        setSemanticWorkerHint(src + ": шаг " + stepLabel + " — строки не распарсились (ожидается token>head)");
        return;
    }

    var validEdgeCount = parsedEdges.length;

    semanticPeriodicLog(
        "applySemanticCollectPayload",
        String(src) + " step=" + stepLabel + " edges=" + String(validEdgeCount)
    );

    semanticWorkerApplySinceClear += 1;
    var atOrOver = semanticWorkerApplySinceClear >= semanticWorkerClearEvery;
    var bigBatch = validEdgeCount > SEMANTIC_COLLECT_FULL_CLEAR_MIN_EDGES;
    if (atOrOver && !bigBatch) {
        semanticWorkerApplySinceClear = 0;
    }
    var doFullClear = atOrOver && bigBatch;
    if (doFullClear) {
        semanticPeriodicLog("applySemanticCollectPayload.graphFullClear", "edges=" + String(validEdgeCount));
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

    liveCollectQueue = parsedEdges.slice();

    if (fp) {
        lastAppliedCollectFp = fp;
    }
    var ra = data.received_at ? " @ " + data.received_at : "";
    var packHint;
    if (doFullClear) {
        packHint =
            " · граф очищен (порог и >" +
            String(SEMANTIC_COLLECT_FULL_CLEAR_MIN_EDGES) +
            " рёбер); следующий через " +
            String(semanticWorkerClearEvery) +
            " пак.";
    } else if (atOrOver && !bigBatch) {
        packHint =
            " · пакет ≤" +
            String(SEMANTIC_COLLECT_FULL_CLEAR_MIN_EDGES) +
            " рёбер — сброс счётчика; полный clear при пороге и >" +
            String(SEMANTIC_COLLECT_FULL_CLEAR_MIN_EDGES) +
            ".";
    } else {
        packHint =
            " · накопление, полный сброс при ~" +
            String(semanticWorkerClearEvery - semanticWorkerApplySinceClear) +
            " пак. и >" +
            String(SEMANTIC_COLLECT_FULL_CLEAR_MIN_EDGES) +
            " рёбер.";
    }
    setSemanticWorkerHint(
        src + ": шаг " + stepLabel + ", рёбер " + String(validEdgeCount) + ra + packHint
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
        semanticPeriodicLog("liveCollectReplay.timerAppendEdge", String(e.src) + " > " + String(e.head));
        appendDependencyEdge(e.src, e.head, liveCollectStepNum);
    }, SEMANTIC_REPLAY_MS);
}

function pollSemanticLastCollect() {
    semanticPeriodicLog("pollSemanticLastCollect", "n=" + String(semanticLastCollectPollCount + 1));
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

    semanticPeriodicLog("applyMoodCollectPayload", String(sourceTag || "mood"));

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
    semanticPeriodicLog("pollMoodLastCollect");
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
        semanticPeriodicLog("semanticSocket.connect");
        stopSemanticPingLoop();
        semanticPingTimer = setInterval(function () {
            semanticPingCounter += 1;
            semanticPingStartMs = Date.now();
            semanticSocket.emit("my_ping");
            if (semanticPingCounter % 25 === 0) {
                semanticPeriodicLog("semanticSocket.pingEmit", "counter=" + String(semanticPingCounter));
            }
        }, 250);
    });

    semanticSocket.on("disconnect", function () {
        semanticPeriodicLog("semanticSocket.disconnect");
        stopSemanticPingLoop();
    });

    semanticSocket.on("my_pong", function () {
        var lat = Date.now() - semanticPingStartMs;
        paintSemanticSocketMetrics(lat);
    });

    semanticSocket.on("semantic_inject_begin", function (data) {
        semanticPeriodicLog("semanticSocket.on.semantic_inject_begin");
        semanticPause();
        stopLiveCollectReplay();
        demoPlaying = false;
        demoIndex = 0;
        demoLinkKeys = {};
        if (demoTimer) {
            clearInterval(demoTimer);
            demoTimer = null;
        }
        clearSemanticLog();
        if (graph) {
            graph.removeallLinks();
            graph.removeAllNodes();
        }
        demoCompleted = true;
        semanticUpdateStatus();
        setSemanticWorkerHint(
            "inject" + (data && data.inject_id ? " " + data.inject_id : "") + ": ожидание semantic_collect…"
        );
    });

    semanticSocket.on("semantic_restore_demo", function (data) {
        semanticPeriodicLog("semanticSocket.on.semantic_restore_demo");
        semanticReset();
        loadDemoPayload();
    });

    semanticSocket.on("semantic_collect", function (data) {
        semanticPeriodicLog("semanticSocket.on.semantic_collect");
        applySemanticCollectPayload(data, "Socket.IO");
    });

    semanticSocket.on("mood_collect", function (data) {
        semanticPeriodicLog("semanticSocket.on.mood_collect");
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
        semanticPeriodicLog("startWhenGraphReady.graphReady", "attempts=" + String(attempts));
        if (typeof graph.setValues === "function") {
            graph.setValues(values);
        }
        loadDemoPayload();
        return;
    }
    if (attempts > 150) {
        semanticPeriodicLog("startWhenGraphReady.giveUpNoGraph", "attempts=" + String(attempts));
        loadDemoPayload();
        return;
    }
    if (attempts > 0 && attempts % 30 === 0) {
        semanticPeriodicLog("startWhenGraphReady.retry", String(attempts));
    }
    setTimeout(function () {
        startWhenGraphReady(attempts + 1);
    }, 40);
}

setTimeout(function () {
    semanticPeriodicLog("semantic3d.deferredBoot", "50ms");
    initGraph();
    wireDemoControls();
    wireForcePanelCollapse();
    wireForcePanelHotkey();
    wireForceSliders();
    initSemanticSocket();
    startWhenGraphReady(0);
}, 50);
