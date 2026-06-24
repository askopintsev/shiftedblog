import { useCallback, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

const DRAFT_PREFIX = "shiftedblog-post-body:";

function htmlEndsWithSentence(html: string): boolean {
  const trimmed = html.trimEnd();
  if (!trimmed) return false;
  return /\.\s*$/.test(trimmed) || trimmed.endsWith(".</p>");
}

export function useAutosave<T extends { body: string }>(
  postId: string | undefined,
  isNew: boolean,
  getPayload: () => T,
  onSaved?: () => void,
) {
  const idleTimer = useRef<number | null>(null);
  const sentenceTimer = useRef<number | null>(null);
  const lsTimer = useRef<number | null>(null);
  const lastBody = useRef("");

  const autosaveMutation = useMutation({
    mutationFn: (payload: T) =>
      apiFetch(`/posts/${postId}/autosave/`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      onSaved?.();
      if (postId) {
        try {
          localStorage.removeItem(`${DRAFT_PREFIX}${postId}`);
          localStorage.removeItem(`${DRAFT_PREFIX}${postId}:ts`);
        } catch {
          /* ignore */
        }
      }
    },
    onError: (err: unknown) => {
      const status = (err as { status?: number }).status;
      if (status === 401 || status === 403) {
        const payload = getPayload();
        if (postId) {
          try {
            localStorage.setItem(`${DRAFT_PREFIX}${postId}`, payload.body);
            localStorage.setItem(`${DRAFT_PREFIX}${postId}:ts`, String(Date.now()));
          } catch {
            /* ignore */
          }
        }
      }
    },
  });

  const persistLocal = useCallback(
    (body: string) => {
      if (!postId || isNew) return;
      if (lsTimer.current) window.clearTimeout(lsTimer.current);
      lsTimer.current = window.setTimeout(() => {
        try {
          localStorage.setItem(`${DRAFT_PREFIX}${postId}`, body);
          localStorage.setItem(`${DRAFT_PREFIX}${postId}:ts`, String(Date.now()));
        } catch {
          /* ignore */
        }
      }, 1500);
    },
    [isNew, postId],
  );

  const triggerAutosave = useCallback(() => {
    if (isNew || !postId) return;
    autosaveMutation.mutate(getPayload());
  }, [autosaveMutation, getPayload, isNew, postId]);

  const scheduleAutosave = useCallback(
    (body: string) => {
      if (isNew || !postId) return;
      persistLocal(body);

      if (idleTimer.current) window.clearTimeout(idleTimer.current);
      idleTimer.current = window.setTimeout(triggerAutosave, 5000);

      if (htmlEndsWithSentence(body)) {
        if (sentenceTimer.current) window.clearTimeout(sentenceTimer.current);
        sentenceTimer.current = window.setTimeout(() => {
          if (idleTimer.current) window.clearTimeout(idleTimer.current);
          idleTimer.current = null;
          triggerAutosave();
        }, 1000);
      }
    },
    [isNew, persistLocal, postId, triggerAutosave],
  );

  useEffect(() => {
    if (isNew || !postId) return;
    const interval = window.setInterval(() => {
      const body = getPayload().body;
      if (body !== lastBody.current) {
        lastBody.current = body;
        scheduleAutosave(body);
      }
    }, 500);
    return () => window.clearInterval(interval);
  }, [getPayload, isNew, postId, scheduleAutosave]);

  return { scheduleAutosave, triggerAutosave, autosaving: autosaveMutation.isPending };
}

export function tryRestoreDraftFromLocal(
  postId: string,
  currentBody: string,
): string | null {
  try {
    const saved = localStorage.getItem(`${DRAFT_PREFIX}${postId}`);
    if (!saved || saved === currentBody) return null;
    if (
      window.confirm(
        "В браузере есть несохранённая копия текста поста (например, после обрыва сессии). Восстановить её в поле редактора?",
      )
    ) {
      return saved;
    }
  } catch {
    /* ignore */
  }
  return null;
}
