from django.core.management.base import BaseCommand
from django.conf import settings
import os
import subprocess
from datetime import datetime
import yadisk  # For Yandex Disk

class Command(BaseCommand):
    help = 'Backup PostgreSQL DB and media files locally and optionally to Yandex Disk'

    def add_arguments(self, parser):
        parser.add_argument('--method', type=str, default='pg_dump', choices=['pg_dump'])
        parser.add_argument('--skip-media', action='store_true', help='Backup only the database, skip media files')
        parser.add_argument('--skip-db', action='store_true', help='Backup only media files, skip the database')

    def handle(self, *args, **options):
        method = options['method']
        skip_media = options['skip_media']
        skip_db = options['skip_db']
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')
        db_password = os.environ.get('DB_PASS')
        db_host = os.environ.get('DB_HOST', 'db')
        backup_dir = os.environ.get('BACKUP_DIR', '/backups')
        yandex_token = os.environ.get('YADISK_TOKEN')

        if not skip_db:
            if not db_name:
                self.stdout.write(self.style.ERROR('DB_NAME environment variable is required'))
                return
            if not db_user:
                self.stdout.write(self.style.ERROR('DB_USER environment variable is required'))
                return
            if not db_password:
                self.stdout.write(self.style.ERROR('DB_PASS environment variable is required'))
                return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            os.makedirs(backup_dir, exist_ok=True)
        except OSError as e:
            self.stdout.write(self.style.ERROR(f'Failed to create backup directory {backup_dir}: {e}'))
            return

        backup_files = []

        # Step 1: Database backup
        if not skip_db:
            backup_file = f"{backup_dir}/{db_name}_{method}_{timestamp}.sql.gz"
            os.environ['PGPASSWORD'] = db_password
            try:
                cmd = f"pg_dump -h {db_host} -U {db_user} {db_name} | gzip > {backup_file}"
                subprocess.check_call(cmd, shell=True)
                self.stdout.write(self.style.SUCCESS(f'DB backup completed: {backup_file}'))
                backup_files.append(backup_file)
            except subprocess.CalledProcessError as e:
                self.stdout.write(self.style.ERROR(f'DB backup failed: {e}'))
                raise
            finally:
                os.environ.pop('PGPASSWORD', None)

        # Step 2: Media backup
        if not skip_media:
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and os.path.isdir(media_root):
                media_archive = f"{backup_dir}/media_{timestamp}.tar.gz"
                parent = os.path.dirname(media_root)
                dirname = os.path.basename(media_root)
                try:
                    cmd = f"tar -czf {media_archive} -C {parent} {dirname}"
                    subprocess.check_call(cmd, shell=True)
                    self.stdout.write(self.style.SUCCESS(f'Media backup completed: {media_archive}'))
                    backup_files.append(media_archive)
                except subprocess.CalledProcessError as e:
                    self.stdout.write(self.style.ERROR(f'Media backup failed: {e}'))
                    raise
            else:
                self.stdout.write(self.style.WARNING(
                    f'Media root not found or not a directory ({media_root}), skipping media backup.'
                ))

        # Step 3: Upload to Yandex Disk
        if yandex_token and backup_files:
            try:
                y = yadisk.YaDisk(token=yandex_token)
                if not y.check_token():
                    self.stdout.write(self.style.ERROR('Invalid Yandex token'))
                    return
                remote_dir = '/backups/'
                if not y.exists(remote_dir):
                    y.mkdir(remote_dir)
                for path in backup_files:
                    remote_path = f"{remote_dir}{os.path.basename(path)}"
                    y.upload(path, remote_path, overwrite=True)
                    self.stdout.write(self.style.SUCCESS(f'Uploaded to Yandex Disk: {remote_path}'))
            except yadisk.exceptions.YaDiskError as e:
                self.stdout.write(self.style.ERROR(f'Yandex upload failed: {e}'))
                self.stdout.write(self.style.WARNING(
                    'Local backup(s) completed. Check Yandex token permissions '
                    '(needs "cloud_api:disk.app_folder" scope).'
                ))
        elif yandex_token and not backup_files:
            self.stdout.write(self.style.WARNING('Nothing to upload (no backups created).'))
        elif not yandex_token and backup_files:
            self.stdout.write(self.style.WARNING('Yandex token not set—skipping upload.'))
