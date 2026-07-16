import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface EditorToolbarButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  active?: boolean;
  children: ReactNode;
}

export const EditorToolbarButton = forwardRef<
  HTMLButtonElement,
  EditorToolbarButtonProps
>(function EditorToolbarButton(
  { icon, active, children, className, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={cn(
        "inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg border-2 border-border bg-surface px-3 py-1.5 text-[0.8125rem] font-medium text-text-primary shadow-sm transition",
        "hover:border-text-muted hover:bg-surface-muted",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        active &&
          "border-accent bg-accent/5 shadow-[0_0_0_1px] shadow-accent/25",
        className,
      )}
      {...props}
    >
      {icon ? (
        <span
          className="flex shrink-0 items-center text-base leading-none"
          aria-hidden
        >
          {icon}
        </span>
      ) : null}
      <span className="whitespace-nowrap">{children}</span>
    </button>
  );
});
