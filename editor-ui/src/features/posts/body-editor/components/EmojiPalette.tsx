const GROUPS = [
  {
    label: "Смайлы",
    chars: "😀 😃 😄 😁 😅 😂 🤣 🙂 😉 😊 🥰 😍 🤔 😎",
  },
  {
    label: "Жесты",
    chars: "👍 👎 👏 🙌 🤝 🙏 ✌️ 💪",
  },
  {
    label: "Символы",
    chars: "❤️ ✅ ❗ ❓ 💡 🔥 ⭐",
  },
];

import { useState } from "react";
import type { Editor } from "ckeditor5";

interface EmojiPaletteProps {
  onInsert: (editor: Editor | null, text: string) => void;
}

export function EmojiPalette({ onInsert }: EmojiPaletteProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-2 flex justify-end">
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm"
        >
          😀 Эмодзи
        </button>
        {open && (
          <div className="absolute right-0 z-10 mt-1 max-h-48 w-72 overflow-auto rounded-lg border border-border bg-surface p-2 shadow-lg">
            {GROUPS.map((g) => (
              <div key={g.label} className="mb-2">
                <div className="text-xs font-semibold uppercase text-text-muted">
                  {g.label}
                </div>
                <div className="flex flex-wrap gap-1">
                  {g.chars.split(" ").map((ch) => (
                    <button
                      key={ch}
                      type="button"
                      className="rounded p-1 hover:bg-surface-muted"
                      onClick={() => onInsert(null, ch)}
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
