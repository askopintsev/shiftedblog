/**
 * Auto-save Post in admin: on sentence end (.) or after 5 seconds idle in body field.
 * Saves via AJAX; detects session expiry redirects; backs up body to localStorage.
 *
 * Runs only on post *change* (existing pk). Disabled on post *add*: concurrent POSTs
 * there can create duplicate rows / slug unique violations. Saving the form via the
 * admin buttons aborts any in-flight autosave to avoid overlapping writes.
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

    /**
     * Build POST body omitting empty file inputs. Some browsers serialize them with
     * filename="", which interacts badly with Django multipart parsing and existing
     * CoverImage/FileField logic on admin change forms.
     */
    function buildAutosaveFormData(form) {
        var fd = new FormData(form);
        fd.set('_save', 'Save');
        var inputs = form.querySelectorAll('input[type="file"]');
        for (var i = 0; i < inputs.length; i++) {
            var inp = inputs[i];
            if (!inp.name) continue;
            try {
                if (!inp.files || inp.files.length === 0) {
                    fd.delete(inp.name);
                }
            } catch (e) {}
        }
        return fd;
    }

    /** Django admin renders real errors under p.errornote or ul.errorlist with li items. */
    function adminHtmlHasErrors(htmlText) {
        try {
            var doc = new DOMParser().parseFromString(htmlText, 'text/html');
            var note = doc.querySelector('p.errornote');
            if (note && note.textContent && note.textContent.trim()) {
                return true;
            }
            var lists = doc.querySelectorAll('ul.errorlist');
            var i;
            for (i = 0; i < lists.length; i++) {
                if (lists[i].querySelector('li')) {
                    return true;
                }
            }
            return false;
        } catch (e) {
            return false;
        }
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
    /** True once the native admin form begins submit (manual Save / keyboard). */
    var autosaveSuspended = false;
    var autosaveAbort = null;

    function attachAutosaveSubmitHook(form) {
        if (!form || form.dataset.shiftedblogAutosaveSubmitHook === '1') {
            return;
        }
        form.dataset.shiftedblogAutosaveSubmitHook = '1';
        form.addEventListener(
            'submit',
            function () {
                autosaveSuspended = true;
                if (autosaveAbort) {
                    try {
                        autosaveAbort.abort();
                    } catch (eAbort) {}
                    autosaveAbort = null;
                }
            },
            true
        );
    }

    function triggerSave() {
        var form = getForm();
        if (!form || saveInProgress || autosaveSuspended) return;
        saveInProgress = true;
        var formData = buildAutosaveFormData(form);
        var fetchOpts = {
            method: 'POST',
            body: formData,
            redirect: 'manual',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        if (typeof AbortController !== 'undefined') {
            autosaveAbort = new AbortController();
            fetchOpts.signal = autosaveAbort.signal;
        }
        fetch(window.location.href, fetchOpts).then(function (response) {
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
            if (response.status >= 502 && response.status <= 504) {
                showSessionLostBanner();
                persistDraftToLocal(getBodyContent());
                return;
            }
            if (response.type === 'opaqueredirect' ||
                response.status === 302 || response.status === 303 ||
                response.status === 307 || response.status === 308) {
                showSavedIndicator();
                clearDraftLocal();
                return;
            }
            if (response.status === 200) {
                return response.text().then(function (html) {
                    if (!adminHtmlHasErrors(html)) {
                        showSavedIndicator();
                        clearDraftLocal();
                    }
                });
            }
        }).catch(function () {
            /* Ignore network failures and aborted autosave requests. */
        }).finally(function () {
            autosaveAbort = null;
            saveInProgress = false;
        });
    }

    function runAutosave() {
        var bodyEl = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        var form = getForm();
        if (!bodyEl || !form) return;
        attachAutosaveSubmitHook(form);

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
        /* Autosave on "add" can race with Save and create duplicate slug rows — skip until first save. */
        if (window.location.pathname.indexOf('/post/add/') !== -1) {
            return;
        }
        setTimeout(runAutosave, 2000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
