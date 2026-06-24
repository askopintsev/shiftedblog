const GROUPS = [
  {
    label: "Смайлы",
    chars:
      "😀 😃 😄 😁 😅 😂 🤣 🥲 🥹 🙂 😉 😊 😇 🥰 😍 🤩 😘 😗 😚 😙 😋 😛 😜 🤪 😝 🤑 🤗 🤭 🤫 🤔 🤐 🫢 🫣 🫡 😐 😑 😶 🙄 😏 😒 🙃 😬 😮‍💨 🤥 😌 😔 😪 🤤 😴 😷 🤒 🤕 🤢 🤮 🤧 🥵 🥶 🥴 😵 🤯 🤠 🥳 🥸 😎 🤓 🧐 😕 😟 🙁 😮 😯 😲 😳 🥺 😦 😧 😨 😰 😥 😢 😭 😱 😖 😣 😞 😓 😩 😫 🥱 😤 😡 😠 🤬 😈 👿 💀 💩 🤡 👹 👺 👻 👽 👾 🤖",
  },
  {
    label: "Жесты / люди",
    chars:
      "👍 👎 ✊ 👊 🤛 🤜 👏 🙌 👐 🤲 🤝 🙏 ✌️ 🤞 🤟 🤘 🤙 👌 🤌 👈 👉 👆 👇 ☝️ 💪 🦾 🦵 🦶 👂 👃 🧠 🫀 🫁 🦷 🦴 👀 👅 🤦 🤷 👶 🧒 👦 👧 🧑 👨 👩 🧔 👴 👵",
  },
  {
    label: "Сердца / символы",
    chars:
      "❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 ❣️ 💕 💞 💓 💗 💖 💘 💝 💟 ☮️ ✝️ ☪️ 🕎 ☸️ ⚛️ 🔯 ♈ ♉ ♊ ♋ ♌ ♍ ♎ ♏ ♐ ♑ ♒ ♓ ✅ ☑️ ✔️ ❌ ❎ ➕ ➖ ✖️ ➗ ♾️ ⁉️ ❓ ❔ ❗ ❕ ⚠️ 💯 ♻️",
  },
  {
    label: "Техно / офис",
    chars:
      "💻 🖥️ 🖨️ ⌨️ 🖱️ 📱 📞 ☎️ 📠 📺 📻 🎙️ 📷 📸 📹 💾 💿 📀 📁 📂 📌 📎 ✏️ ✒️ 📏 📐 📊 📈 📉 📧 📨 📩 📪 💡 🔦 🔌 🔋 🔗 🧭 🕐 ⏱️ 🔒 🔓 🔑",
  },
  {
    label: "Идеи / письмо",
    chars:
      "💡 📌 ✅ ❗ ❓ 📎 ✍️ 📝 📋 📚 📖 🔍 🔎 📣 📢 💬 💭 📰 🗂️ 🎯 🏆 🥇 🎉 🎊 🎁 🔥 ⚡ 💥 ✨ 🌟 ⭐ 💧 🌍 🌎 🌏 🌞 🌙 🚀",
  },
];

import { useState } from "react";
import type { Editor } from "ckeditor5";

interface EmojiPaletteProps {
  onInsert: (editor: Editor | null, text: string) => void;
}

function splitChars(chars: string): string[] {
  return chars.trim().split(/\s+/).filter(Boolean);
}

export function EmojiPalette({ onInsert }: EmojiPaletteProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex justify-end">
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex h-9 items-center rounded-lg border border-border bg-surface px-3 text-sm"
        >
          😀 Эмодзи
        </button>
        {open && (
          <div className="absolute right-0 z-10 mt-1 max-h-80 w-96 overflow-auto rounded-lg border border-border bg-surface p-3 shadow-lg">
            {GROUPS.map((g) => (
              <div key={g.label} className="mb-3 last:mb-0">
                <div className="text-xs font-semibold uppercase text-text-muted">
                  {g.label}
                </div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {splitChars(g.chars).map((ch) => (
                    <button
                      key={ch}
                      type="button"
                      className="rounded p-1.5 text-lg leading-none hover:bg-surface-muted"
                      onClick={() => onInsert(null, ch)}
                      aria-label={`Вставить ${ch}`}
                    >
                      {ch}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
