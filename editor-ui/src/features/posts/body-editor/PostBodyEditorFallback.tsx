export function PostBodyEditorFallback() {
  return (
    <div
      className="mx-auto w-full max-w-[760px] animate-pulse space-y-3"
      aria-hidden
    >
      <div className="h-8 rounded-lg bg-surface-muted" />
      <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
        <div className="h-11 border-b border-border bg-surface-muted" />
        <div className="min-h-[420px] bg-surface-muted/40" />
      </div>
    </div>
  );
}
