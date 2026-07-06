/**
 * Forward scenes hotkeys (a = autoswitch, n = next) to parent /scenes/ shell when embedded in iframe.
 */
(function () {
    if (window.parent === window) {
        return;
    }

    function isTypingTarget(el) {
        if (!el || !el.tagName) return false;
        var t = el.tagName;
        if (t === "INPUT" || t === "TEXTAREA" || t === "SELECT") return true;
        if (el.isContentEditable) return true;
        return false;
    }

    document.addEventListener("keydown", function (ev) {
        if (!ev || ev.defaultPrevented) return;
        if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
        if (isTypingTarget(ev.target)) return;

        var action = null;
        if (ev.key === "a" || ev.key === "A") {
            action = "toggle-autoswitch";
        } else if (ev.key === "n" || ev.key === "N") {
            action = "next-scene";
        }
        if (!action) return;

        ev.preventDefault();
        window.parent.postMessage({ type: "jamming-scenes-hotkey", action: action }, "*");
    });
})();
