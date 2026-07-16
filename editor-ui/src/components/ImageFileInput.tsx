import { useId, useRef, type RefObject } from "react";
import { ImagePlus, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ImageFileInputProps {
  buttonLabel?: string;
  hint?: string;
  disabled?: boolean;
  loading?: boolean;
  accept?: string;
  className?: string;
  inputRef?: RefObject<HTMLInputElement | null>;
  onFileSelect: (file: File) => void;
}

export function ImageFileInput({
  buttonLabel = "Выбрать изображение",
  hint = "JPEG, PNG или WebP",
  disabled = false,
  loading = false,
  accept = "image/*",
  className,
  inputRef,
  onFileSelect,
}: ImageFileInputProps) {
  const autoId = useId();
  const localRef = useRef<HTMLInputElement>(null);
  const ref = inputRef ?? localRef;
  const inactive = disabled || loading;

  return (
    <div className={cn("space-y-2", className)}>
      <input
        ref={ref}
        id={autoId}
        type="file"
        accept={accept}
        disabled={inactive}
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileSelect(file);
        }}
      />
      <label
        htmlFor={autoId}
        aria-disabled={inactive}
        className={cn(
          "inline-flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border",
          "bg-surface-muted px-4 py-3 text-sm font-medium text-text transition-colors",
          inactive
            ? "cursor-not-allowed opacity-60"
            : "cursor-pointer hover:border-accent hover:bg-accent/5 hover:text-accent",
        )}
      >
        {loading ? (
          <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden />
        ) : (
          <ImagePlus className="size-4 shrink-0" aria-hidden />
        )}
        <span>{loading ? "Загрузка…" : buttonLabel}</span>
      </label>
      {hint ? <p className="text-xs text-text-muted">{hint}</p> : null}
    </div>
  );
}
