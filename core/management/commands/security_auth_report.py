"""Summarize authentication failures and rate-limit signals from logs and axes."""

from __future__ import annotations

import re
from collections import Counter
from datetime import timedelta
from pathlib import Path

from axes.models import AccessFailureLog
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Report failed logins, lockouts, and rate-limit log lines for the last N hours."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Lookback window in hours (default: 24).",
        )
        parser.add_argument(
            "--ip-threshold",
            type=int,
            default=20,
            help="Alert when one IP exceeds this failure count (default: 20).",
        )
        parser.add_argument(
            "--username-ip-threshold",
            type=int,
            default=3,
            help="Flag username seen from more than N IPs (default: 3).",
        )
        parser.add_argument(
            "--email",
            action="store_true",
            help="Email report to ADMIN_EMAIL when thresholds are exceeded.",
        )

    def handle(self, *args, **options):
        hours = max(1, int(options["hours"]))
        since = timezone.now() - timedelta(hours=hours)
        ip_threshold = int(options["ip_threshold"])
        username_ip_threshold = int(options["username_ip_threshold"])

        failures_by_ip: Counter[str] = Counter()
        failures_by_username: Counter[str] = Counter()
        username_ips: dict[str, set[str]] = {}
        lockouts = 0
        ratelimit_hits = 0

        qs = AccessFailureLog.objects.filter(attempt_time__gte=since)
        lockouts = qs.filter(locked_out=True).count()
        for row in qs.iterator():
            ip = row.ip_address or "unknown"
            username = row.username or "unknown"
            failures_by_ip[ip] += 1
            failures_by_username[username] += 1
            username_ips.setdefault(username, set()).add(ip)

        auth_log = Path(settings.LOG_DIR) / "authentication.log"
        security_log = Path(settings.LOG_DIR) / "security.log"
        ratelimit_hits += self._count_log_matches(
            auth_log, since, patterns=[r"ratelimit", r"Too Many Requests"]
        )
        ratelimit_hits += self._count_log_matches(
            security_log, since, patterns=[r"ratelimit", r"429"]
        )

        lines = [
            f"Security auth report (last {hours}h, since {since.isoformat()})",
            f"Failed attempts (axes DB): {sum(failures_by_ip.values())}",
            f"Lockouts (axes DB): {lockouts}",
            f"Rate-limit log hits: {ratelimit_hits}",
            "",
            "Top IPs:",
        ]
        for ip, count in failures_by_ip.most_common(10):
            lines.append(f"  {ip}: {count}")

        lines.append("")
        lines.append("Top usernames:")
        for username, count in failures_by_username.most_common(10):
            lines.append(f"  {username}: {count}")

        alerts: list[str] = []
        for ip, count in failures_by_ip.items():
            if count >= ip_threshold:
                alerts.append(
                    f"IP {ip} has {count} failures (threshold {ip_threshold})."
                )
        for username, ips in username_ips.items():
            if len(ips) > username_ip_threshold:
                alerts.append(
                    f"Username {username} seen from {len(ips)} IPs "
                    f"(threshold {username_ip_threshold})."
                )

        if alerts:
            lines.append("")
            lines.append("ALERTS:")
            lines.extend(f"  - {item}" for item in alerts)

        report = "\n".join(lines)
        self.stdout.write(report)

        if alerts and options["email"]:
            admin_email = getattr(settings, "ADMIN_EMAIL", "") or ""
            if admin_email:
                send_mail(
                    subject="[shiftedblog] Security auth report alerts",
                    message=report,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_email],
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Alert email sent to {admin_email}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("ADMIN_EMAIL is not set; skipping alert email.")
                )

        if alerts:
            self.stdout.write(self.style.WARNING("Threshold alerts detected."))
            raise SystemExit(1)

    def _count_log_matches(self, path: Path, since, *, patterns: list[str]) -> int:
        if not path.is_file():
            return 0
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
        count = 0
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return 0
        for line in text.splitlines():
            if not any(c.search(line) for c in compiled):
                continue
            count += 1
        return count
