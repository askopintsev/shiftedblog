import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useT } from "@/i18n";

type SiteSettings = {
  site_name: string;
  tagline: string;
  footer_text: string;
  telegram_url: string;
  github_url: string;
  habr_url: string;
  twitter_site: string;
  contact_email: string;
  default_from_email: string;
  admin_email: string;
  email_host: string;
  email_port: number;
  email_host_user: string;
  email_use_tls: boolean;
  email_use_ssl: boolean;
  telegram_use_rich_messages: boolean;
  text_quality_checker_enabled: boolean;
};

const emptyForm: SiteSettings = {
  site_name: "",
  tagline: "",
  footer_text: "",
  telegram_url: "",
  github_url: "",
  habr_url: "",
  twitter_site: "",
  contact_email: "",
  default_from_email: "",
  admin_email: "",
  email_host: "",
  email_port: 587,
  email_host_user: "",
  email_use_tls: true,
  email_use_ssl: false,
  telegram_use_rich_messages: false,
  text_quality_checker_enabled: false,
};

export function SiteSettingsPage() {
  const queryClient = useQueryClient();
  const t = useT();
  const [form, setForm] = useState<SiteSettings>(emptyForm);

  const { data, isLoading } = useQuery({
    queryKey: ["site-settings"],
    queryFn: () =>
      apiFetch<{ ok: boolean; settings: SiteSettings }>("/config/site-settings/"),
  });

  useEffect(() => {
    if (data?.settings) {
      setForm({ ...emptyForm, ...data.settings });
    }
  }, [data?.settings]);

  const patchMutation = useMutation({
    mutationFn: () =>
      apiFetch("/config/site-settings/", {
        method: "PATCH",
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["site-settings"] });
    },
  });

  function setField<K extends keyof SiteSettings>(key: K, value: SiteSettings[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  if (isLoading) {
    return (
      <div className="p-6 text-text-muted">{t("common.loading")}</div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-semibold">{t("siteSettings.title")}</h1>
      <p className="mb-6 max-w-2xl text-sm text-text-muted">
        {t("siteSettings.help")}
      </p>
      <form
        className="max-w-2xl space-y-8"
        onSubmit={(e) => {
          e.preventDefault();
          patchMutation.mutate();
        }}
      >
        <section className="space-y-4 rounded-lg border border-border bg-surface p-4">
          <h2 className="text-sm font-semibold">{t("siteSettings.brand")}</h2>
          <label className="block text-sm">
            {t("siteSettings.siteName")}
            <input
              value={form.site_name}
              onChange={(e) => setField("site_name", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.tagline")}
            <input
              value={form.tagline}
              onChange={(e) => setField("tagline", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.footerText")}
            <textarea
              value={form.footer_text}
              onChange={(e) => setField("footer_text", e.target.value)}
              rows={4}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
        </section>

        <section className="space-y-4 rounded-lg border border-border bg-surface p-4">
          <h2 className="text-sm font-semibold">{t("siteSettings.social")}</h2>
          <label className="block text-sm">
            {t("siteSettings.telegramUrl")}
            <input
              value={form.telegram_url}
              onChange={(e) => setField("telegram_url", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.githubUrl")}
            <input
              value={form.github_url}
              onChange={(e) => setField("github_url", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.habrUrl")}
            <input
              value={form.habr_url}
              onChange={(e) => setField("habr_url", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.twitterSite")}
            <input
              value={form.twitter_site}
              onChange={(e) => setField("twitter_site", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.contactEmail")}
            <input
              type="email"
              value={form.contact_email}
              onChange={(e) => setField("contact_email", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
        </section>

        <section className="space-y-4 rounded-lg border border-border bg-surface p-4">
          <h2 className="text-sm font-semibold">{t("siteSettings.email")}</h2>
          <p className="text-xs text-text-muted">{t("siteSettings.emailHelp")}</p>
          <label className="block text-sm">
            {t("siteSettings.defaultFromEmail")}
            <input
              type="email"
              value={form.default_from_email}
              onChange={(e) => setField("default_from_email", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.adminEmail")}
            <input
              type="email"
              value={form.admin_email}
              onChange={(e) => setField("admin_email", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.emailHost")}
            <input
              value={form.email_host}
              onChange={(e) => setField("email_host", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.emailPort")}
            <input
              type="number"
              value={form.email_port}
              onChange={(e) =>
                setField("email_port", Number(e.target.value) || 587)
              }
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="block text-sm">
            {t("siteSettings.emailHostUser")}
            <input
              value={form.email_host_user}
              onChange={(e) => setField("email_host_user", e.target.value)}
              className="mt-1 w-full rounded-lg border border-border px-2 py-1.5"
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.email_use_tls}
              onChange={(e) => setField("email_use_tls", e.target.checked)}
            />
            {t("siteSettings.emailUseTls")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.email_use_ssl}
              onChange={(e) => setField("email_use_ssl", e.target.checked)}
            />
            {t("siteSettings.emailUseSsl")}
          </label>
        </section>

        <section className="space-y-4 rounded-lg border border-border bg-surface p-4">
          <h2 className="text-sm font-semibold">{t("siteSettings.toggles")}</h2>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.telegram_use_rich_messages}
              onChange={(e) =>
                setField("telegram_use_rich_messages", e.target.checked)
              }
            />
            {t("siteSettings.telegramRich")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.text_quality_checker_enabled}
              onChange={(e) =>
                setField("text_quality_checker_enabled", e.target.checked)
              }
            />
            {t("siteSettings.textQuality")}
          </label>
        </section>

        <button
          type="submit"
          disabled={patchMutation.isPending}
          className="rounded-lg bg-accent px-4 py-2 text-sm text-white"
        >
          {t("common.save")}
        </button>
      </form>
    </div>
  );
}
