/**
 * Post admin: show body stats (symbols, words, reading time) near the body field.
 * Counts only content inside the CKEditor editable area. Reading time: 200 words/min, min 1 min.
 * Symbol counts: with spaces (Telegram / SEO style) and without whitespace characters.
 */
(function() {
    'use strict';

    var qualityState = {
        lastText: '',
        response: null,
        debounceTimer: null,
        inFlight: false,
    };

    function enforceSpellcheck(container, bodyEl) {
        var lang = (document.documentElement && document.documentElement.lang) ? document.documentElement.lang : 'ru';
        function applySpellAttrs(node) {
            if (!node) return;
            if (node.getAttribute('spellcheck') !== 'true') node.setAttribute('spellcheck', 'true');
            if (node.getAttribute('lang') !== lang) node.setAttribute('lang', lang);
            if (node.getAttribute('autocapitalize') !== 'sentences') node.setAttribute('autocapitalize', 'sentences');
            if (node.getAttribute('autocorrect') !== 'on') node.setAttribute('autocorrect', 'on');
        }
        if (bodyEl) {
            applySpellAttrs(bodyEl);
        }
        if (!container) return;
        var editables = container.querySelectorAll('.ck-editor__editable, .ck-content, [contenteditable="true"]');
        editables.forEach(function(node) {
            applySpellAttrs(node);
        });
    }

    function observeEditorForSpellcheck(container, bodyEl) {
        if (!container || !window.MutationObserver) return;
        var observer = new MutationObserver(function() {
            enforceSpellcheck(container, bodyEl);
        });
        observer.observe(container, { childList: true, subtree: true });
    }

    function getBodyContentFromEditor(container) {
        var editable = container ? container.querySelector('.ck-editor__editable, .ck-content, [contenteditable="true"]') : null;
        if (editable) {
            return editable.innerHTML;
        }
        var ta = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        return ta ? ta.value : '';
    }

    function htmlToPlainText(html) {
        if (!html) return '';
        var div = document.createElement('div');
        div.innerHTML = html;
        var raw = div.textContent || div.innerText || '';
        return raw.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
    }

    function getStats(html, qualityData) {
        if (qualityData && qualityData.text_meta) {
            var meta = qualityData.text_meta;
            var words = meta.words || 0;
            return {
                symbolsWithSpaces: meta.characters || 0,
                symbolsNoSpaces: meta.characters_no_spaces || 0,
                words: words,
                minutes: Math.max(1, Math.round(meta.reading_time_minutes || words / 200)),
            };
        }
        var plain = htmlToPlainText(html);
        var words = plain ? plain.split(/\s+/).filter(Boolean).length : 0;
        return {
            symbolsWithSpaces: plain.length,
            symbolsNoSpaces: plain.replace(/ /g, '').length,
            words: words,
            minutes: Math.max(1, Math.round(words / 200)),
        };
    }

    function formatNum(n) {
        return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '\u202f');
    }

    function metricsBaseLine(s) {
        return 'Символов: <strong>' + formatNum(s.symbolsWithSpaces) + '</strong>' +
            ' (с пробелами) · без пробелов: <strong>' + formatNum(s.symbolsNoSpaces) + '</strong>' +
            ' · Слов: <strong>' + formatNum(s.words) + '</strong>' +
            ' · Время чтения: <strong>~' + s.minutes + '</strong> мин';
    }

    function metricsQualityLine(data) {
        if (!data || !data.overall || !data.scores) return '';
        var score = data.overall.score;
        var readability = data.scores.readability ? data.scores.readability.score : '-';
        var spamWords = data.scores.spam_words ? data.scores.spam_words.score : '-';
        var waterness = data.scores.waterness ? data.scores.waterness.score : '-';
        var orthography = data.scores.orthography ? data.scores.orthography.score : '-';
        var punctuation = data.scores.punctuation ? data.scores.punctuation.score : '-';
        var typos = data.scores.typos ? data.scores.typos.score : '-';
        return 'Качество текста: <strong>' + score + '</strong>' +
            ' · Читаемость: <strong>' + readability + '</strong>' +
            ' · Спам: <strong>' + spamWords + '</strong>' +
            ' · Водность: <strong>' + waterness + '</strong>' +
            ' · Орфография: <strong>' + orthography + '</strong>' +
            ' · Пунктуация: <strong>' + punctuation + '</strong>' +
            ' · Опечатки: <strong>' + typos + '</strong>';
    }

    function updateStatsEl(statsEl, s, qualityData) {
        if (!statsEl) return;
        var html = '<div class="post-body-stats__base">' + metricsBaseLine(s) + '</div>';
        if (qualityData) {
            html += '<div class="post-body-stats__quality">' + metricsQualityLine(qualityData) + '</div>';
        }
        statsEl.innerHTML = html;
    }

    function configuredQualityUrl() {
        var el = document.getElementById('post-admin-text-quality-url-data');
        if (!el || !el.textContent) return '';
        try {
            var url = JSON.parse(el.textContent);
            return typeof url === 'string' ? url : '';
        } catch (e) {
            return '';
        }
    }

    function adminQualityUrl(path) {
        var normalized = path.replace(/\/?$/, '/');
        if (/\/editor\/post\/[^/]+\/change\/$/.test(normalized)) {
            return normalized.replace(/\/[^/]+\/change\/$/, '/text-quality/');
        }
        if (/\/editor\/post\/add\/$/.test(normalized)) {
            return normalized.replace(/\/add\/$/, '/text-quality/');
        }
        return '';
    }

    function ensureTrailingSlash(url) {
        if (!url) return url;
        return url.charAt(url.length - 1) === '/' ? url : url + '/';
    }

    function getCookie(name) {
        var parts = document.cookie ? document.cookie.split(';') : [];
        for (var i = 0; i < parts.length; i++) {
            var c = parts[i].trim();
            if (c.indexOf(name + '=') === 0) {
                return decodeURIComponent(c.slice(name.length + 1));
            }
        }
        return '';
    }

    function requestQuality(statsEl, html) {
        if (qualityState.inFlight) return;
        var url = ensureTrailingSlash(
            configuredQualityUrl() || adminQualityUrl(window.location.pathname)
        );
        if (!url) return;
        qualityState.inFlight = true;
        fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                schema_version: '1.0',
                request_id: (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : String(Date.now()),
                locale: 'ru-RU',
                content_format: 'html',
                enable_extra_metrics: true,
                text: html
            })
        }).then(function(resp) {
            if (!resp.ok) return null;
            return resp.json();
        }).then(function(data) {
            if (!data || !data.ok) return;
            qualityState.response = data;
            var latestHtml = getBodyContentFromEditor(statsEl.parentElement);
            updateStatsEl(statsEl, getStats(latestHtml, qualityState.response), qualityState.response);
        }).catch(function() {
        }).finally(function() {
            qualityState.inFlight = false;
        });
    }

    function scheduleQuality(statsEl, html) {
        var plain = htmlToPlainText(html);
        if (plain === qualityState.lastText) return;
        qualityState.lastText = plain;
        if (qualityState.debounceTimer) clearTimeout(qualityState.debounceTimer);
        qualityState.debounceTimer = setTimeout(function() {
            requestQuality(statsEl, html);
        }, 1200);
    }

    function init() {
        var path = window.location.pathname;
        if (path.indexOf('/editor/post/') === -1) return;
        if (path.indexOf('/change/') === -1 && path.indexOf('/add/') === -1) return;

        var bodyEl = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        if (!bodyEl) return;

        var container = bodyEl.closest('.form-row') || bodyEl.closest('.field-body') || bodyEl.closest('[class*="field-body"]') || bodyEl.parentElement;
        if (!container) return;
        enforceSpellcheck(container, bodyEl);
        observeEditorForSpellcheck(container, bodyEl);

        var statsEl = document.createElement('div');
        statsEl.className = 'post-body-stats';
        statsEl.setAttribute('aria-live', 'polite');
        container.insertBefore(statsEl, container.firstChild);

        var editable = container.querySelector('.ck-editor__editable, .ck-content, [contenteditable="true"]');

        function refresh() {
            var html = getBodyContentFromEditor(container);
            var s = getStats(html, qualityState.response);
            updateStatsEl(statsEl, s, qualityState.response);
            scheduleQuality(statsEl, html);
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
