"""Restore PostgreSQL and media from backup_db output."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.services.site_domain import sync_sites_framework_from_site_url


def _latest_matching(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


class Command(BaseCommand):
    help = (
        "Restore PostgreSQL and media from backup_db files. "
        "Dump and Postgres major versions must match (production image is 17). "
        "Reuse CREDENTIALS_ENCRYPTION_KEY and SECRET_KEY from the source site."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            type=str,
            default="",
            help="Path to {DB_NAME}_pg_dump_*.sql.gz (default: newest in BACKUP_DIR)",
        )
        parser.add_argument(
            "--media",
            type=str,
            default="",
            help="Path to media_*.tar.gz (default: newest in BACKUP_DIR)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate inputs and print actions without writing",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Replace a non-empty public schema",
        )
        parser.add_argument(
            "--skip-media",
            action="store_true",
            help="Restore only the database",
        )
        parser.add_argument(
            "--skip-db",
            action="store_true",
            help="Restore only media files",
        )
        parser.add_argument(
            "--skip-site-sync",
            action="store_true",
            help="Do not update django.contrib.sites from SITE_URL",
        )

    def handle(self, *args, **options):
        skip_media = options["skip_media"]
        skip_db = options["skip_db"]
        dry_run = options["dry_run"]
        force = options["force"]
        if skip_db and skip_media:
            raise CommandError("Nothing to restore: both --skip-db and --skip-media")

        backup_dir = Path(os.environ.get("BACKUP_DIR", "/backups"))
        dump_path = self._resolve_dump(options["dump"], backup_dir, skip_db)
        media_path = self._resolve_media(options["media"], backup_dir, skip_media)

        if not skip_db:
            self._restore_database(dump_path, dry_run=dry_run, force=force)
        if not skip_media:
            self._restore_media(media_path, dry_run=dry_run)
        if not skip_db and not options["skip_site_sync"]:
            self._sync_site(dry_run=dry_run)

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"Restore completed{suffix}"))

    def _resolve_dump(
        self, explicit: str, backup_dir: Path, skip_db: bool
    ) -> Path | None:
        if skip_db:
            return None
        if explicit:
            path = Path(explicit)
            if not path.is_file():
                raise CommandError(f"Dump file not found: {path}")
            return path
        db_name = os.environ.get("DB_NAME") or "shiftedblog"
        found = _latest_matching(backup_dir, f"{db_name}_pg_dump_*.sql.gz")
        if found is None:
            found = _latest_matching(backup_dir, "*_pg_dump_*.sql.gz")
        if found is None:
            raise CommandError(
                f"No pg_dump .sql.gz in {backup_dir}. "
                "Pass --dump or copy backup_db output there."
            )
        return found

    def _resolve_media(
        self, explicit: str, backup_dir: Path, skip_media: bool
    ) -> Path | None:
        if skip_media:
            return None
        if explicit:
            path = Path(explicit)
            if not path.is_file():
                raise CommandError(f"Media archive not found: {path}")
            return path
        found = _latest_matching(backup_dir, "media_*.tar.gz")
        if found is None:
            raise CommandError(
                f"No media_*.tar.gz in {backup_dir}. Pass --media or use --skip-media."
            )
        return found

    def _db_env(self) -> tuple[str, str, str, str]:
        db_name = os.environ.get("DB_NAME")
        db_user = os.environ.get("DB_USER")
        db_password = os.environ.get("DB_PASS")
        db_host = os.environ.get("DB_HOST", "db")
        if not db_name or not db_user or not db_password:
            raise CommandError("DB_NAME, DB_USER, and DB_PASS are required")
        return db_name, db_user, db_password, db_host or "db"

    def _public_table_count(
        self, db_name: str, db_user: str, db_password: str, db_host: str
    ) -> int:
        query = (
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        try:
            result = subprocess.run(
                ["psql", "-h", db_host, "-U", db_user, "-d", db_name, "-tAc", query],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CommandError(f"Could not inspect target database: {exc}") from exc
        text = (result.stdout or "").strip()
        try:
            return int(text)
        except ValueError as exc:
            raise CommandError(f"Unexpected psql table count: {text!r}") from exc

    def _restore_database(
        self, dump_path: Path | None, *, dry_run: bool, force: bool
    ) -> None:
        assert dump_path is not None
        db_name, db_user, db_password, db_host = self._db_env()
        table_count = self._public_table_count(db_name, db_user, db_password, db_host)
        self.stdout.write(f"Target public tables: {table_count}")
        self.stdout.write(f"Dump: {dump_path}")
        if table_count > 0 and not force:
            raise CommandError(
                "Target database is not empty. "
                "Re-run with --force to replace the public schema."
            )
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: skipping pg_restore"))
            return
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        drop_sql = (
            "DROP SCHEMA public CASCADE; CREATE SCHEMA public; "
            f"GRANT ALL ON SCHEMA public TO {db_user}; "
            "GRANT ALL ON SCHEMA public TO public;"
        )
        try:
            subprocess.run(
                [
                    "psql",
                    "-h",
                    db_host,
                    "-U",
                    db_user,
                    "-d",
                    db_name,
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    drop_sql,
                ],
                check=True,
                env=env,
            )
            gunzip = subprocess.Popen(
                ["gunzip", "-c", str(dump_path)],
                stdout=subprocess.PIPE,
            )
            try:
                subprocess.run(
                    [
                        "psql",
                        "-h",
                        db_host,
                        "-U",
                        db_user,
                        "-d",
                        db_name,
                        "-v",
                        "ON_ERROR_STOP=1",
                    ],
                    check=True,
                    stdin=gunzip.stdout,
                    env=env,
                )
            finally:
                if gunzip.stdout is not None:
                    gunzip.stdout.close()
                gzip_rc = gunzip.wait()
            if gzip_rc != 0:
                raise subprocess.CalledProcessError(gzip_rc, "gunzip")
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CommandError(f"Database restore failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Database restored from {dump_path}"))

    def _restore_media(self, media_path: Path | None, *, dry_run: bool) -> None:
        assert media_path is not None
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if not media_root:
            raise CommandError("MEDIA_ROOT is not configured")
        parent = Path(media_root).parent
        self.stdout.write(f"Media archive: {media_path}")
        self.stdout.write(f"Extract to: {parent}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: skipping media extract"))
            return
        try:
            parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["tar", "-xzf", str(media_path), "-C", str(parent)],
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CommandError(f"Media restore failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Media restored from {media_path}"))

    def _sync_site(self, *, dry_run: bool) -> None:
        site_url = getattr(settings, "SITE_URL", "") or ""
        if dry_run:
            self.stdout.write(
                f"Dry-run: would sync django.contrib.sites from {site_url!r}"
            )
            return
        try:
            site = sync_sites_framework_from_site_url()
        except ValueError as exc:
            self.stdout.write(self.style.WARNING(f"Skipped Site sync: {exc}"))
            return
        self.stdout.write(
            self.style.SUCCESS(f"Updated Site pk={site.pk} domain={site.domain}")
        )
