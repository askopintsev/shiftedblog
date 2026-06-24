import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/api/client";

function htmlToPlain(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return (div.textContent || "").replace(/\s+/g, " ").trim();
}

function formatNum(n: number): string {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f");
}

interface BodyStatsBarProps {
  html: string;
  onHtmlChange?: (html: string) => void;
}

export function BodyStatsBar({ html, onHtmlChange }: BodyStatsBarProps) {
  const [qualityLine, setQualityLine] = useState("");

  const stats = useMemo(() => {
    const plain = htmlToPlain(html);
    const words = plain ? plain.split(/\s+/).filter(Boolean).length : 0;
    return {
      chars: plain.length,
      charsNoSpaces: plain.replace(/ /g, "").length,
      words,
      minutes: Math.max(1, Math.round(words / 200)),
    };
  }, [html]);

  useEffect(() => {
    onHtmlChange?.(html);
  }, [html, onHtmlChange]);

  useEffect(() => {
    if (!html.trim()) {
      setQualityLine("");
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const data = await apiFetch<{
          ok: boolean;
          overall?: { score: number };
          scores?: Record<string, { score: number }>;
        }>("/posts/text-quality/", {
          method: "POST",
          body: JSON.stringify({
            schema_version: "1.0",
            locale: "ru-RU",
            content_format: "html",
            enable_extra_metrics: true,
            text: html,
          }),
        });
        if (data.ok && data.overall && data.scores) {
          setQualityLine(
            `Качество: ${data.overall.score} · Читаемость: ${data.scores.readability?.score ?? "-"} · Орфография: ${data.scores.orthography?.score ?? "-"}`,
          );
        }
      } catch {
        setQualityLine("");
      }
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [html]);

  return (
    <div className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-xs text-text-secondary">
      <div>
        Символов: <strong>{formatNum(stats.chars)}</strong> (без пробелов:{" "}
        <strong>{formatNum(stats.charsNoSpaces)}</strong>) · Слов:{" "}
        <strong>{formatNum(stats.words)}</strong> · Время чтения: ~
        <strong>{stats.minutes}</strong> мин
      </div>
      {qualityLine && <div className="mt-1">{qualityLine}</div>}
    </div>
  );
}
