export function PostBodyEditorMock() {
  return (
    <div className="post-body-editor rounded-xl border border-border bg-surface p-4">
      <div className="mb-2 text-xs text-text-muted">
        Символов: 12 345 · Слов: 1 890 · ~9 мин · Качество: 78
      </div>
      <div className="rounded-lg border border-border bg-white p-2">
        <div className="flex flex-wrap gap-1 border-b border-border pb-2 text-xs">
          {["H", "B", "I", "U", "•", "1.", "🔗", "🖼", "<>"].map((t) => (
            <span key={t} className="rounded bg-surface-muted px-2 py-1">
              {t}
            </span>
          ))}
        </div>
        <p className="mx-auto max-w-[700px] pt-4 text-lg leading-relaxed text-justify">
          Пример текста поста с выравниванием по ширине, как на публичной странице блога.
        </p>
      </div>
    </div>
  );
}
