/* global d3, $, io */
/* Jamming Bot D3 force graph (same behavior as bot.html myGraph) + semantic.txt replay */

var SEMANTIC_FORCE_LS = "jammingSemanticForceParams";

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

var zoom;
var container;

function zoomed() {
    container.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
}

var graph;

function myGraph() {
    var nodes = [];
    var links = [];

    this.getNodes = function () {
        return nodes;
    };

    this.addNode = function (id, step, r) {
        if (r === undefined) r = 6;
        nodes.push({ id: id, step: step, r: r });
        update();
        return id;
    };

    this.removeNode = function (id) {
        if (this.findNodeIndex(id) < 0) return;
        var i = 0;
        var n = findNode(id);
        if (!n) return;
        while (i < links.length) {
            if (links[i].source.id === id || links[i].target.id === id) {
                links.splice(i, 1);
            } else {
                i += 1;
            }
        }
        var idx = this.findNodeIndex(id);
        if (idx !== undefined && idx >= 0) {
            nodes.splice(idx, 1);
        }
        update();
    };

    this.removeLink = function (source, target) {
        for (var i = 0; i < links.length; i++) {
            if (links[i].source.id === source && links[i].target.id === target) {
                links.splice(i, 1);
                break;
            }
        }
        update();
    };

    this.removeallLinks = function () {
        links.splice(0, links.length);
        update();
    };

    this.removeAllNodes = function () {
        nodes.splice(0, nodes.length);
        update();
    };

    this.addLink = function (source, target, value) {
        var s = findNode(source);
        var t = findNode(target);
        if (!s || !t) return;
        links.push({ source: s, target: t, value: value });
        update();
    };

    this.findNode = function (id) {
        for (var i in nodes) {
            if (nodes[i].id === id) return nodes[i];
        }
    };

    this.removeLinksForNode = function (node_id) {
        var i = 0;
        while (i < links.length) {
            if (links[i].source.id === node_id || links[i].target.id === node_id) {
                links.splice(i, 1);
            } else {
                i += 1;
            }
        }
        update();
    };

    var findNode = function (id) {
        for (var j in nodes) {
            if (nodes[j].id === id) return nodes[j];
        }
    };

    this.findNodeIndex = function (id) {
        for (var k = 0; k < nodes.length; k++) {
            if (nodes[k].id === id) {
                return k;
            }
        }
        return -1;
    };

    var w = window.innerWidth;
    var h = window.innerHeight;

    function isMobile() {
        return /Mobi|Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    function isIPhone() {
        return /iPhone/.test(navigator.userAgent);
    }

    var scale = 1;
    if (isMobile()) {
        scale = isIPhone() && w <= 428 ? 1.0 : 1.2;
    }

    var vis = d3.select("body")
        .append("svg:svg")
        .attr("width", Math.floor(w * scale))
        .attr("height", Math.floor(h * scale))
        .attr("id", "svg")
        .attr("pointer-events", "all")
        .attr("viewBox", "0 0 " + Math.floor(w * scale) + " " + Math.floor(h * scale))
        .attr("perserveAspectRatio", "xMinYMid");

    container = vis.append("g");

    zoom = d3.behavior.zoom()
        .scaleExtent([0.1, 10])
        .on("zoom", zoomed);

    vis.call(zoom)
        .on("mousedown.zoom", null)
        .on("touchstart.zoom", null)
        .on("touchmove.zoom", null)
        .on("touchend.zoom", null);

    d3.select("body").append("button")
        .attr("class", "semantic-zoom-minus")
        .attr("type", "button")
        .text("-")
        .on("click", function () {
            zoom.scale(zoom.scale() / 1.2);
            zoom.event(vis.transition().duration(500));
        });

    var force;

    function resize() {
        w = window.innerWidth;
        h = window.innerHeight;
        if (isMobile()) {
            scale = isIPhone() && w <= 428 ? 1.0 : 1.2;
        } else {
            scale = 1.0;
        }
        vis.attr("width", Math.floor(w * scale)).attr("height", Math.floor(h * scale))
            .attr("viewBox", "0 0 " + Math.floor(w * scale) + " " + Math.floor(h * scale));
        if (force && typeof applyForceLayoutParameters === "function") {
            applyForceLayoutParameters();
        }
    }

    window.addEventListener("resize", resize);
    resize();

    force = d3.layout.force();
    nodes = force.nodes();
    links = force.links();

    function applyForceLayoutParameters() {
        var linkMultiplier = getLinkDistanceMultiplier();
        force.linkDistance(function (d) { return d.value * 13 * values.v1 * 4 * linkMultiplier; })
            .gravity(0.01 * values.v2 * 4)
            .charge(-80000 * values.v3 * 4)
            .linkStrength(values.v4)
            .friction(0.004 * values.v5 * 4);
        if (typeof force.theta === "function") {
            force.theta(values.theta);
        }
        if (typeof force.chargeDistance === "function") {
            var cd = values.chargeDist;
            force.chargeDistance(cd >= 8000 ? Infinity : cd);
        }
        force.size([w, h]).start();
    }

    var update = function () {
        links = force.links();

        var link = container.selectAll("line")
            .data(links, function (d) {
                return d.source.id + "-" + d.target.id;
            });

        link.enter().append("line")
            .attr("id", function (d) {
                if (d.source && d.target) {
                    return d.source.id + "-" + d.target.id;
                }
            })
            .attr("stroke-width", function (d) {
                return d.value / 1;
            })
            .attr("class", "link");

        link.append("title")
            .text(function (d) {
                return d.value;
            });

        link.exit().remove();

        var node = container.selectAll("g.node")
            .data(nodes, function (d) {
                return d.id;
            });

        var customDrag = force.drag()
            .on("dragstart", function () {
                d3.event.sourceEvent.stopPropagation();
                if (d3.event.sourceEvent.type === "touchstart") {
                    d3.event.sourceEvent.preventDefault();
                }
            })
            .on("drag", function () {
                d3.event.sourceEvent.stopPropagation();
                if (d3.event.sourceEvent.type === "touchmove") {
                    d3.event.sourceEvent.preventDefault();
                }
            })
            .on("dragend", function () {
                d3.event.sourceEvent.stopPropagation();
                if (d3.event.sourceEvent.type === "touchend") {
                    d3.event.sourceEvent.preventDefault();
                }
            });

        var nodeEnter = node.enter().append("g")
            .attr("class", "node")
            .call(customDrag);

        var nodeSizeMultiplier = isMobile() && w <= 428 ? 0.8 : 1.2;

        nodeEnter.append("svg:circle")
            .attr("r", function (d) { return d.r * nodeSizeMultiplier; })
            .attr("id", function (d) { return "Node;" + d.id; })
            .attr("class", "nodeStrokeClass");

        var textX = isMobile() && w <= 428 ? 27 : 37;

        nodeEnter.append("svg:text")
            .attr("class", "textClass")
            .attr("x", textX)
            .attr("y", ".31em")
            .text(function (d) {
                return d.id;
            });

        node.call(customDrag);
        node.exit().remove();

        force.on("tick", function () {
            node.attr("transform", function (d) {
                return "translate(" + d.x + "," + d.y + ")";
            });
            link.attr("x1", function (d) { return d.source.x; })
                .attr("y1", function (d) { return d.source.y; })
                .attr("x2", function (d) { return d.target.x; })
                .attr("y2", function (d) { return d.target.y; });
        });

        applyForceLayoutParameters();
    };

    this.setValues = function (v) {
        values = mergeForceDefaults(v);
        applyForceLayoutParameters();
    };

    update();
    this.upd = function () {
        update();
    };
}

function keepNodesOnTop() {
    $(".nodeStrokeClass").each(function () {
        var gnode = this.parentNode;
        gnode.parentNode.appendChild(gnode);
    });
}

var graphInitAttempts = 0;
var maxGraphInitAttempts = 50;

function initGraph() {
    if (typeof d3 === "undefined") {
        graphInitAttempts += 1;
        if (graphInitAttempts >= maxGraphInitAttempts) {
            console.error("d3.js failed to load.");
            return;
        }
        setTimeout(initGraph, 100);
        return;
    }
    graph = new myGraph();
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
    // Same server as bot, but page lives under /semantic/ — Socket.IO stays at app root.
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
            }
            startSemanticLastCollectPoll();
        })
        .catch(function (err) {
            console.error(err);
            var el = document.getElementById("semantic-status");
            if (el) el.textContent = "load failed";
        });
}

setTimeout(function () {
    initGraph();
    wireDemoControls();
    wireForceSliders();
    initSemanticSocket();
    if (graph && typeof graph.setValues === "function") {
        graph.setValues(values);
    }
    loadDemoPayload();
}, 50);
