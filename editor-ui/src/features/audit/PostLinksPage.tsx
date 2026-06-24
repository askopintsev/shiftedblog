import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

export function PostLinksPage() {
  const { data } = useQuery({
    queryKey: ["post-links"],
    queryFn: () =>
      apiFetch<{
        ok: boolean;
        results: {
          id: number;
          post_title: string;
          network_slug: string;
          message_url: string;
          created_at: string;
        }[];
      }>("/audit/post-links/"),
  });

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold">Post links</h1>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead className="bg-surface-muted text-left">
            <tr>
              <th className="px-4 py-2">Пост</th>
              <th className="px-4 py-2">Сеть</th>
              <th className="px-4 py-2">URL</th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((row) => (
              <tr key={row.id} className="border-t border-border">
                <td className="px-4 py-2">{row.post_title}</td>
                <td className="px-4 py-2">{row.network_slug}</td>
                <td className="px-4 py-2">
                  {row.message_url ? (
                    <a href={row.message_url} target="_blank" rel="noreferrer">
                      {row.message_url}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
