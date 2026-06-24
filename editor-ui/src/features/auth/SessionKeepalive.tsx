import { useEffect } from "react";
import { apiFetch } from "@/api/client";

const KEEPALIVE_MS = 25 * 60 * 1000;

export function SessionKeepalive() {
  useEffect(() => {
    const tick = () => {
      apiFetch<void>("/auth/session-keepalive/").catch(() => {});
    };
    const id = window.setInterval(tick, KEEPALIVE_MS);
    return () => window.clearInterval(id);
  }, []);
  return null;
}
