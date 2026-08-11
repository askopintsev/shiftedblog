import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useT } from "@/i18n";
import {
  applyTagSuggestion,
  filterTagSuggestions,
} from "@/lib/tagsInput";
import { cn } from "@/lib/utils";

type TagsInputProps = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
};

export function TagsInput({ value, onChange, className }: TagsInputProps) {
  const t = useT();
  const listId = useId();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const tagsQuery = useQuery({
    queryKey: ["tags"],
    queryFn: () =>
      apiFetch<{ ok: boolean; results: string[] }>("/tags/"),
    staleTime: 60_000,
  });

  const suggestions = useMemo(
    () => filterTagSuggestions(tagsQuery.data?.results ?? [], value),
    [tagsQuery.data?.results, value],
  );

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [value]);

  useEffect(() => {
    setActiveIndex(0);
    setOpen(suggestions.length > 0);
  }, [suggestions]);

  function pickSuggestion(tag: string) {
    onChange(applyTagSuggestion(value, tag));
    setOpen(false);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        rows={2}
        role="combobox"
        aria-expanded={open && suggestions.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        placeholder={t("postEdit.tagsPlaceholder")}
        className={cn(
          "mt-1 min-h-16 w-full resize-none overflow-hidden rounded-lg border border-border px-2 py-1.5",
          className,
        )}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => {
          if (suggestions.length > 0) setOpen(true);
        }}
        onBlur={() => {
          // Allow click on suggestion before closing.
          window.setTimeout(() => setOpen(false), 120);
        }}
        onKeyDown={(e) => {
          if (!open || suggestions.length === 0) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActiveIndex((i) => (i + 1) % suggestions.length);
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActiveIndex(
              (i) => (i - 1 + suggestions.length) % suggestions.length,
            );
          } else if (e.key === "Enter" || e.key === "Tab") {
            e.preventDefault();
            pickSuggestion(suggestions[activeIndex] ?? suggestions[0]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open && suggestions.length > 0 ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-border bg-surface py-1 shadow-lg"
        >
          {suggestions.map((tag, index) => (
            <li key={tag} role="option" aria-selected={index === activeIndex}>
              <button
                type="button"
                className={cn(
                  "block w-full px-3 py-1.5 text-left text-sm",
                  index === activeIndex
                    ? "bg-accent text-white"
                    : "hover:bg-surface-muted",
                )}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pickSuggestion(tag)}
              >
                {tag}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {tagsQuery.isLoading ? (
        <p className="mt-1 text-xs text-text-muted">
          {t("postEdit.loadingTags")}
        </p>
      ) : null}
    </div>
  );
}
