/* Semantic pages: S toggles div-hidden on force panel, demo meta, mood log. */
(function () {
    "use strict";

    var SEMANTIC_UI_HIDDEN_LS = "jammingSemanticUiHidden";

    function loadSemanticUiHiddenDefaultTrue() {
        try {
            var v = localStorage.getItem(SEMANTIC_UI_HIDDEN_LS);
            if (v === null || v === undefined) {
                return true;
            }
            return v === "1" || v === "true";
        } catch (e) {
            return true;
        }
    }

    function saveSemanticUiHidden(hidden) {
        try {
            localStorage.setItem(SEMANTIC_UI_HIDDEN_LS, hidden ? "1" : "0");
        } catch (e) {
            /* ignore */
        }
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

    function applySemanticUiHidden(hidden) {
        var panel = document.getElementById("semantic-force-panel");
        var mood = document.getElementById("log_mood");
        var metas = document.querySelectorAll(".semantic-demo-meta");
        function setEl(el) {
            if (!el) {
                return;
            }
            if (hidden) {
                el.classList.add("div-hidden");
            } else {
                el.classList.remove("div-hidden");
            }
        }
        setEl(panel);
        setEl(mood);
        for (var i = 0; i < metas.length; i++) {
            setEl(metas[i]);
        }
    }

    function wireSemanticOverlayHotkey() {
        applySemanticUiHidden(loadSemanticUiHiddenDefaultTrue());
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
            var panel = document.getElementById("semantic-force-panel");
            if (!panel) {
                return;
            }
            ev.preventDefault();
            var hidden = panel.classList.contains("div-hidden");
            applySemanticUiHidden(!hidden);
            saveSemanticUiHidden(!hidden);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", wireSemanticOverlayHotkey);
    } else {
        wireSemanticOverlayHotkey();
    }
})();
