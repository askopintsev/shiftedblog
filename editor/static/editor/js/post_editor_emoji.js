/**
 * Post admin: emoji palette for CKEditor body (django-ckeditor-5).
 * No extra build: inserts Unicode via the editor model API; OS paste still works.
 */
(function () {
    'use strict';

    var BODY_FIELD_ID = 'id_body';

    /** Curated BMP + common supplementary symbols (pairs as surrogate pairs avoided where possible). */
    var EMOJI_GROUPS = [
        {
            label: 'Смайлы',
            chars: '😀 😃 😄 😁 😅 😂 🤣 🥲 🥹 🙂 😉 😊 😇 🥰 😍 🤩 😘 😗 😚 😙 😋 😛 😜 🤪 😝 🤑 🤗 🤭 🤫 🤔 🤐 🫢 🫣 🫡 😐 😑 😶 🙄 😏 😒 🙃 😬 😮‍💨 🤥 😌 😔 😪 🤤 😴 😷 🤒 🤕 🤢 🤮 🤧 🥵 🥶 🥴 😵 🤯 🤠 🥳 🥸 😎 🤓 🧐 😕 😟 🙁 😮 😯 😲 😳 🥺 😦 😧 😨 😰 😥 😢 😭 😱 😖 😣 😞 😓 😩 😫 🥱 😤 😡 😠 🤬 😈 👿 💀 💩 🤡 👹 👺 👻 👽 👾 🤖',
        },
        {
            label: 'Жесты / люди',
            chars: '👍 👎 ✊ 👊 🤛 🤜 👏 🙌 👐 🤲 🤝 🙏 ✌️ 🤞 🤟 🤘 🤙 👌 🤌 👈 👉 👆 👇 ☝️ 💪 🦾 🦵 🦶 👂 👃 🧠 🫀 🫁 🦷 🦴 👀 👅 🤦 🤷 👶 🧒 👦 👧 🧑 👨 👩 🧔 👴 👵',
        },
        {
            label: 'Сердца / символы',
            chars: '❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 ❣️ 💕 💞 💓 💗 💖 💘 💝 💟 ☮️ ✝️ ☪️ 🕎 ☸️ ⚛️ 🔯 ♈ ♉ ♊ ♋ ♌ ♍ ♎ ♏ ♐ ♑ ♒ ♓ ✅ ☑️ ✔️ ❌ ❎ ➕ ➖ ✖️ ➗ ♾️ ⁉️ ❓ ❔ ❗ ❕ ⚠️ 💯 ♻️',
        },
        {
            label: 'Техно / офис',
            chars: '💻 🖥️ 🖨️ ⌨️ 🖱️ 📱 📞 ☎️ 📠 📺 📻 🎙️ 📷 📸 📹 💾 💿 📀 📁 📂 📌 📎 ✏️ ✒️ 📏 📐 📊 📈 📉 📧 📨 📩 📪 💡 🔦 🔌 🔋 🔗 🧭 🕐 ⏱️ 🔒 🔓 🔑',
        },
        {
            label: 'Идеи / письмо',
            chars: '💡 📌 ✅ ❗ ❓ 📎 ✍️ 📝 📋 📚 📖 🔍 🔎 📣 📢 💬 💭 📰 🗂️ 🎯 🏆 🥇 🎉 🎊 🎁 🔥 ⚡ 💥 ✨ 🌟 ⭐ 💧 🌍 🌎 🌏 🌞 🌙 🚀',
        },
    ];

    function splitChars(s) {
        return s.trim().split(/\s+/).filter(Boolean);
    }

    function insertAtCaret(editor, text) {
        editor.model.change(function (writer) {
            var sel = editor.model.document.selection;
            if (!sel.isCollapsed) {
                writer.remove(sel.getFirstRange());
            }
            var pos = editor.model.document.selection.focus;
            writer.insertText(text, pos);
        });
        editor.editing.view.focus();
    }

    function buildPalette(root, editor) {
        var panel = document.createElement('div');
        panel.className = 'post-editor-emoji__panel ck-reset_all';
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-hidden', 'true');

        EMOJI_GROUPS.forEach(function (g) {
            var h = document.createElement('div');
            h.className = 'post-editor-emoji__group-title';
            h.textContent = g.label;
            panel.appendChild(h);
            var row = document.createElement('div');
            row.className = 'post-editor-emoji__grid';
            splitChars(g.chars).forEach(function (ch) {
                var b = document.createElement('button');
                b.type = 'button';
                b.className = 'post-editor-emoji__btn';
                b.textContent = ch;
                b.setAttribute('aria-label', 'Вставить ' + ch);
                b.addEventListener('click', function () {
                    insertAtCaret(editor, ch);
                });
                row.appendChild(b);
            });
            panel.appendChild(row);
        });

        root.appendChild(panel);
        return panel;
    }

    function attach(editor) {
        if (editor._postEmojiAttached) return;
        editor._postEmojiAttached = true;

        var ta = document.getElementById(BODY_FIELD_ID);
        var wrap = ta && ta.closest('.ck-editor-container');
        if (!wrap) return;

        var bar = document.createElement('div');
        bar.className = 'post-editor-emoji ck-reset_all';

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'post-editor-emoji__toggle';
        btn.setAttribute('title', 'Открыть палитру эмодзи');
        btn.innerHTML =
            '<span class="post-editor-emoji__icon" aria-hidden="true">😀</span>' +
            '<span class="post-editor-emoji__label">Эмодзи</span>';
        btn.setAttribute('aria-expanded', 'false');
        btn.setAttribute('aria-controls', BODY_FIELD_ID + '-emoji-panel');

        wrap.insertBefore(bar, wrap.firstChild);
        bar.appendChild(btn);

        var panel = buildPalette(bar, editor);
        panel.id = BODY_FIELD_ID + '-emoji-panel';

        function close() {
            panel.classList.remove('post-editor-emoji__panel--open');
            btn.setAttribute('aria-expanded', 'false');
            panel.setAttribute('aria-hidden', 'true');
        }

        function open() {
            panel.classList.add('post-editor-emoji__panel--open');
            btn.setAttribute('aria-expanded', 'true');
            panel.setAttribute('aria-hidden', 'false');
        }

        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (panel.classList.contains('post-editor-emoji__panel--open')) {
                close();
            } else {
                open();
            }
        });

        document.addEventListener('click', function (ev) {
            if (!bar.contains(ev.target)) close();
        });
        document.addEventListener('keydown', function (ev) {
            if (ev.key === 'Escape') close();
        });
    }

    function pollEditor() {
        var editors = window.editors;
        if (editors && editors[BODY_FIELD_ID]) attach(editors[BODY_FIELD_ID]);
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof window.ckeditorRegisterCallback === 'function') {
            window.ckeditorRegisterCallback(BODY_FIELD_ID, attach);
        }
        var n = 0;
        var t = setInterval(function () {
            pollEditor();
            if (++n > 240) clearInterval(t);
        }, 125);
    });
})();
