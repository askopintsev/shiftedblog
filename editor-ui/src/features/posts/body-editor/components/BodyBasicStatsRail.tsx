import { useMemo } from "react";
import { useT } from "@/i18n";
import { formatStatNum, useBasicBodyStats } from "./bodyTextStats";

interface BodyBasicStatsRailProps {
  html: string;
}

export function BodyBasicStatsRail({ html }: BodyBasicStatsRailProps) {
  const t = useT();
  const stats = useMemo(() => useBasicBodyStats(html), [html]);

  return (
    <aside
      className="post-body-editor-basic-stats"
      aria-label={t("editor.stats.aria")}
    >
      <div className="post-body-editor-basic-stats__line">
        {t("editor.stats.chars")} <strong>{formatStatNum(stats.chars)}</strong>
      </div>
      <div className="post-body-editor-basic-stats__line">
        {t("editor.stats.noSpaces")}{" "}
        <strong>{formatStatNum(stats.charsNoSpaces)}</strong>
      </div>
      <div className="post-body-editor-basic-stats__line">
        {t("editor.stats.words")} <strong>{formatStatNum(stats.words)}</strong>
      </div>
      <div className="post-body-editor-basic-stats__line">
        {t("editor.stats.timeLabel")} ~<strong>{stats.minutes}</strong>{" "}
        {t("editor.stats.min")}
      </div>
    </aside>
  );
}
