import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/api/client";
import { useI18n } from "@/i18n";
import { formatStatNum, htmlToPlain } from "./bodyTextStats";

type TextQualityResponse = {
  ok: boolean;
  overall?: { score: number };
  scores?: Record<string, { score: number }>;
};

function metricScore(
  scores: TextQualityResponse["scores"],
  key: string,
): number | "-" {
  return scores?.[key]?.score ?? "-";
}

interface BodyStatsBarProps {
  html: string;
  onHtmlChange?: (html: string) => void;
}

export function BodyStatsBar({ html, onHtmlChange }: BodyStatsBarProps) {
  const { t, bcp47 } = useI18n();
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
        const data = await apiFetch<TextQualityResponse>("/posts/text-quality/", {
          method: "POST",
          body: JSON.stringify({
            schema_version: "1.0",
            locale: bcp47,
            content_format: "html",
            enable_extra_metrics: true,
            text: html,
          }),
        });
        if (!data.ok || !data.overall || !data.scores) {
          setQualityLine("");
          return;
        }
        setQualityLine(
          t("editor.quality.line", {
            overall: data.overall.score,
            readability: metricScore(data.scores, "readability"),
            spam: metricScore(data.scores, "spam_words"),
            waterness: metricScore(data.scores, "waterness"),
            orthography: metricScore(data.scores, "orthography"),
            punctuation: metricScore(data.scores, "punctuation"),
            typos: metricScore(data.scores, "typos"),
          }),
        );
      } catch {
        setQualityLine("");
      }
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [html, bcp47, t]);

  return (
    <div className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-xs text-text-secondary">
      <div>
        {t("editor.stats.chars")}{" "}
        <strong>{formatStatNum(stats.chars)}</strong> (
        {t("editor.stats.noSpaces")}{" "}
        <strong>{formatStatNum(stats.charsNoSpaces)}</strong>) ·{" "}
        {t("editor.stats.words")} <strong>{formatStatNum(stats.words)}</strong>{" "}
        · {t("editor.stats.readingTime")} ~
        <strong>{stats.minutes}</strong> {t("editor.stats.min")}
      </div>
      {qualityLine && <div className="mt-1">{qualityLine}</div>}
    </div>
  );
}
