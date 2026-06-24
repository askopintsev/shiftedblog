import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiUpload } from "@/api/client";
import type { GalleryImage } from "@/api/types";

interface GalleryTabProps {
  postId: number;
}

export function GalleryTab({ postId }: GalleryTabProps) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [galleryKey, setGalleryKey] = useState(1);
  const [caption, setCaption] = useState("");

  const { data } = useQuery({
    queryKey: ["post-gallery", postId],
    queryFn: () =>
      apiFetch<{ ok: boolean; results: GalleryImage[] }>(
        `/posts/${postId}/gallery/`,
      ),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("image", file);
      fd.append("gallery_key", String(galleryKey));
      if (caption) fd.append("caption", caption);
      return apiUpload<{ ok: boolean; gallery: GalleryImage }>(
        `/posts/${postId}/gallery/`,
        fd,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["post-gallery", postId] });
      queryClient.invalidateQueries({ queryKey: ["post", String(postId)] });
      setCaption("");
      if (fileRef.current) fileRef.current.value = "";
    },
  });

  const patchMutation = useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: number;
      patch: { caption?: string; gallery_key?: number; order?: number };
    }) =>
      apiFetch(`/posts/${postId}/gallery/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["post-gallery", postId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/posts/${postId}/gallery/${id}/`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["post-gallery", postId] });
      queryClient.invalidateQueries({ queryKey: ["post", String(postId)] });
    },
  });

  const images = data?.results ?? [];

  return (
    <div className="mt-6 rounded-xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-medium">Галерея</h2>
        <p className="text-xs text-text-muted">
          Вставьте в текст маркер <code>[gallery:N]</code>
        </p>
      </div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Группа N
          <input
            type="number"
            min={1}
            value={galleryKey}
            onChange={(e) => setGalleryKey(Number(e.target.value) || 1)}
            className="ml-2 w-16 rounded-lg border border-border px-2 py-1"
          />
        </label>
        <label className="text-sm">
          Подпись
          <input
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            className="ml-2 rounded-lg border border-border px-2 py-1"
          />
        </label>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="text-sm"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadMutation.mutate(file);
          }}
        />
      </div>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {images.map((img) => (
          <li key={img.id} className="rounded-lg border border-border p-2">
            <img
              src={img.image_url}
              alt={img.caption || `Gallery ${img.gallery_key}`}
              className="mb-2 max-h-40 w-full rounded object-cover"
            />
            <div className="flex items-center gap-2 text-xs">
              <span className="rounded bg-surface-muted px-1.5 py-0.5">
                [gallery:{img.gallery_key}]
              </span>
              <input
                defaultValue={img.caption}
                placeholder="Подпись"
                className="flex-1 rounded border border-border px-1 py-0.5"
                onBlur={(e) => {
                  if (e.target.value !== img.caption) {
                    patchMutation.mutate({
                      id: img.id,
                      patch: { caption: e.target.value },
                    });
                  }
                }}
              />
              <button
                type="button"
                className="text-red-600"
                onClick={() => deleteMutation.mutate(img.id)}
              >
                Удалить
              </button>
            </div>
          </li>
        ))}
      </ul>
      {!images.length && (
        <p className="text-sm text-text-muted">Изображений пока нет.</p>
      )}
    </div>
  );
}
