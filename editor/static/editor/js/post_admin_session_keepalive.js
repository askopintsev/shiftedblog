/**
 * Periodically ping admin session-keepalive so staff sessions stay valid while editing.
 */
(function () {
    'use strict';

    var INTERVAL_MS = 4 * 60 * 1000;

    function adminRootPrefix() {
        var parts = window.location.pathname.split('/').filter(Boolean);
        return parts.length ? '/' + parts[0] : '';
    }

    function ping() {
        if (document.visibilityState && document.visibilityState !== 'visible') {
            return;
        }
        var root = adminRootPrefix();
        if (!root) return;
        fetch(root + '/session-keepalive/', {
            method: 'GET',
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).catch(function () {});
    }

    function init() {
        var path = window.location.pathname;
        if (path.indexOf('/editor/post/') === -1) return;
        if (path.indexOf('/change/') === -1 && path.indexOf('/add/') === -1) return;
        ping();
        setInterval(ping, INTERVAL_MS);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'visible') {
                ping();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
