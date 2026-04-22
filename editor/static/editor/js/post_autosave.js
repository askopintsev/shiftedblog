/**
 * Auto-save Post in admin: on sentence end (.) or after 5 seconds idle in body field.
 * Saves via AJAX; detects session expiry redirects; backs up body to localStorage.
 */
(function () {
    'use strict';

    var DRAFT_PREFIX = 'shiftedblog-post-body:';
    var LS_DEBOUNCE_MS = 1500;

    function getBodyContent() {
        var ta = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        if (!ta) return null;
        return ta.value;
    }

    function getForm() {
        var bodyEl = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        return bodyEl ? bodyEl.closest('form') : null;
    }

    function draftStorageKey() {
        var path = window.location.pathname;
        var m = path.match(/\/post\/(\d+)\/change\//);
        if (m) return DRAFT_PREFIX + m[1];
        if (path.indexOf('/post/add/') !== -1) return DRAFT_PREFIX + 'new';
        return null;
    }

    function persistDraftToLocal(content) {
        var key = draftStorageKey();
        if (!key || !window.localStorage || content === null) return;
        try {
            localStorage.setItem(key, content);
            localStorage.setItem(key + ':ts', String(Date.now()));
        } catch (e) {}
    }

    function clearDraftLocal() {
        var key = draftStorageKey();
        if (!key || !window.localStorage) return;
        try {
            localStorage.removeItem(key);
            localStorage.removeItem(key + ':ts');
        } catch (e) {}
    }

    function tryRestoreDraftFromLocal() {
        var key = draftStorageKey();
        if (!key || !window.localStorage) return;
        var saved;
        try {
            saved = localStorage.getItem(key);
        } catch (e) {
            return;
        }
        if (!saved) return;
        var ta = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        if (!ta) return;
        if (saved === ta.value) return;
        if (window.confirm(
            'В браузере есть несохранённая копия текста поста (например, после обрыва сессии). Восстановить её в поле редактора?'
        )) {
            ta.value = saved;
            try {
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                ta.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (err) {}
        }
    }

    function isLikelyAuthRedirect(response) {
        if (response.status !== 301 && response.status !== 302 && response.status !== 303 &&
            response.status !== 307 && response.status !== 308) {
            return false;
        }
        var loc = response.headers.get('Location') || '';
        return /login|account\/login|two_factor|signup|password_reset/i.test(loc);
    }

    function showSavedIndicator() {
        var now = new Date();
        var timeStr = now.getHours() + ':' + (now.getMinutes() < 10 ? '0' : '') + now.getMinutes();
        var msg = document.createElement('div');
        msg.id = 'post-autosave-indicator';
        msg.setAttribute('style',
            'position:fixed;top:60px;right:20px;z-index:9999;padding:8px 14px;background:#0d6efd;color:#fff;' +
            'border-radius:6px;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,0.2);transition:opacity 0.3s;');
        msg.textContent = 'Saved at ' + timeStr;
        document.body.appendChild(msg);
        setTimeout(function () {
            msg.style.opacity = '0';
            setTimeout(function () { msg.remove(); }, 300);
        }, 2500);
    }

    function showSessionLostBanner() {
        var id = 'post-autosave-session-lost';
        if (document.getElementById(id)) return;
        var bar = document.createElement('div');
        bar.id = id;
        bar.setAttribute('style',
            'position:fixed;top:0;left:0;right:0;z-index:10000;padding:12px 16px;background:#842029;color:#fff;' +
            'font-size:14px;text-align:center;');
        bar.textContent = 'Сессия истекла. Скопируйте текст поста в безопасное место, затем войдите снова. Черновик также сохранён в этом браузере (восстановление при обновлении страницы).';
        document.body.appendChild(bar);
    }

    var saveInProgress = false;

    function triggerSave() {
        var form = getForm();
        if (!form || saveInProgress) return;
        saveInProgress = true;
        var formData = new FormData(form);
        formData.set('_save', 'Save');
        fetch(window.location.href, {
            method: 'POST',
            body: formData,
            redirect: 'manual',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).then(function (response) {
            saveInProgress = false;
            if (isLikelyAuthRedirect(response)) {
                showSessionLostBanner();
                persistDraftToLocal(getBodyContent());
                return;
            }
            if (response.status === 403 || response.status === 401) {
                showSessionLostBanner();
                persistDraftToLocal(getBodyContent());
                return;
            }
            if (response.type === 'opaqueredirect' || response.status === 302 || response.status === 200) {
                if (response.status === 200 || response.status === 302) {
                    showSavedIndicator();
                    clearDraftLocal();
                }
            }
        }).catch(function () {
            saveInProgress = false;
        });
    }

    function runAutosave() {
        var bodyEl = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        if (!bodyEl || !getForm()) return;

        var lastContent = getBodyContent();
        var idleTimeout = null;
        var sentenceEndTimeout = null;
        var lsTimeout = null;
        var IDLE_MS = 5000;
        var SENTENCE_END_MS = 1000;
        var POLL_MS = 500;

        function scheduleLocalBackup() {
            if (lsTimeout) clearTimeout(lsTimeout);
            lsTimeout = setTimeout(function () {
                lsTimeout = null;
                persistDraftToLocal(getBodyContent());
            }, LS_DEBOUNCE_MS);
        }

        function scheduleIdleSave() {
            if (idleTimeout) clearTimeout(idleTimeout);
            idleTimeout = setTimeout(function () {
                idleTimeout = null;
                triggerSave();
            }, IDLE_MS);
        }

        function scheduleSentenceEndSave() {
            if (sentenceEndTimeout) clearTimeout(sentenceEndTimeout);
            sentenceEndTimeout = setTimeout(function () {
                sentenceEndTimeout = null;
                if (idleTimeout) clearTimeout(idleTimeout);
                idleTimeout = null;
                triggerSave();
            }, SENTENCE_END_MS);
        }

        function checkContent() {
            var content = getBodyContent();
            if (content === null) return;
            if (content !== lastContent) {
                lastContent = content;
                scheduleLocalBackup();
                scheduleIdleSave();
                var trimmed = content.trimEnd();
                if (trimmed.length > 0 && (/\.\s*$/.test(trimmed) || trimmed.endsWith('.</p>'))) {
                    scheduleSentenceEndSave();
                }
            }
        }

        setInterval(checkContent, POLL_MS);
    }

    function boot() {
        if (window.location.pathname.indexOf('/editor/post/') === -1) return;
        if (window.location.pathname.indexOf('/change/') === -1 && window.location.pathname.indexOf('/add/') === -1) {
            return;
        }
        setTimeout(tryRestoreDraftFromLocal, 500);
        setTimeout(runAutosave, 2000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
