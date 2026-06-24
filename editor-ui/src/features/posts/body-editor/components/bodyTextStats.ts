export function htmlToPlain(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return (div.textContent || "").replace(/\s+/g, " ").trim();
}

export function formatStatNum(n: number): string {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f");
}

export function useBasicBodyStats(html: string) {
  const plain = htmlToPlain(html);
  const words = plain ? plain.split(/\s+/).filter(Boolean).length : 0;
  return {
    chars: plain.length,
    charsNoSpaces: plain.replace(/ /g, "").length,
    words,
    minutes: Math.max(1, Math.round(words / 200)),
  };
}
