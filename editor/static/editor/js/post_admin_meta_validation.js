/**
 * Highlight SEO-critical fields when status is Ready to publish / Published
 * so editors see requirements before submit (with server-side validation).
 */
(function () {
    'use strict';

    var PUBLISH = ['ready_to_publish', 'published'];

    function isPublishStatus(value) {
        return PUBLISH.indexOf(value) !== -1;
    }

    function sync() {
        var statusEl = document.getElementById('id_status');
        if (!statusEl) return;
        var publish = isPublishStatus(statusEl.value);
        ['field-title', 'field-cover_image'].forEach(function (cls) {
            var row = document.querySelector('.form-row.' + cls);
            if (row) {
                row.classList.toggle('post-meta-required', publish);
            }
        });
    }

    function init() {
        var path = window.location.pathname;
        if (path.indexOf('/editor/post/') === -1 || path.indexOf('/change/') === -1) return;

        sync();
        var statusEl = document.getElementById('id_status');
        if (statusEl) {
            statusEl.addEventListener('change', sync);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
