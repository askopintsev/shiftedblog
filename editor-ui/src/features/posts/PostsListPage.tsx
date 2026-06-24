import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { apiFetch } from "@/api/client";
import type { PostListItem, PostStatus } from "@/api/types";
import { cn } from "@/lib/utils";

const statusLabels: Record<PostStatus, string> = {
  draft: "Черновик",
  ready_to_publish: "Готов",
  published: "Опубликован",
};

const statusColors: Record<PostStatus, string> = {
  draft: "bg-gray-100 text-gray-700",
  ready_to_publish: "bg-orange-100 text-orange-800",
  published: "bg-green-100 text-green-800",
};

export function PostsListPage() {
  const [status, setStatus] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["posts", status],
    queryFn: () => {
      const q = status ? `?status=${status}` : "";
      return apiFetch<{ ok: boolean; results: PostListItem[] }>(`/posts${q}`);
    },
  });

  const sitePublish = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/posts/${id}/site-publish/`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
  });

  const siteUnpublish = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/posts/${id}/site-unpublish/`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["posts"] }),
  });

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Посты</h1>
        <Link
          to="/posts/new"
          className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm text-white"
        >
          <Plus className="h-4 w-4" />
          Новый пост
        </Link>
      </div>
      <div className="mb-4 flex gap-2">
        {["", "draft", "ready_to_publish", "published"].map((s) => (
          <button
            key={s || "all"}
            type="button"
            onClick={() => setStatus(s)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm",
              status === s ? "bg-accent text-white" : "bg-surface border border-border",
            )}
          >
            {s ? statusLabels[s as PostStatus] : "Все"}
          </button>
        ))}
      </div>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted text-left text-text-muted">
            <tr>
              <th className="px-4 py-3">Заголовок</th>
              <th className="px-4 py-3">Статус</th>
              <th className="px-4 py-3">Обновлён</th>
              <th className="px-4 py-3">Действия</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-text-muted">
                  Загрузка…
                </td>
              </tr>
            )}
            {data?.results.map((post) => (
              <tr key={post.id} className="border-t border-border">
                <td className="px-4 py-3">
                  <Link to={`/posts/${post.id}`} className="font-medium hover:underline">
                    {post.title || `#${post.id}`}
                  </Link>
                  <div className="text-xs text-text-muted">{post.slug}</div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-medium",
                      statusColors[post.status],
                    )}
                  >
                    {statusLabels[post.status]}
                  </span>
                </td>
                <td className="px-4 py-3 text-text-muted">
                  {new Date(post.updated).toLocaleString("ru-RU")}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <Link to={`/posts/${post.id}`} className="text-accent">
                      Редактировать
                    </Link>
                    {post.status === "published" && !post.is_on_site && (
                      <button
                        type="button"
                        className="text-green-700"
                        onClick={() => sitePublish.mutate(post.id)}
                      >
                        На сайт
                      </button>
                    )}
                    {post.is_on_site && (
                      <button
                        type="button"
                        className="text-red-600"
                        onClick={() => siteUnpublish.mutate(post.id)}
                      >
                        С сайта
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
