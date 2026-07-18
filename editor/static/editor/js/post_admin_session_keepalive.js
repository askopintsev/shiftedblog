/**
 * Keep staff sessions alive on admin pages; guard login forms left open too long.
 */
(function () {
    'use strict';

    var INTERVAL_MS = 3 * 60 * 1000;
    var LOGIN_MAX_IDLE_MS = 50 * 60 * 1000;
    var pageLoadedAt = Date.now();

    function adminRootPrefix() {
        var parts = window.location.pathname.split('/').filter(Boolean);
        return parts.length ? '/' + parts[0] : '';
    }

    function isLoginPath(path) {
        return /^\/(login|account\/login)(\/|$)/.test(path);
    }

    function isAdminPath(path) {
        if (isLoginPath(path)) {
            return false;
        }
        var root = adminRootPrefix();
        if (!root) {
            return false;
        }
        return path === root || path.indexOf(root + '/') === 0;
    }

    function pingAdminSession() {
        var root = adminRootPrefix();
        if (!root) {
            return;
        }
        fetch(root + '/session-keepalive/', {
            method: 'GET',
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).catch(function () {});
    }

    function bindLoginIdleGuard() {
        var forms = document.querySelectorAll('form');
        forms.forEach(function (form) {
            if (form.dataset.shiftedblogLoginGuard === '1') {
                return;
            }
            form.dataset.shiftedblogLoginGuard = '1';
            form.addEventListener(
                'submit',
                function (event) {
                    if (Date.now() - pageLoadedAt < LOGIN_MAX_IDLE_MS) {
                        return;
                    }
                    event.preventDefault();
                    window.location.reload();
                },
                true,
            );
        });
    }

    function bindAdminPreSubmitPing() {
        document.querySelectorAll('form').forEach(function (form) {
            if (form.dataset.shiftedblogPreSubmitPing === '1') {
                return;
            }
            form.dataset.shiftedblogPreSubmitPing = '1';
            form.addEventListener(
                'submit',
                function () {
                    pingAdminSession();
                },
                true,
            );
        });
    }

    function ping() {
        var path = window.location.pathname;
        if (isLoginPath(path) || !isAdminPath(path)) {
            return;
        }
        pingAdminSession();
    }

    function init() {
        var path = window.location.pathname;
        if (isLoginPath(path)) {
            bindLoginIdleGuard();
            return;
        }
        if (!isAdminPath(path)) {
            return;
        }
        bindAdminPreSubmitPing();
        ping();
        setInterval(ping, INTERVAL_MS);
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'visible') {
                ping();
            }
        });
        window.addEventListener('focus', ping);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
