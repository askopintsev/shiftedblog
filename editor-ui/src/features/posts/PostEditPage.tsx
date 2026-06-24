import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiUpload } from "@/api/client";
import type { PostDetail, PostStatus } from "@/api/types";
import { PostBodyEditor } from "@/features/posts/body-editor/PostBodyEditor";
import { GalleryTab } from "@/features/posts/components/GalleryTab";
import {
  tryRestoreDraftFromLocal,
  useAutosave,
} from "@/features/posts/hooks/useAutosave";
import { cn } from "@/lib/utils";

export function PostEditPage() {
  const { id } = useParams();
  const isNew = !id || id === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [focusMode, setFocusMode] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"editor" | "gallery">("editor");
  const draftRestored = useRef(false);

  const { data, isLoading } = useQuery({
    queryKey: ["post", id],
    enabled: !isNew,
    queryFn: () =>
      apiFetch<{ ok: boolean; post: PostDetail }>(`/posts/${id}/`),
  });

  const [form, setForm] = useState({
    title: "",
    body: "",
    status: "draft" as PostStatus,
    short_description: "",
    slug: "",
  });

  useEffect(() => {
    if (data?.post) {
      setForm({
        title: data.post.title ?? "",
        body: data.post.body ?? "",
        status: data.post.status,
        short_description: data.post.short_description ?? "",
        slug: data.post.slug ?? "",
      });
    }
  }, [data?.post]);

  useEffect(() => {
    if (isNew || !id || draftRestored.current || !data?.post) return;
    draftRestored.current = true;
    const restored = tryRestoreDraftFromLocal(id, data.post.body ?? "");
    if (restored) {
      setForm((f) => ({ ...f, body: restored }));
    }
  }, [data?.post, id, isNew]);

  const formRef = useRef(form);
  formRef.current = form;
  const getPayload = useCallback(() => formRef.current, []);

  const { scheduleAutosave } = useAutosave(id, isNew, getPayload, () =>
    setSavedAt(new Date()),
  );

  const saveMutation = useMutation({
    mutationFn: async (payload: typeof form) => {
      if (isNew) {
        return apiFetch<{ ok: boolean; post: PostDetail }>("/posts/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      return apiFetch<{ ok: boolean; post: PostDetail }>(`/posts/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: (res) => {
      setSavedAt(new Date());
      queryClient.invalidateQueries({ queryKey: ["posts"] });
      if (isNew && res.post?.id) {
        navigate(`/posts/${res.post.id}`, { replace: true });
      }
    },
  });

  const coverMutation = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("cover_image", file);
      return apiUpload<{ ok: boolean; post: PostDetail }>(
        `/posts/${id}/`,
        fd,
        "PATCH",
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["post", id] });
      setSavedAt(new Date());
    },
  });

  const sitePublish = useMutation({
    mutationFn: () =>
      apiFetch(`/posts/${id}/site-publish/`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["post", id] }),
  });

  const siteUnpublish = useMutation({
    mutationFn: () =>
      apiFetch(`/posts/${id}/site-unpublish/`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["post", id] }),
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        saveMutation.mutate(form);
      }
      if (e.key === "Escape" && focusMode) {
        setFocusMode(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusMode, form, saveMutation]);

  const historyQuery = useQuery({
    queryKey: ["post-history", id],
    enabled: historyOpen && !isNew,
    queryFn: () =>
      apiFetch<{
        ok: boolean;
        items: { id: number; created_at: string; preview: string }[];
      }>(`/posts/${id}/history/`),
  });

  const updateForm = useCallback(
    (next: typeof form) => {
      setForm(next);
      scheduleAutosave(next.body);
    },
    [scheduleAutosave],
  );

  if (!isNew && isLoading) {
    return <div className="p-6">Загрузка…</div>;
  }

  const publishReady =
    form.status === "ready_to_publish" || form.status === "published";

  return (
    <div className="flex min-h-full">
      {!focusMode && (
        <div className="flex w-12 flex-col items-center gap-2 border-r border-border bg-surface py-4">
          <Link to="/posts" className="text-xs text-text-muted">
            ←
          </Link>
          {!isNew && (
            <button
              type="button"
              title="История"
              className="text-xs text-text-muted"
              onClick={() => setHistoryOpen(true)}
            >
              H
            </button>
          )}
          <button
            type="button"
            title="Фокус"
            className="text-xs text-text-muted"
            onClick={() => setFocusMode(true)}
          >
            ⛶
          </button>
        </div>
      )}
      {focusMode && (
        <button
          type="button"
          className="fixed right-4 top-4 z-50 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm"
          onClick={() => setFocusMode(false)}
        >
          Выйти из фокуса (Esc)
        </button>
      )}
      <div className="flex min-w-0 flex-1">
        <div className="flex-1 p-6">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm text-text-muted">
              {savedAt
                ? `Сохранено ${savedAt.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}`
                : "Не сохранено"}
            </div>
            <div className="flex gap-2">
              {!isNew && data?.post?.draft_preview_url && (
                <a
                  href={data.post.draft_preview_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-accent"
                >
                  Превью
                </a>
              )}
              {!isNew && form.status === "ready_to_publish" && (
                <Link to="/publish" className="text-sm text-accent">
                  Публикация →
                </Link>
              )}
              <button
                type="button"
                onClick={() => saveMutation.mutate(form)}
                className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
              >
                Сохранить
              </button>
            </div>
          </div>
          <input
            value={form.title}
            onChange={(e) => updateForm({ ...form, title: e.target.value })}
            placeholder="Заголовок"
            className={cn(
              "mb-4 w-full border-0 bg-transparent text-3xl font-semibold outline-none",
              publishReady && "rounded-lg border-l-4 border-warning pl-3",
            )}
          />
          {!isNew && (
            <div className="mb-4 flex gap-2 border-b border-border">
              {(["editor", "gallery"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "border-b-2 px-3 py-2 text-sm",
                    activeTab === tab
                      ? "border-accent text-accent"
                      : "border-transparent text-text-muted",
                  )}
                >
                  {tab === "editor" ? "Редактор" : "Галерея"}
                </button>
              ))}
            </div>
          )}
          {activeTab === "editor" && (
            <PostBodyEditor
              value={form.body}
              onChange={(body) => updateForm({ ...form, body })}
            />
          )}
          {activeTab === "gallery" && !isNew && id && (
            <GalleryTab postId={Number(id)} />
          )}
        </div>
        {!focusMode && (
          <aside className="w-72 shrink-0 border-l border-border bg-surface p-4">
            <label className="mb-3 block text-sm">
              Статус
              <select
                value={form.status}
                onChange={(e) =>
                  setForm({ ...form, status: e.target.value as PostStatus })
                }
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              >
                <option value="draft">Черновик</option>
                <option value="ready_to_publish">Готов к публикации</option>
                {form.status === "published" && (
                  <option value="published">Опубликован</option>
                )}
              </select>
              {form.status !== "published" && (
                <p className="mt-1 text-xs text-text-muted">
                  «Опубликован» только через мультиканал.
                </p>
              )}
            </label>
            {!isNew && form.status === "published" && (
              <div className="mb-3 text-sm">
                {data?.post?.is_on_site ? (
                  <button
                    type="button"
                    className="text-red-600"
                    onClick={() => siteUnpublish.mutate()}
                  >
                    Убрать с сайта
                  </button>
                ) : (
                  <button
                    type="button"
                    className="text-green-700"
                    onClick={() => sitePublish.mutate()}
                  >
                    Опубликовать на сайте
                  </button>
                )}
              </div>
            )}
            <label className="mb-3 block text-sm">
              Обложка
              <input
                type="file"
                accept="image/*"
                disabled={isNew}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) coverMutation.mutate(file);
                }}
                className={cn(
                  "mt-1 block w-full text-xs",
                  publishReady && "rounded-lg border border-warning p-1",
                )}
              />
              {data?.post?.cover_image_url && (
                <img
                  src={data.post.cover_image_url}
                  alt="Cover"
                  className="mt-2 max-h-32 rounded-lg object-cover"
                />
              )}
            </label>
            <label className="mb-3 block text-sm">
              Краткое описание (SEO)
              <textarea
                value={form.short_description}
                onChange={(e) =>
                  setForm({ ...form, short_description: e.target.value })
                }
                rows={3}
                className={cn(
                  "mt-1 w-full rounded-lg border border-border px-2 py-1.5",
                  publishReady && "border-warning",
                )}
              />
            </label>
            <label className="block text-sm">
              Slug
              <input
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              />
            </label>
          </aside>
        )}
      </div>
      {historyOpen && (
        <div className="fixed inset-y-0 left-0 z-50 w-80 border-r border-border bg-surface p-4 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">История автосохранения</h2>
            <button type="button" onClick={() => setHistoryOpen(false)}>
              ✕
            </button>
          </div>
          <ul className="space-y-2 text-sm">
            {historyQuery.data?.items.map((item) => (
              <li key={item.id} className="rounded-lg border border-border p-2">
                <div className="text-xs text-text-muted">{item.created_at}</div>
                <div className="line-clamp-2">{item.preview}</div>
                <button
                  type="button"
                  className="mt-1 text-accent"
                  onClick={async () => {
                    const snap = await apiFetch<{
                      ok: boolean;
                      snapshot: {
                        title: string;
                        body: string;
                        short_description: string | null;
                      };
                    }>(`/posts/${id}/history/${item.id}/`);
                    if (snap.snapshot) {
                      setForm((f) => ({
                        ...f,
                        title: snap.snapshot.title,
                        body: snap.snapshot.body,
                        short_description: snap.snapshot.short_description ?? "",
                      }));
                      setHistoryOpen(false);
                    }
                  }}
                >
                  Восстановить
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
