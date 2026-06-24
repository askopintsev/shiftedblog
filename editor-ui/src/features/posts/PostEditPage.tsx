import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Focus, History } from "lucide-react";
import { apiFetch, apiUpload, ApiError } from "@/api/client";
import type { Category, PostDetail, PostStatus } from "@/api/types";
import { PostBodyEditorFallback } from "@/features/posts/body-editor/PostBodyEditorFallback";
import { GalleryTab } from "@/features/posts/components/GalleryTab";
import { ImageFileInput } from "@/components/ImageFileInput";
import {
  tryRestoreDraftFromLocal,
  useAutosave,
} from "@/features/posts/hooks/useAutosave";
import { formatApiErrors } from "@/lib/formatApiErrors";
import { mediaUrl } from "@/lib/mediaUrl";
import { publicUrl } from "@/lib/publicUrl";
import { slugifySegment } from "@/lib/slugifySegment";
import { formatTagsInput, parseTagsInput } from "@/lib/tagsInput";
import { cn } from "@/lib/utils";

type PostFormState = {
  title: string;
  body: string;
  status: PostStatus;
  short_description: string;
  cover_description: string;
  slug: string;
  category_id: number | null;
  tags: string;
};

function toApiPayload(form: PostFormState) {
  return {
    title: form.title,
    body: form.body,
    status: form.status,
    short_description: form.short_description,
    cover_description: form.cover_description,
    slug: form.slug,
    category_id: form.category_id,
    tags: parseTagsInput(form.tags),
  };
}

const PostBodyEditor = lazy(() =>
  import("@/features/posts/body-editor/PostBodyEditor").then((module) => ({
    default: module.PostBodyEditor,
  })),
);

export function PostEditPage() {
  const { id } = useParams();
  const isNew = !id || id === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [focusMode, setFocusMode] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"editor" | "gallery">("editor");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [coverError, setCoverError] = useState<string | null>(null);
  const draftRestored = useRef(false);
  const slugEditedRef = useRef(false);

  const { data, isLoading } = useQuery({
    queryKey: ["post", id],
    enabled: !isNew,
    queryFn: () =>
      apiFetch<{ ok: boolean; post: PostDetail }>(`/posts/${id}/`),
  });

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () =>
      apiFetch<{ ok: boolean; results: Category[] }>("/categories/"),
  });

  const [form, setForm] = useState<PostFormState>({
    title: "",
    body: "",
    status: "draft",
    short_description: "",
    cover_description: "",
    slug: "",
    category_id: null,
    tags: "",
  });

  useEffect(() => {
    if (data?.post) {
      slugEditedRef.current = true;
      setForm({
        title: data.post.title ?? "",
        body: data.post.body ?? "",
        status: data.post.status,
        short_description: data.post.short_description ?? "",
        cover_description: data.post.cover_description ?? "",
        slug: data.post.slug ?? "",
        category_id: data.post.category?.id ?? null,
        tags: formatTagsInput(data.post.tags ?? []),
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
  const getPayload = useCallback(() => toApiPayload(formRef.current), []);

  const { scheduleAutosave } = useAutosave(id, isNew, getPayload, () =>
    setSavedAt(new Date()),
  );

  const saveMutation = useMutation({
    mutationFn: async (payload: PostFormState) => {
      const body = JSON.stringify(toApiPayload(payload));
      if (isNew) {
        return apiFetch<{ ok: boolean; post: PostDetail }>("/posts/", {
          method: "POST",
          body,
        });
      }
      return apiFetch<{ ok: boolean; post: PostDetail }>(`/posts/${id}/`, {
        method: "PATCH",
        body,
      });
    },
    onSuccess: (res) => {
      setSaveError(null);
      setSavedAt(new Date());
      queryClient.invalidateQueries({ queryKey: ["posts"] });
      if (isNew && res.post?.id) {
        navigate(`/posts/${res.post.id}`, { replace: true });
      } else if (id) {
        queryClient.invalidateQueries({ queryKey: ["post", id] });
      }
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        setSaveError(formatApiErrors(error.payload));
        return;
      }
      setSaveError("Не удалось сохранить.");
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
      setCoverError(null);
      queryClient.invalidateQueries({ queryKey: ["post", id] });
      setSavedAt(new Date());
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        setCoverError(formatApiErrors(error.payload));
        return;
      }
      setCoverError("Не удалось загрузить обложку.");
    },
  });

  const clearCoverMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ ok: boolean; post: PostDetail }>(`/posts/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ cover_image_clear: true }),
      }),
    onSuccess: () => {
      setCoverError(null);
      queryClient.invalidateQueries({ queryKey: ["post", id] });
      setSavedAt(new Date());
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        setCoverError(formatApiErrors(error.payload));
        return;
      }
      setCoverError("Не удалось очистить обложку.");
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
        saveMutation.mutate(formRef.current);
      }
      if (e.key === "Escape" && focusMode) {
        setFocusMode(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusMode, saveMutation]);

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
    (next: PostFormState) => {
      setForm(next);
      scheduleAutosave(next.body);
    },
    [scheduleAutosave],
  );

  const updateTitle = useCallback(
    (title: string) => {
      setSaveError(null);
      updateForm({
        ...formRef.current,
        title,
        slug: slugEditedRef.current
          ? formRef.current.slug
          : slugifySegment(title),
      });
    },
    [updateForm],
  );

  const updateSlug = useCallback((slug: string) => {
    slugEditedRef.current = true;
    setSaveError(null);
    setForm((current) => ({ ...current, slug }));
  }, []);

  const saveAndReturnToPosts = useCallback(async () => {
    try {
      await saveMutation.mutateAsync(formRef.current);
      navigate("/posts");
    } catch {
      /* saveMutation.onError renders the error message */
    }
  }, [navigate, saveMutation]);

  if (!isNew && isLoading) {
    return <div className="p-6">Загрузка…</div>;
  }

  const publishReady =
    form.status === "ready_to_publish" || form.status === "published";

  return (
    <div
      className={cn(
        "flex min-h-full",
        focusMode &&
          "fixed inset-0 z-40 min-h-screen overflow-y-auto bg-surface-muted",
      )}
    >
      {!focusMode && (
        <div className="flex w-16 shrink-0 flex-col items-center gap-3 border-r border-border bg-surface px-2 py-4">
          <button
            type="button"
            title="К списку постов"
            aria-label="К списку постов"
            disabled={saveMutation.isPending}
            className="inline-flex size-10 items-center justify-center rounded-xl border border-border bg-surface-muted text-text-secondary shadow-sm transition hover:border-accent hover:bg-accent/5 hover:text-accent disabled:cursor-not-allowed disabled:opacity-60"
            onClick={() => {
              void saveAndReturnToPosts();
            }}
          >
            <ArrowLeft className="size-4" aria-hidden />
          </button>
          {!isNew && (
            <button
              type="button"
              title="История"
              aria-label="История"
              className="inline-flex size-10 items-center justify-center rounded-xl border border-border bg-surface-muted text-text-secondary shadow-sm transition hover:border-accent hover:bg-accent/5 hover:text-accent"
              onClick={() => setHistoryOpen(true)}
            >
              <History className="size-4" aria-hidden />
            </button>
          )}
          <button
            type="button"
            title="Фокус"
            aria-label="Фокус"
            className="inline-flex size-10 items-center justify-center rounded-xl border border-border bg-surface-muted text-text-secondary shadow-sm transition hover:border-accent hover:bg-accent/5 hover:text-accent"
            onClick={() => setFocusMode(true)}
          >
            <Focus className="size-4" aria-hidden />
          </button>
        </div>
      )}
      {focusMode && (
        <div className="fixed left-1/2 top-4 z-50 -translate-x-1/2">
          <button
            type="button"
            className="rounded-full border border-border bg-surface/95 px-4 py-2 text-sm text-text-secondary shadow-lg backdrop-blur transition hover:border-accent hover:text-accent"
            onClick={() => setFocusMode(false)}
          >
            Выйти из фокуса · Esc
          </button>
        </div>
      )}
      <div className="flex min-w-0 flex-1">
        <div className="flex-1 p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div className="min-w-0 text-sm text-text-muted">
              {saveError ? (
                <span className="text-red-600">{saveError}</span>
              ) : savedAt ? (
                `Сохранено ${savedAt.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}`
              ) : (
                "Не сохранено"
              )}
            </div>
            <div className="flex gap-2">
              {!isNew && data?.post?.draft_preview_url && (
                <a
                  href={publicUrl(data.post.draft_preview_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-9 items-center rounded-lg border border-border px-3 text-sm text-accent hover:bg-surface-muted"
                >
                  Превью
                </a>
              )}
              {!isNew && form.status === "ready_to_publish" && (
                <Link
                  to="/publish"
                  className="inline-flex h-9 items-center rounded-lg border border-border px-3 text-sm text-accent hover:bg-surface-muted"
                >
                  Публикация →
                </Link>
              )}
              <button
                type="button"
                disabled={saveMutation.isPending}
                onClick={() => saveMutation.mutate(formRef.current)}
                className="inline-flex h-9 items-center rounded-lg bg-accent px-4 text-sm text-white disabled:opacity-60"
              >
                {saveMutation.isPending ? "Сохранение…" : "Сохранить"}
              </button>
            </div>
          </div>
          <input
            value={form.title}
            onChange={(e) => updateTitle(e.target.value)}
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
                  {tab === "editor" ? "Редактор" : "Галерии"}
                </button>
              ))}
            </div>
          )}
          {activeTab === "editor" && (
            <section aria-label="Текст поста" className="min-h-[420px]">
              <Suspense fallback={<PostBodyEditorFallback />}>
                <PostBodyEditor
                  value={form.body}
                  onChange={(body) => updateForm({ ...form, body })}
                  galleryImages={data?.post?.gallery_images ?? []}
                  postId={!isNew && id ? Number(id) : undefined}
                  onGalleryUploaded={() => {
                    if (!id) return;
                    queryClient.invalidateQueries({ queryKey: ["post", id] });
                    queryClient.invalidateQueries({
                      queryKey: ["post-gallery", Number(id)],
                    });
                  }}
                />
              </Suspense>
            </section>
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
            <div className="mb-3">
              <div className="mb-1 text-sm">Обложка</div>
              {isNew ? (
                <p className="rounded-lg border border-dashed border-border bg-surface-muted px-3 py-3 text-xs text-text-muted">
                  Сохраните пост, чтобы загрузить обложку.
                </p>
              ) : (
                <>
                  <ImageFileInput
                    buttonLabel={
                      data?.post?.cover_image_url
                        ? "Заменить обложку"
                        : "Загрузить обложку"
                    }
                    hint="JPEG, PNG или WebP"
                    loading={coverMutation.isPending}
                    className={cn(publishReady && "rounded-lg ring-1 ring-warning")}
                    onFileSelect={(file) => coverMutation.mutate(file)}
                  />
                  {coverError ? (
                    <p className="mt-2 text-xs text-red-600">{coverError}</p>
                  ) : null}
                </>
              )}
              {data?.post?.cover_image_url && (
                <div className="mt-2 space-y-2">
                  <img
                    src={mediaUrl(data.post.cover_image_url)}
                    alt="Cover"
                    className="max-h-32 rounded-lg object-cover"
                  />
                  <button
                    type="button"
                    disabled={clearCoverMutation.isPending}
                    className="text-xs text-red-600 disabled:opacity-60"
                    onClick={() => clearCoverMutation.mutate()}
                  >
                    {clearCoverMutation.isPending
                      ? "Очищаем…"
                      : "Очистить обложку"}
                  </button>
                </div>
              )}
            </div>
            <label className="mb-3 block text-sm">
              Описание обложки
              <textarea
                value={form.cover_description}
                onChange={(e) =>
                  setForm({ ...form, cover_description: e.target.value })
                }
                rows={2}
                placeholder="Краткое описание изображения"
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              />
              <p className="mt-1 text-xs text-text-muted">
                Используется как описание изображения обложки.
              </p>
            </label>
            <label className="mb-3 block text-sm">
              Краткое описание
              <textarea
                value={form.short_description}
                onChange={(e) =>
                  setForm({ ...form, short_description: e.target.value })
                }
                rows={3}
                placeholder="Короткий анонс поста"
                className={cn(
                  "mt-1 w-full rounded-lg border border-border px-2 py-1.5",
                  publishReady && "border-warning",
                )}
              />
              <p className="mt-1 text-xs text-text-muted">
                Используется для SEO, карточек и превью в соцсетях.
              </p>
            </label>
            <label className="mb-3 block text-sm">
              Slug
              <input
                value={form.slug}
                onChange={(e) => updateSlug(e.target.value)}
                placeholder="Заполнится из заголовка"
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              />
            </label>
            <label className="mb-3 block text-sm">
              Категория
              <select
                value={form.category_id ?? ""}
                onChange={(e) => {
                  setSaveError(null);
                  setForm({
                    ...form,
                    category_id: e.target.value ? Number(e.target.value) : null,
                  });
                }}
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              >
                <option value="">Без категории</option>
                {(categoriesQuery.data?.results ?? []).map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              {categoriesQuery.isLoading ? (
                <p className="mt-1 text-xs text-text-muted">Загрузка категорий…</p>
              ) : null}
            </label>
            <label className="block text-sm">
              Теги
              <input
                value={form.tags}
                onChange={(e) => {
                  setSaveError(null);
                  setForm({ ...form, tags: e.target.value });
                }}
                placeholder="news, django"
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              />
              <p className="mt-1 text-xs text-text-muted">
                Введите теги через запятую.
              </p>
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
