import { cn } from "@/lib/utils";

interface LoadingFallbackProps {
  className?: string;
  label?: string;
}

export function LoadingFallback({
  className,
  label = "Загрузка…",
}: LoadingFallbackProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-center text-sm text-text-muted",
        className,
      )}
    >
      {label}
    </div>
  );
}
