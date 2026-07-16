import { useMemo } from "react";
import { formatStatNum, useBasicBodyStats } from "./bodyTextStats";

interface BodyBasicStatsRailProps {
  html: string;
}

export function BodyBasicStatsRail({ html }: BodyBasicStatsRailProps) {
  const stats = useMemo(() => useBasicBodyStats(html), [html]);

  return (
    <aside
      className="post-body-editor-basic-stats"
      aria-label="Статистика текста"
    >
      <div className="post-body-editor-basic-stats__line">
        Символов: <strong>{formatStatNum(stats.chars)}</strong>
      </div>
      <div className="post-body-editor-basic-stats__line">
        без пробелов: <strong>{formatStatNum(stats.charsNoSpaces)}</strong>
      </div>
      <div className="post-body-editor-basic-stats__line">
        Слов: <strong>{formatStatNum(stats.words)}</strong>
      </div>
      <div className="post-body-editor-basic-stats__line">
        Время: ~<strong>{stats.minutes}</strong> мин
      </div>
    </aside>
  );
}
