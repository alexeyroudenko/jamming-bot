/**
 * Подбор font-size у контейнера, чтобы содержимое помещалось в clientWidth/clientHeight.
 * Контейнер должен иметь ограниченную высоту (например flex:1; min-height:0; overflow:hidden).
 */
(function (global) {
    'use strict';

    function fitFontToBox(el, options) {
        if (!el || !el.isConnected) return;
        var opt = options || {};
        var minPx = opt.minPx != null ? opt.minPx : 10;
        var maxPx = opt.maxPx != null ? opt.maxPx : 160;
        var tol = opt.tolerance != null ? opt.tolerance : 2;

        var ch = el.clientHeight;
        var cw = el.clientWidth;
        if (ch < 12 || cw < 12) return;

        var low = minPx;
        var high = maxPx;
        var best = minPx;
        var guard = 0;

        while (low <= high + 0.25 && guard < 48) {
            guard += 1;
            var mid = (low + high) / 2;
            el.style.fontSize = mid + 'px';
            var overY = el.scrollHeight > ch + tol;
            var overX = el.scrollWidth > cw + tol;
            if (!overY && !overX) {
                best = mid;
                low = mid + 0.5;
            } else {
                high = mid - 0.5;
            }
        }
        el.style.fontSize = best + 'px';
    }

    var rafById = Object.create(null);

    function schedule(el, options) {
        if (!el || typeof el !== 'object') return;
        var key = el.id || el._jbFitKey || (el._jbFitKey = 'k' + String(Math.random()).slice(2));
        if (rafById[key]) cancelAnimationFrame(rafById[key]);
        rafById[key] = requestAnimationFrame(function () {
            rafById[key] = null;
            fitFontToBox(el, options);
        });
    }

    function debounce(el, options, ms) {
        var wait = ms != null ? ms : 80;
        var key = el.id || el._jbFitDebounceKey || (el._jbFitDebounceKey = 'd' + String(Math.random()).slice(2));
        if (el._jbFitDebounceTimer) clearTimeout(el._jbFitDebounceTimer);
        el._jbFitDebounceTimer = setTimeout(function () {
            el._jbFitDebounceTimer = null;
            schedule(el, options);
        }, wait);
    }

    global.jbPageViewFit = {
        fit: fitFontToBox,
        schedule: schedule,
        debounce: debounce
    };
})(typeof window !== 'undefined' ? window : this);
