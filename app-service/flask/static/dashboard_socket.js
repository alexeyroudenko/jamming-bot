/**
 * Shared Socket.IO client: path behind ingress, ping/latency, socket event log + step timeline.
 * Loaded before bot.html inline script so `socket` and helpers are global.
 */
(function () {
    'use strict';

    // Engine.IO всегда с корня хоста (как на главной /). Не привязывать path к pathname
    // страниц вроде /events/ — иначе получится /events/socket.io → 404.
    var socketPath = '/socket.io';

    window.socket = window.io({ path: socketPath });

    var socket = window.socket;

    var counter = 0;
    var start_time = new Date().getTime();
    var pingInterval = null;

    window.logsBuffer = [];
    var logsBuffer = window.logsBuffer;
    var MAX_LOG_EVENTS = 200;
    var STEP_TIMELINE_DURATION_MS = 10000;
    window.stepTimelineState = {
        step: null,
        startedAt: null,
        events: []
    };
    var stepTimelineState = window.stepTimelineState;
    var stepTimelineCursorFrame = null;

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
    window.escapeHtml = escapeHtml;

    function classifySocketEvent(eventName) {
        switch (eventName) {
        case 'event':
        case 'step':
        case 'sublink':
        case 'clear':
        case 'steps_forwards':
            return 'bot';
        case 'analyzed':
        case 'tags_updated':
            return 'analyzer';
        case 'screenshot':
        case 'image_analyzed':
            return 'screenshoter';
        case 'location':
            return 'geo';
        case 'set':
        case 'set_values':
            return 'controls';
        default:
            return 'system';
        }
    }

    function summarizeSocketEvent(eventName, payload) {
        if (eventName === 'connect') return 'socket connected';
        if (eventName === 'disconnect') return 'socket disconnected';
        if (eventName === 'clear') return 'clear state';
        if (eventName === 'my_pong') return 'latency ' + String(payload && payload.latency_ms != null ? payload.latency_ms : '—') + 'ms';
        if (eventName === 'event') return String((payload && payload.event) || 'event');
        if (eventName === 'steps_forwards') return 'steps ' + String(payload && payload.value != null ? payload.value : payload);
        if (eventName === 'sublink') return String((payload && payload.url) || 'sublink');
        if (eventName === 'step') {
            return '#' + String(payload && payload.step != null ? payload.step : '—') + ' ' +
                String((payload && payload.status_code) || '—') + ' ' +
                String((payload && payload.url) || '');
        }
        if (eventName === 'analyzed') {
            var wordsCount = Array.isArray(payload && payload.words) ? payload.words.length : 0;
            var phraseCount = Array.isArray(payload && payload.noun_phrases) ? payload.noun_phrases.length : 0;
            return 'words=' + String(wordsCount) + ' noun_phrases=' + String(phraseCount);
        }
        if (eventName === 'screenshot') {
            return payload && payload.screenshot_url ? String(payload.screenshot_url) : 'screenshot ready';
        }
        if (eventName === 'image_analyzed') {
            var paletteCount = Array.isArray(payload && payload.palette) ? payload.palette.length : 0;
            return 'palette=' + String(paletteCount);
        }
        if (eventName === 'set_values' || eventName === 'set') {
            if (!payload || typeof payload !== 'object') return 'values updated';
            var keys = Object.keys(payload).slice(0, 3);
            return keys.length ? keys.map(function (key) {
                return key + '=' + String(payload[key]);
            }).join(' ') : 'values updated';
        }
        if (eventName === 'location') {
            if (!payload || typeof payload !== 'object') return 'geo resolved';
            return String(payload.country || payload.city || payload.ip || 'geo resolved');
        }
        if (eventName === 'tags_updated') return 'tags refreshed';
        if (eventName === 'response') return String((payload && payload.message) || 'response');
        return typeof payload === 'string' ? payload : eventName;
    }

    function renderStepTimeline() {
        var trackEl = document.getElementById('step-timeline-track');
        var cursorEl = document.getElementById('step-timeline-cursor');
        var metaEl = document.getElementById('step-timeline-meta');
        var captionEl = document.getElementById('step-timeline-caption');
        if (!trackEl || !cursorEl || !metaEl || !captionEl) return;

        if (stepTimelineState.step == null || !stepTimelineState.startedAt) {
            metaEl.textContent = 'Waiting for step...';
            trackEl.innerHTML = '<div class="bot-step-timeline-empty">Waiting for step...</div><div id="step-timeline-cursor" class="bot-step-timeline-cursor" hidden></div>';
            captionEl.innerHTML = '<span>step -</span><span>0 events</span>';
            updateStepTimelineCursor();
            return;
        }

        metaEl.textContent = 'step #' + String(stepTimelineState.step) + ' • 10s window';
        captionEl.textContent = 'step ' + String(stepTimelineState.step) + ' • ' + String(stepTimelineState.events.length) + ' events';

        if (!stepTimelineState.events.length) {
            trackEl.innerHTML = '<div class="bot-step-timeline-empty">Waiting for events inside the current 10s step window...</div><div id="step-timeline-cursor" class="bot-step-timeline-cursor" hidden></div>';
            updateStepTimelineCursor();
            return;
        }

        var segmentsHtml = stepTimelineState.events.map(function (entry, index) {
            var summary = escapeHtml(entry.summary || entry.event || 'event');
            var eventName = escapeHtml(entry.event || 'event');
            var typeName = escapeHtml(entry.type || 'system');
            var elapsedMs = Math.max(0, Math.round(entry.elapsedMs || 0));
            var title = eventName + ' • ' + elapsedMs + 'ms • ' + summary;
            var classes = 'bot-step-timeline-segment type-' + typeName + (entry.overflow ? ' is-overflow' : '');
            var previousEntry = stepTimelineState.events[index - 1] || null;
            var startLeft = previousEntry ? previousEntry.left : 0;
            var width = Math.max(entry.left - startLeft, entry.width || 0.35);
            return '<span class="' + classes + '" style="left:' + startLeft + '%;width:' + width + '%" title="' + escapeHtml(title) + '"></span>';
        }).join('');
        trackEl.innerHTML = segmentsHtml + '<div id="step-timeline-cursor" class="bot-step-timeline-cursor" hidden></div>';
        updateStepTimelineCursor();
    }
    window.renderStepTimeline = renderStepTimeline;

    function updateStepTimelineCursor() {
        var cursorEl = document.getElementById('step-timeline-cursor');
        if (!cursorEl) {
            return;
        }
        if (stepTimelineState.step == null || !stepTimelineState.startedAt) {
            cursorEl.hidden = true;
            return;
        }
        var elapsedMs = Math.max(0, Date.now() - stepTimelineState.startedAt);
        var clampedMs = Math.min(elapsedMs, STEP_TIMELINE_DURATION_MS);
        var left = (clampedMs / STEP_TIMELINE_DURATION_MS) * 100;
        cursorEl.hidden = false;
        cursorEl.style.left = left + '%';
    }
    window.updateStepTimelineCursor = updateStepTimelineCursor;

    function startStepTimelineCursorLoop() {
        if (stepTimelineCursorFrame !== null) {
            cancelAnimationFrame(stepTimelineCursorFrame);
        }
        function tick() {
            updateStepTimelineCursor();
            stepTimelineCursorFrame = requestAnimationFrame(tick);
        }
        stepTimelineCursorFrame = requestAnimationFrame(tick);
    }
    window.startStepTimelineCursorLoop = startStepTimelineCursorLoop;

    function resetStepTimeline(stepNumber, startedAt) {
        stepTimelineState.step = stepNumber == null ? null : stepNumber;
        stepTimelineState.startedAt = startedAt || Date.now();
        stepTimelineState.events = [];
        renderStepTimeline();
    }
    window.resetStepTimeline = resetStepTimeline;

    function clearStepTimeline() {
        stepTimelineState.step = null;
        stepTimelineState.startedAt = null;
        stepTimelineState.events = [];
        renderStepTimeline();
    }
    window.clearStepTimeline = clearStepTimeline;

    function appendTimelineEvent(eventName, payload, forcedType, eventTime) {
        if (eventName === 'step' || !stepTimelineState.startedAt) {
            return;
        }

        var timestamp = typeof eventTime === 'number' ? eventTime : Date.now();
        var elapsedMs = Math.max(0, timestamp - stepTimelineState.startedAt);
        var clampedMs = Math.min(elapsedMs, STEP_TIMELINE_DURATION_MS);
        var left = (clampedMs / STEP_TIMELINE_DURATION_MS) * 100;
        var width = 0.35;
        var maxLeft = Math.max(100 - width, 0);
        var timelineType = forcedType || classifySocketEvent(eventName);

        stepTimelineState.events.push({
            event: eventName,
            type: timelineType,
            summary: summarizeSocketEvent(eventName, payload),
            elapsedMs: elapsedMs,
            left: Math.min(left, maxLeft),
            width: width,
            overflow: elapsedMs > STEP_TIMELINE_DURATION_MS
        });
        renderStepTimeline();
    }

    function pushSocketLog(eventName, payload, forcedType) {
        var eventTime = Date.now();
        var entry = {
            time: new Date(eventTime),
            type: forcedType || classifySocketEvent(eventName),
            event: eventName,
            summary: summarizeSocketEvent(eventName, payload),
            payload: payload
        };
        logsBuffer.unshift(entry);
        if (logsBuffer.length > MAX_LOG_EVENTS) {
            logsBuffer.length = MAX_LOG_EVENTS;
        }
        renderLogs();
        appendTimelineEvent(eventName, payload, forcedType, eventTime);
    }
    window.pushSocketLog = pushSocketLog;

    function formatLogTime(value) {
        if (!(value instanceof Date)) {
            return '--:--:--';
        }
        return value.toLocaleTimeString([], { hour12: false });
    }

    function payloadPreview(payload) {
        if (payload == null) return '';
        if (typeof payload === 'string') return payload;
        try {
            var raw = JSON.stringify(payload);
            return raw.length > 280 ? raw.slice(0, 277) + '...' : raw;
        } catch (error) {
            return '[payload]';
        }
    }

    function renderLogs() {
        var listEl = document.getElementById('logs-list');
        var metaEl = document.getElementById('logs-meta');
        if (!listEl || !metaEl) return;

        metaEl.textContent = String(logsBuffer.length) + ' events';

        if (!logsBuffer.length) {
            listEl.innerHTML = '<div class="bot-logs-empty">Waiting for socket events...</div>';
            return;
        }

        var head = [
            '<div class="bot-logs-row is-head">',
            '<span>time</span>',
            '<span>type</span>',
            '<span>event</span>',
            '<span>summary</span>',
            '</div>'
        ].join('');

        var rows = logsBuffer.map(function (entry) {
            var time = escapeHtml(formatLogTime(entry.time));
            var type = escapeHtml(entry.type || 'system');
            var event = escapeHtml(entry.event || 'event');
            var summary = escapeHtml(entry.summary || '');
            var preview = escapeHtml(payloadPreview(entry.payload));
            return [
                '<div class="bot-logs-row" title="' + preview + '">',
                '<span>' + time + '</span>',
                '<span class="bot-logs-type type-' + type + '">' + type + '</span>',
                '<span class="bot-logs-event">' + event + '</span>',
                '<span class="bot-logs-summary">' + summary + '</span>',
                '</div>'
            ].join('');
        }).join('');

        listEl.innerHTML = head + rows;
    }
    window.renderLogs = renderLogs;

    function setCounterLatencyText(latencyStr, counterStr) {
        var latEl = document.getElementById('latency');
        var cntEl = document.getElementById('counter');
        if (latEl) latEl.textContent = latencyStr;
        if (cntEl) cntEl.textContent = counterStr;
    }

    socket.on('connect', function () {
        console.log('on connect');
        pushSocketLog('connect', { sid: socket.id }, 'system');
        if (pingInterval) {
            clearInterval(pingInterval);
            pingInterval = null;
        }
        pingInterval = window.setInterval(function () {
            counter += 1;
            start_time = new Date().getTime();
            socket.emit('my_ping');
        }, 250);
    });

    socket.on('disconnect', function () {
        if (pingInterval) {
            clearInterval(pingInterval);
            pingInterval = null;
        }
        pushSocketLog('disconnect', { sid: socket.id }, 'system');
        console.log('Disconnected from server');
    });

    socket.on('response', function (data) {
        pushSocketLog('response', data, 'system');
    });

    socket.on('set', function (data) {
        pushSocketLog('set', data, 'controls');
    });

    socket.on('steps_forwards', function (data) {
        pushSocketLog('steps_forwards', { value: data }, 'bot');
    });

    socket.on('tags_updated', function (data) {
        pushSocketLog('tags_updated', data || {}, 'analyzer');
    });

    socket.on('location', function (data) {
        pushSocketLog('location', data, 'geo');
    });

    socket.on('event', function (data) {
        pushSocketLog('event', data, 'bot');
    });

    socket.on('sublink', function (data) {
        pushSocketLog('sublink', data, 'bot');
    });

    socket.on('clear', function (data) {
        pushSocketLog('clear', data, 'bot');
        clearStepTimeline();
    });

    socket.on('step', function (data) {
        pushSocketLog('step', data, 'bot');
        var step = data && data.step;
        resetStepTimeline(step, Date.now());
    });

    socket.on('screenshot', function (data) {
        pushSocketLog('screenshot', data, 'screenshoter');
    });

    socket.on('image_analyzed', function (data) {
        pushSocketLog('image_analyzed', data, 'screenshoter');
    });

    socket.on('set_values', function (data) {
        pushSocketLog('set_values', data, 'controls');
    });

    socket.on('analyzed', function (data) {
        pushSocketLog('analyzed', data, 'analyzer');
    });

    socket.on('my_pong', function () {
        var latency = new Date().getTime() - start_time;
        var latencyStr = String(latency).padStart(4, '0');
        var counterStr = String(counter).padStart(4, '0');
        setCounterLatencyText(latencyStr, counterStr);
        if (window.jQuery) {
            window.jQuery('#latency').html(latencyStr);
            window.jQuery('#counter').html(counterStr);
        }
    });

    function bootCursor() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', startStepTimelineCursorLoop);
        } else {
            startStepTimelineCursorLoop();
        }
    }
    bootCursor();
})();
