import { useRef, useState } from "react";
import type { Editor } from "ckeditor5";
import { EditorToolbarButton } from "./EditorToolbarButton";
import { FloatingEditorPopover } from "./FloatingEditorPopover";

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

interface EmojiPaletteProps {
  onInsert: (editor: Editor | null, text: string) => void;
}

function splitChars(chars: string): string[] {
  return chars.trim().split(/\s+/).filter(Boolean);
}

export function EmojiPalette({ onInsert }: EmojiPaletteProps) {
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);

  const handleInsert = (text: string) => {
    onInsert(null, text);
  };

  return (
    <>
      <EditorToolbarButton
        ref={buttonRef}
        icon={<span className="text-lg leading-none">😀</span>}
        active={open}
        aria-expanded={open}
        aria-haspopup="dialog"
        title="Открыть палитру эмодзи"
        onClick={() => setOpen((value) => !value)}
      >
        Эмодзи
      </EditorToolbarButton>
      <FloatingEditorPopover
        open={open}
        onClose={() => setOpen(false)}
        anchorRef={buttonRef}
        ariaLabel="Палитра эмодзи"
      >
        {GROUPS.map((group) => (
          <div key={group.label} className="mb-3 last:mb-0">
            <div className="text-[0.7rem] font-semibold uppercase tracking-wide text-text-muted">
              {group.label}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {splitChars(group.chars).map((char) => (
                <button
                  key={char}
                  type="button"
                  className="inline-flex size-8 items-center justify-center rounded-md text-xl leading-none transition hover:bg-surface-muted"
                  onClick={() => handleInsert(char)}
                  aria-label={`Вставить ${char}`}
                >
                  {char}
                </button>
              ))}
            </div>
          </div>
        ))}
      </FloatingEditorPopover>
    </>
  );
}
