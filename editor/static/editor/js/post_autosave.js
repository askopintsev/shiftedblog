/**
 * Auto-save Post in admin: on sentence end (.) or after 5 seconds idle in body field.
 * Saves via AJAX so the page stays open. Works with CKEditor 5 (polls body textarea).
 */
(function() {
    'use strict';

    function getBodyContent() {
        var ta = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        if (!ta) return null;
        return ta.value;
    }

    function getForm() {
        var bodyEl = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        return bodyEl ? bodyEl.closest('form') : null;
    }

    function getSaveButton() {
        return document.querySelector('input[name="_save"]');
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
        setTimeout(function() {
            msg.style.opacity = '0';
            setTimeout(function() { msg.remove(); }, 300);
        }, 2500);
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
        }).then(function(response) {
            saveInProgress = false;
            if (response.type === 'opaqueredirect' || response.status === 302 || response.status === 200) {
                showSavedIndicator();
            }
        }).catch(function() {
            saveInProgress = false;
        });
    }

    function runAutosave() {
        var bodyEl = document.getElementById('id_body') || document.querySelector('textarea[name="body"]');
        if (!bodyEl || !getForm()) return;

        var lastContent = getBodyContent();
        var idleTimeout = null;
        var sentenceEndTimeout = null;
        var IDLE_MS = 5000;
        var SENTENCE_END_MS = 1000;
        var POLL_MS = 500;

        function scheduleIdleSave() {
            if (idleTimeout) clearTimeout(idleTimeout);
            idleTimeout = setTimeout(function() {
                idleTimeout = null;
                triggerSave();
            }, IDLE_MS);
        }

        function scheduleSentenceEndSave() {
            if (sentenceEndTimeout) clearTimeout(sentenceEndTimeout);
            sentenceEndTimeout = setTimeout(function() {
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
                scheduleIdleSave();
                var trimmed = content.trimEnd();
                if (trimmed.length > 0 && (/\.\s*$/.test(trimmed) || trimmed.endsWith('.</p>'))) {
                    scheduleSentenceEndSave();
                }
            }
        }

        setInterval(checkContent, POLL_MS);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            if (window.location.pathname.indexOf('/editor/post/') !== -1 && window.location.pathname.indexOf('/change/') !== -1) {
                setTimeout(runAutosave, 2000);
            }
        });
    } else {
        if (window.location.pathname.indexOf('/editor/post/') !== -1 && window.location.pathname.indexOf('/change/') !== -1) {
            setTimeout(runAutosave, 2000);
        }
    }
})();
