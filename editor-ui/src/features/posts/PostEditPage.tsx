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
import { useI18n } from "@/i18n";
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

function postToForm(post: PostDetail): PostFormState {
  return {
    title: post.title ?? "",
    body: post.body ?? "",
    status: post.status,
    short_description: post.short_description ?? "",
    cover_description: post.cover_description ?? "",
    slug: post.slug ?? "",
    category_id: post.category?.id ?? null,
    tags: formatTagsInput(post.tags ?? []),
  };
}

const emptyFormState = (): PostFormState => ({
  title: "",
  body: "",
  status: "draft",
  short_description: "",
  cover_description: "",
  slug: "",
  category_id: null,
  tags: "",
});

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
  const { t, bcp47 } = useI18n();
  const [focusMode, setFocusMode] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"editor" | "gallery">("editor");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [coverError, setCoverError] = useState<string | null>(null);
  const draftRestored = useRef(false);
  const slugEditedRef = useRef(false);
  const hydratedPostIdRef = useRef<string | null>(null);
  const tagsTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const saveBarRef = useRef<HTMLDivElement | null>(null);
  const [toolbarStickyTop, setToolbarStickyTop] = useState(0);
  const [isFormReady, setIsFormReady] = useState(isNew);

  const { data, isLoading } = useQuery({
    queryKey: ["post", id],
    enabled: !isNew,
    queryFn: () =>
      apiFetch<{ ok: boolean; post: PostDetail }>(`/posts/${id}/`),
  });

  const post = data?.post;
  const postMatchesRoute =
    isNew || (post != null && String(post.id) === String(id));

  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: () =>
      apiFetch<{ ok: boolean; results: Category[] }>("/categories/"),
  });

  const [form, setForm] = useState<PostFormState>(emptyFormState);

  useEffect(() => {
    draftRestored.current = false;
    hydratedPostIdRef.current = null;
    slugEditedRef.current = false;
    setIsFormReady(isNew);
    if (isNew) {
      setForm(emptyFormState());
    }
  }, [id, isNew]);

  useEffect(() => {
    if (isNew || !id || !post || !postMatchesRoute) return;
    if (hydratedPostIdRef.current === id) return;

    hydratedPostIdRef.current = id;
    slugEditedRef.current = true;

    let nextForm = postToForm(post);
    if (!draftRestored.current) {
      draftRestored.current = true;
      const restored = tryRestoreDraftFromLocal(id, post.body ?? "");
      if (restored) {
        nextForm = { ...nextForm, body: restored };
      }
    }

    setForm(nextForm);
    setIsFormReady(true);
  }, [id, isNew, post, postMatchesRoute]);

  useEffect(() => {
    const textarea = tagsTextareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [form.tags]);

  useEffect(() => {
    const saveBar = saveBarRef.current;
    if (!saveBar) return;

    const updateToolbarStickyTop = () => {
      setToolbarStickyTop(saveBar.getBoundingClientRect().height);
    };

    updateToolbarStickyTop();
    const observer = new ResizeObserver(updateToolbarStickyTop);
    observer.observe(saveBar);
    return () => observer.disconnect();
  }, [focusMode, saveError, savedAt, isNew, form.status]);

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
      setSaveError(t("postEdit.saveFailed"));
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
      setCoverError(t("postEdit.coverUploadFailed"));
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
      setCoverError(t("postEdit.coverClearFailed"));
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
    (patch: Partial<PostFormState>) => {
      setForm((current) => {
        const next = { ...current, ...patch };
        if (patch.body !== undefined && patch.body !== current.body) {
          scheduleAutosave(next.body);
        }
        return next;
      });
    },
    [scheduleAutosave],
  );

  const updateBody = useCallback(
    (body: string) => {
      setForm((current) => {
        if (current.body === body) return current;
        scheduleAutosave(body);
        return { ...current, body };
      });
    },
    [scheduleAutosave],
  );

  const updateTitle = useCallback(
    (title: string) => {
      setSaveError(null);
      setForm((current) => ({
        ...current,
        title,
        slug: slugEditedRef.current ? current.slug : slugifySegment(title),
      }));
    },
    [],
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

  if (!isNew && (isLoading || !isFormReady || !postMatchesRoute)) {
    return <div className="p-6">{t("postEdit.loading")}</div>;
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
            title={t("postEdit.backToList")}
            aria-label={t("postEdit.backToList")}
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
              title={t("postEdit.history")}
              aria-label={t("postEdit.history")}
              className="inline-flex size-10 items-center justify-center rounded-xl border border-border bg-surface-muted text-text-secondary shadow-sm transition hover:border-accent hover:bg-accent/5 hover:text-accent"
              onClick={() => setHistoryOpen(true)}
            >
              <History className="size-4" aria-hidden />
            </button>
          )}
          <button
            type="button"
            title={t("postEdit.focus")}
            aria-label={t("postEdit.focus")}
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
            {t("postEdit.exitFocus")}
          </button>
        </div>
      )}
      <div className="flex min-w-0 flex-1">
        <div className="flex-1 p-6">
          <div
            ref={saveBarRef}
            className="sticky top-0 z-40 -mx-6 mb-4 flex items-center justify-between gap-4 border-b border-border bg-surface/95 px-6 py-2 backdrop-blur supports-[backdrop-filter]:bg-surface/85"
          >
            <div className="min-w-0 text-sm text-text-muted">
              {saveError ? (
                <span className="text-red-600">{saveError}</span>
              ) : savedAt ? (
                t("postEdit.savedAt", {
                  time: savedAt.toLocaleTimeString(bcp47, {
                    hour: "2-digit",
                    minute: "2-digit",
                  }),
                })
              ) : (
                t("postEdit.notSaved")
              )}
            </div>
            <div className="flex gap-2">
              {!isNew && post?.draft_preview_url && (
                <a
                  href={publicUrl(post.draft_preview_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-9 items-center rounded-lg border border-border px-3 text-sm text-accent hover:bg-surface-muted"
                >
                  {t("postEdit.preview")}
                </a>
              )}
              {!isNew && form.status === "ready_to_publish" && (
                <Link
                  to="/publish"
                  className="inline-flex h-9 items-center rounded-lg border border-border px-3 text-sm text-accent hover:bg-surface-muted"
                >
                  {t("postEdit.publishLink")}
                </Link>
              )}
              <button
                type="button"
                disabled={saveMutation.isPending}
                onClick={() => saveMutation.mutate(formRef.current)}
                className="inline-flex h-9 items-center rounded-lg bg-accent px-4 text-sm text-white disabled:opacity-60"
              >
                {saveMutation.isPending
                  ? t("postEdit.saving")
                  : t("common.save")}
              </button>
            </div>
          </div>
          <input
            value={form.title}
            onChange={(e) => updateTitle(e.target.value)}
            placeholder={t("postEdit.titlePlaceholder")}
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
                  {tab === "editor"
                    ? t("postEdit.tabEditor")
                    : t("postEdit.tabGallery")}
                </button>
              ))}
            </div>
          )}
          {activeTab === "editor" && (
            <section aria-label={t("postEdit.bodyAria")} className="min-h-[420px]">
              <Suspense fallback={<PostBodyEditorFallback />}>
                <PostBodyEditor
                  key={id}
                  value={form.body}
                  onChange={updateBody}
                  toolbarStickyTop={toolbarStickyTop}
                  galleryImages={post?.gallery_images ?? []}
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
              {t("postEdit.status")}
              <select
                value={form.status}
                onChange={(e) =>
                  updateForm({ status: e.target.value as PostStatus })
                }
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              >
                <option value="draft">{t("postEdit.statusDraft")}</option>
                <option value="ready_to_publish">
                  {t("postEdit.statusReady")}
                </option>
                {form.status === "published" && (
                  <option value="published">
                    {t("postEdit.statusPublished")}
                  </option>
                )}
              </select>
              {form.status !== "published" && (
                <p className="mt-1 text-xs text-text-muted">
                  {t("postEdit.publishedOnlyMultichannel")}
                </p>
              )}
            </label>
            {!isNew && form.status === "published" && (
              <div className="mb-3 text-sm">
                {post?.is_on_site ? (
                  <button
                    type="button"
                    className="text-red-600"
                    onClick={() => siteUnpublish.mutate()}
                  >
                    {t("postEdit.removeFromSite")}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="text-green-700"
                    onClick={() => sitePublish.mutate()}
                  >
                    {t("postEdit.publishOnSite")}
                  </button>
                )}
              </div>
            )}
            <div className="mb-3">
              <div className="mb-1 text-sm">{t("postEdit.cover")}</div>
              {isNew ? (
                <p className="rounded-lg border border-dashed border-border bg-surface-muted px-3 py-3 text-xs text-text-muted">
                  {t("postEdit.coverSaveFirst")}
                </p>
              ) : (
                <>
                  <ImageFileInput
                    buttonLabel={
                      post?.cover_image_url
                        ? t("postEdit.replaceCover")
                        : t("postEdit.uploadCover")
                    }
                    hint={t("common.imageFormats")}
                    loading={coverMutation.isPending}
                    className={cn(publishReady && "rounded-lg ring-1 ring-warning")}
                    onFileSelect={(file) => coverMutation.mutate(file)}
                  />
                  {coverError ? (
                    <p className="mt-2 text-xs text-red-600">{coverError}</p>
                  ) : null}
                </>
              )}
              {post?.cover_image_url && (
                <div className="mt-2 space-y-2">
                  <img
                    src={mediaUrl(post.cover_image_url)}
                    alt={t("postEdit.coverAlt")}
                    className="max-h-32 rounded-lg object-cover"
                  />
                  <button
                    type="button"
                    disabled={clearCoverMutation.isPending}
                    className="text-xs text-red-600 disabled:opacity-60"
                    onClick={() => clearCoverMutation.mutate()}
                  >
                    {clearCoverMutation.isPending
                      ? t("postEdit.clearingCover")
                      : t("postEdit.clearCover")}
                  </button>
                </div>
              )}
            </div>
            <label className="mb-3 block text-sm">
              {t("postEdit.coverDescription")}
              <textarea
                value={form.cover_description}
                onChange={(e) =>
                  updateForm({ cover_description: e.target.value })
                }
                rows={2}
                placeholder={t("postEdit.coverDescriptionPlaceholder")}
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              />
              <p className="mt-1 text-xs text-text-muted">
                {t("postEdit.coverDescriptionHelp")}
              </p>
            </label>
            <label className="mb-3 block text-sm">
              {t("postEdit.shortDescription")}
              <textarea
                value={form.short_description}
                onChange={(e) =>
                  updateForm({ short_description: e.target.value })
                }
                rows={3}
                placeholder={t("postEdit.shortDescriptionPlaceholder")}
                className={cn(
                  "mt-1 w-full rounded-lg border border-border px-2 py-1.5",
                  publishReady && "border-warning",
                )}
              />
              <p className="mt-1 text-xs text-text-muted">
                {t("postEdit.shortDescriptionHelp")}
              </p>
            </label>
            <label className="mb-3 block text-sm">
              {t("postEdit.slug")}
              <input
                value={form.slug}
                onChange={(e) => updateSlug(e.target.value)}
                placeholder={t("postEdit.slugPlaceholder")}
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              />
            </label>
            <label className="mb-3 block text-sm">
              {t("postEdit.category")}
              <select
                value={form.category_id ?? ""}
                onChange={(e) => {
                  setSaveError(null);
                  updateForm({
                    category_id: e.target.value ? Number(e.target.value) : null,
                  });
                }}
                className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
              >
                <option value="">{t("postEdit.noCategory")}</option>
                {(categoriesQuery.data?.results ?? []).map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              {categoriesQuery.isLoading ? (
                <p className="mt-1 text-xs text-text-muted">
                  {t("postEdit.loadingCategories")}
                </p>
              ) : null}
            </label>
            <label className="block text-sm">
              {t("postEdit.tags")}
              <textarea
                ref={tagsTextareaRef}
                value={form.tags}
                onChange={(e) => {
                  setSaveError(null);
                  updateForm({ tags: e.target.value });
                }}
                rows={2}
                placeholder={t("postEdit.tagsPlaceholder")}
                className="mt-1 min-h-16 w-full resize-none overflow-hidden rounded-lg border border-border px-2 py-1.5"
              />
              <p className="mt-1 text-xs text-text-muted">
                {t("postEdit.tagsHelp")}
              </p>
            </label>
          </aside>
        )}
      </div>
      {historyOpen && (
        <div className="fixed inset-y-0 left-0 z-50 w-80 border-r border-border bg-surface p-4 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">{t("postEdit.historyTitle")}</h2>
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
                  {t("postEdit.restore")}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
