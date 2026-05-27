/**
 * Post admin: default CKEditor body text alignment to justify.
 */
(function () {
    'use strict';

    var BODY_FIELD_ID = 'id_body';
    var DEFAULT_ALIGN = 'justify';

    function forEachAlignableBlock(editor, callback) {
        var root = editor.model.document.getRoot();
        if (!root) {
            return;
        }
        var range = editor.model.createRangeIn(root);
        var walker = range.getWalker({ ignoreElementEnd: true });
        var step = walker.next();
        while (!step.done) {
            var item = step.value;
            if (item.type === 'elementStart') {
                var el = item.item;
                if (el.is && el.is('element') && editor.model.schema.checkAttribute(el, 'alignment')) {
                    callback(el);
                }
            }
            step = walker.next();
        }
    }

    function applyDefaultAlignment(editor) {
        if (editor._postDefaultAlignApplying) {
            return;
        }
        editor._postDefaultAlignApplying = true;
        editor.model.change(function (writer) {
            forEachAlignableBlock(editor, function (el) {
                if (!el.hasAttribute('alignment')) {
                    writer.setAttribute('alignment', DEFAULT_ALIGN, el);
                }
            });
        });
        editor._postDefaultAlignApplying = false;
    }

    function scheduleDefaultAlignment(editor) {
        if (editor._postDefaultAlignTimer) {
            clearTimeout(editor._postDefaultAlignTimer);
        }
        editor._postDefaultAlignTimer = setTimeout(function () {
            editor._postDefaultAlignTimer = null;
            applyDefaultAlignment(editor);
        }, 250);
    }

    function wrapSetData(editor) {
        if (editor._postDefaultAlignSetDataWrapped) {
            return;
        }
        editor._postDefaultAlignSetDataWrapped = true;
        var originalSetData = editor.setData.bind(editor);
        editor.setData = function (data) {
            var result = originalSetData(data);
            if (result && typeof result.then === 'function') {
                return result.then(function (value) {
                    scheduleDefaultAlignment(editor);
                    return value;
                });
            }
            scheduleDefaultAlignment(editor);
            return result;
        };
    }

    function attach(editor) {
        if (editor._postDefaultAlignAttached) {
            return;
        }
        editor._postDefaultAlignAttached = true;

        wrapSetData(editor);
        scheduleDefaultAlignment(editor);

        editor.editing.view.document.on('enter', function () {
            scheduleDefaultAlignment(editor);
        }, { priority: 'lowest' });

        editor.model.document.on('change:data', function () {
            scheduleDefaultAlignment(editor);
        });
    }

    function pollEditor() {
        var editors = window.editors;
        if (editors && editors[BODY_FIELD_ID]) {
            attach(editors[BODY_FIELD_ID]);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof window.ckeditorRegisterCallback === 'function') {
            window.ckeditorRegisterCallback(BODY_FIELD_ID, attach);
        }
        var attempts = 0;
        var timer = setInterval(function () {
            pollEditor();
            if (++attempts > 240) {
                clearInterval(timer);
            }
        }, 125);
    });
})();
