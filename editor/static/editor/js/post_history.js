/**
 * Post admin: list autosave history snapshots and restore into the editor form.
 */
(function () {
    'use strict';

    var BODY_FIELD_ID = 'id_body';

    function getHistoryListUrl() {
        var el = document.getElementById('post-admin-history-list-url-data');
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    function historyDetailUrl(listUrl, historyId) {
        if (!listUrl) return null;
        return listUrl.replace(/\/?$/, '/') + String(historyId) + '/';
    }

    function formatTimestamp(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        if (Number.isNaN(d.getTime())) return iso;
        var pad = function (n) { return n < 10 ? '0' + n : String(n); };
        return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
            ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    }

    function setFieldValue(name, value) {
        var el = document.getElementById('id_' + name) || document.querySelector('[name="' + name + '"]');
        if (!el) return;
        el.value = value == null ? '' : value;
        try {
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (err) {}
    }

    function setBodyContent(html) {
        var editors = window.editors;
        if (editors && editors[BODY_FIELD_ID] && typeof editors[BODY_FIELD_ID].setData === 'function') {
            editors[BODY_FIELD_ID].setData(html || '');
            return;
        }
        setFieldValue('body', html || '');
    }

    function applySnapshot(snapshot) {
        if (!snapshot) return;
        setFieldValue('title', snapshot.title || '');
        setFieldValue('short_description', snapshot.short_description || '');
        setBodyContent(snapshot.body || '');
    }

    function setStatus(text, isError) {
        var node = document.getElementById('post-history-status');
        if (!node) return;
        node.textContent = text || '';
        node.className = 'post-history-panel__status' + (isError ? ' post-history-panel__status--error' : '');
    }

    function updateSummaryCount(count) {
        var summary = document.querySelector('#post-history-panel .post-history-panel__summary');
        if (!summary) return;
        summary.textContent = count > 0
            ? 'Autosave history (' + count + ')'
            : 'Autosave history';
    }

    function renderList(items) {
        var list = document.getElementById('post-history-list');
        if (!list) return;
        list.innerHTML = '';
        if (!items || !items.length) {
            var empty = document.createElement('li');
            empty.className = 'post-history-list__empty';
            empty.textContent = 'No autosave history yet.';
            list.appendChild(empty);
            updateSummaryCount(0);
            return;
        }
        updateSummaryCount(items.length);
        items.forEach(function (item) {
            var li = document.createElement('li');
            li.className = 'post-history-list__item';

            var meta = document.createElement('div');
            meta.className = 'post-history-list__meta';
            meta.textContent = formatTimestamp(item.created_at);

            var preview = document.createElement('div');
            preview.className = 'post-history-list__preview';
            preview.textContent = item.preview || '';

            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'button post-history-list__restore';
            btn.textContent = 'Restore';
            btn.addEventListener('click', function () {
                restoreEntry(item.id, btn);
            });

            li.appendChild(meta);
            li.appendChild(preview);
            li.appendChild(btn);
            list.appendChild(li);
        });
    }

    function restoreEntry(historyId, btn) {
        var listUrl = getHistoryListUrl();
        var url = historyDetailUrl(listUrl, historyId);
        if (!url) return;
        if (!window.confirm(
            'Restore this autosave snapshot into the editor? Unsaved changes in the form will be replaced.'
        )) {
            return;
        }
        if (btn) {
            btn.disabled = true;
        }
        setStatus('Loading snapshot…', false);
        fetch(url, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (resp) {
            return resp.json().then(function (data) {
                return { ok: resp.ok, data: data };
            });
        }).then(function (result) {
            if (!result.ok || !result.data || !result.data.ok) {
                throw new Error((result.data && result.data.error) || 'Restore failed.');
            }
            applySnapshot(result.data.snapshot);
            setStatus('Snapshot restored into the editor. Save the post to persist.', false);
        }).catch(function (err) {
            setStatus(err && err.message ? err.message : 'Restore failed.', true);
        }).finally(function () {
            if (btn) {
                btn.disabled = false;
            }
        });
    }

    var historyLoaded = false;
    var historyLoading = false;

    function loadHistory() {
        var listUrl = getHistoryListUrl();
        var panel = document.getElementById('post-history-panel');
        if (!listUrl || !panel || historyLoading || historyLoaded) return;

        historyLoading = true;
        setStatus('Loading history…', false);

        fetch(listUrl, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (resp) {
            return resp.json().then(function (data) {
                return { ok: resp.ok, data: data };
            });
        }).then(function (result) {
            if (!result.ok || !result.data || !result.data.ok) {
                throw new Error((result.data && result.data.error) || 'Could not load history.');
            }
            renderList(result.data.items || []);
            setStatus('', false);
            historyLoaded = true;
        }).catch(function (err) {
            renderList([]);
            setStatus(err && err.message ? err.message : 'Could not load history.', true);
        }).finally(function () {
            historyLoading = false;
        });
    }

    function setupPanelToggle() {
        var panel = document.getElementById('post-history-panel');
        if (!panel) return;
        panel.addEventListener('toggle', function () {
            if (panel.open) {
                loadHistory();
            }
        });
    }

    function boot() {
        if (window.location.pathname.indexOf('/editor/post/') === -1) return;
        if (window.location.pathname.indexOf('/change/') === -1) return;
        setupPanelToggle();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
