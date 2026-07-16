import { useEffect, useState, type RefObject } from "react";

function findScrollRoot(element: HTMLElement): Element | null {
  let node: HTMLElement | null = element.parentElement;
  while (node) {
    const { overflowY } = window.getComputedStyle(node);
    if (overflowY === "auto" || overflowY === "scroll") {
      return node;
    }
    node = node.parentElement;
  }
  return null;
}

export function useElementVisible(
  targetRef: RefObject<HTMLElement | null>,
): boolean {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const target = targetRef.current;
    if (!target) return;

    const scrollRoot = findScrollRoot(target);
    const observer = new IntersectionObserver(
      ([entry]) => {
        setVisible(entry.isIntersecting);
      },
      {
        root: scrollRoot,
        threshold: 0,
      },
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [targetRef]);

  return visible;
}
