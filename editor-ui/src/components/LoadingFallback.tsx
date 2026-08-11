import { cn } from "@/lib/utils";
import { useT } from "@/i18n";

interface LoadingFallbackProps {
  className?: string;
  label?: string;
}

export function LoadingFallback({ className, label }: LoadingFallbackProps) {
  const t = useT();
  return (
    <div
      className={cn(
        "flex items-center justify-center text-sm text-text-muted",
        className,
      )}
    >
      {label ?? t("common.loading")}
    </div>
  );
}
