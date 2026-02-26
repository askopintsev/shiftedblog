/**
 * Post admin: show body stats (symbols, words, reading time) near the body field.
 * Counts only content inside the CKEditor editable area. Reading time: 200 words/min, min 1 min.
 */
(function() {
    'use strict';

    function getBodyContentFromEditor(container) {
        var editable = container ? container.querySelector('.ck-editor__editable, .ck-content, [contenteditable="true"]') : null;
        if (editable) {
            return editable.innerHTML;
        }
        var ta = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        return ta ? ta.value : '';
    }

    function stripHtml(html) {
        if (!html) return '';
        var div = document.createElement('div');
        div.innerHTML = html;
        return (div.textContent || div.innerText || '').replace(/\s+/g, ' ').trim();
    }

    function getStats(html) {
        var plain = stripHtml(html);
        var symbols = plain.length;
        var words = plain ? plain.split(/\s+/).filter(Boolean).length : 0;
        var minutes = Math.max(1, Math.round(words / 200));
        return { symbols: symbols, words: words, minutes: minutes };
    }

    function formatNum(n) {
        return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '\u202f');
    }

    function updateStatsEl(statsEl, s) {
        if (!statsEl) return;
        statsEl.innerHTML =
            'Символов: <strong>' + formatNum(s.symbols) + '</strong>' +
            ' · Слов: <strong>' + formatNum(s.words) + '</strong>' +
            ' · Время чтения: <strong>~' + s.minutes + '</strong> мин';
    }

    function init() {
        var path = window.location.pathname;
        if (path.indexOf('/editor/post/') === -1 || path.indexOf('/change/') === -1) return;

        var bodyEl = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        if (!bodyEl) return;

        var container = bodyEl.closest('.form-row') || bodyEl.closest('.field-body') || bodyEl.closest('[class*="field-body"]') || bodyEl.parentElement;
        if (!container) return;

        var statsEl = document.createElement('div');
        statsEl.className = 'post-body-stats';
        statsEl.setAttribute('aria-live', 'polite');
        container.insertBefore(statsEl, container.firstChild);

        var editable = container.querySelector('.ck-editor__editable, .ck-content, [contenteditable="true"]');

        function refresh() {
            var html = getBodyContentFromEditor(container);
            var s = getStats(html);
            updateStatsEl(statsEl, s);
        }

        refresh();

        if (editable) {
            editable.addEventListener('input', refresh);
            editable.addEventListener('blur', refresh);
        }
        bodyEl.addEventListener('input', refresh);
        bodyEl.addEventListener('change', refresh);
        setInterval(refresh, 1500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(init, 1500);
        });
    } else {
        setTimeout(init, 1500);
    }
})();
