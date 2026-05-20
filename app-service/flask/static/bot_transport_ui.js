(function () {
    "use strict";

    function getIo() {
        return typeof window !== "undefined" ? window.io : undefined;
    }

    var FLASH_MS = 50;

    function ensureInjectFlashStyles() {
        if (document.getElementById("jb-inject-flash-style")) {
            return;
        }
        var style = document.createElement("style");
        style.id = "jb-inject-flash-style";
        style.textContent =
            "#inject-flash-overlay{position:fixed;inset:0;z-index:2147483647;background:#fff;opacity:0;visibility:hidden;pointer-events:none}" +
            "#inject-flash-overlay.is-active{opacity:1;visibility:visible}";
        document.head.appendChild(style);
    }

    function ensureInjectFlashOverlay() {
        ensureInjectFlashStyles();
        var el = document.getElementById("inject-flash-overlay");
        if (el) {
            return el;
        }
        el = document.createElement("div");
        el.id = "inject-flash-overlay";
        el.setAttribute("aria-hidden", "true");
        document.body.appendChild(el);
        return el;
    }

    function flashInjectWhite() {
        var el = ensureInjectFlashOverlay();
        el.classList.remove("is-active");
        void el.offsetWidth;
        el.classList.add("is-active");
        if (el._jbFlashTimer) {
            clearTimeout(el._jbFlashTimer);
        }
        el._jbFlashTimer = setTimeout(function () {
            el.classList.remove("is-active");
        }, FLASH_MS);
    }

    function syncInjectActiveClass(state) {
        var on = state === "Injected";
        document.documentElement.classList.toggle("inject-active", on);
    }

    function setBotTransportState(state) {
        var label = state || "Stopped";
        var prev = window._lastBotTransportState;
        if (label === "Injected" && prev !== "Injected") {
            flashInjectWhite();
        }
        syncInjectActiveClass(label);
        if (prev !== label) {
            window._lastBotTransportState = label;
            console.log("[jamming-bot] State:", label);
        }
        var el = document.getElementById("metric-bot-state");
        if (el) {
            el.textContent = label;
            el.dataset.state = String(label).toLowerCase();
        }
    }

    function attachTransportSocketListeners(socket) {
        if (!socket || socket.__jbTransportUi) {
            return;
        }
        socket.__jbTransportUi = true;
        socket.on("bot_transport_state", function (data) {
            if (data && data.state) {
                setBotTransportState(data.state);
            }
        });
        socket.on("inject_begin", function () {
            setBotTransportState("Injected");
        });
        socket.on("inject_end", function () {
            setBotTransportState("Active");
        });
    }

    function patchIo() {
        var orig = getIo();
        if (typeof orig !== "function") {
            return false;
        }
        if (orig.__jbTransportPatched) {
            return true;
        }
        function wrapped() {
            var s = orig.apply(this, arguments);
            attachTransportSocketListeners(s);
            return s;
        }
        var k;
        for (k in orig) {
            if (Object.prototype.hasOwnProperty.call(orig, k)) {
                wrapped[k] = orig[k];
            }
        }
        wrapped.__jbTransportPatched = true;
        wrapped.Manager = orig.Manager;
        wrapped.Socket = orig.Socket;
        window.io = wrapped;
        return true;
    }

    window.flashInjectWhite = flashInjectWhite;
    window.setBotTransportState = setBotTransportState;
    window.jbAttachTransportSocket = attachTransportSocketListeners;

    if (!patchIo()) {
        var tries = 0;
        var wait = setInterval(function () {
            if (patchIo() || ++tries > 120) {
                clearInterval(wait);
            }
        }, 50);
    }
})();
