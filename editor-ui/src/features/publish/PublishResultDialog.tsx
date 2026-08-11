import { useEffect, useId, useRef } from "react";
import { CheckCircle2, ExternalLink, X, XCircle } from "lucide-react";
import type { PublishResult } from "@/api/types";
import { useT, type MessageKey, type TranslateParams } from "@/i18n";

interface PublishResultDialogProps {
  result: PublishResult;
  onClose: () => void;
}

type Translate = (key: MessageKey, params?: TranslateParams) => string;

function networkLabel(network: string, t: Translate): string {
  if (network === "site") return t("publish.site");
  if (network === "telegram") return t("common.telegram");
  return network;
}

export function PublishResultDialog({
  result,
  onClose,
}: PublishResultDialogProps) {
  const t = useT();
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const ok = result.all_ok;
  const entries = Object.entries(result.by_network);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-md overflow-hidden rounded-2xl border border-border bg-surface shadow-xl"
      >
        <div
          className={
            ok
              ? "border-b border-emerald-200 bg-emerald-50 px-5 py-4"
              : "border-b border-red-200 bg-red-50 px-5 py-4"
          }
        >
          <div className="flex items-start gap-3">
            {ok ? (
              <CheckCircle2
                className="mt-0.5 size-8 shrink-0 text-emerald-600"
                aria-hidden
              />
            ) : (
              <XCircle
                className="mt-0.5 size-8 shrink-0 text-red-600"
                aria-hidden
              />
            )}
            <div className="min-w-0 flex-1">
              <h2
                id={titleId}
                className={
                  ok
                    ? "text-lg font-semibold text-emerald-900"
                    : "text-lg font-semibold text-red-900"
                }
              >
                {ok ? t("publish.success") : t("publish.hasErrors")}
              </h2>
              <p
                className={
                  ok
                    ? "mt-1 text-sm text-emerald-800/90"
                    : "mt-1 text-sm text-red-800/90"
                }
              >
                {ok
                  ? t("publish.resultSuccessHint")
                  : t("publish.resultErrorHint")}
              </p>
              {result.status_updated && (
                <p className="mt-2 text-xs font-medium text-text-secondary">
                  {t("publish.statusUpdated")}
                </p>
              )}
            </div>
            <button
              ref={closeRef}
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-text-muted transition hover:bg-black/5 hover:text-text-primary"
              aria-label={t("common.close")}
            >
              <X className="size-5" aria-hidden />
            </button>
          </div>
        </div>

        <ul className="max-h-[50vh] space-y-2 overflow-y-auto px-5 py-4">
          {entries.map(([network, item]) => (
            <li
              key={network}
              className={
                item.ok
                  ? "rounded-xl border border-emerald-200 bg-emerald-50/70 px-3 py-3"
                  : "rounded-xl border border-red-200 bg-red-50/70 px-3 py-3"
              }
            >
              <div className="flex items-center gap-2">
                {item.ok ? (
                  <CheckCircle2
                    className="size-4 shrink-0 text-emerald-600"
                    aria-hidden
                  />
                ) : (
                  <XCircle
                    className="size-4 shrink-0 text-red-600"
                    aria-hidden
                  />
                )}
                <strong className="text-sm text-text-primary">
                  {networkLabel(network, t)}
                </strong>
                <span className="text-xs text-text-muted">
                  {item.ok ? t("common.ok") : t("publish.networkFailed")}
                </span>
              </div>
              {item.ok && item.message_url ? (
                <a
                  href={item.message_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex max-w-full items-center gap-1.5 break-all text-sm text-accent underline-offset-2 hover:underline"
                >
                  <ExternalLink className="size-3.5 shrink-0" aria-hidden />
                  <span>{item.message_url}</span>
                </a>
              ) : null}
              {!item.ok && (item.error || item.detail) ? (
                <p className="mt-2 text-sm text-red-700">
                  {item.detail || item.error}
                </p>
              ) : null}
            </li>
          ))}
        </ul>

        <div className="flex justify-end border-t border-border bg-surface-muted/50 px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
          >
            {t("common.close")}
          </button>
        </div>
      </div>
    </div>
  );
}
