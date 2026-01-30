from django.core.management.base import BaseCommand
import os
import subprocess
from datetime import datetime
import yadisk  # For Yandex Disk

class Command(BaseCommand):
    help = 'Backup PostgreSQL DB locally and to Yandex Disk'

    def add_arguments(self, parser):
        parser.add_argument('--method', type=str, default='pg_dump', choices=['pg_dump'])  # Extend if needed

    def handle(self, *args, **options):
        method = options['method']
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')
        db_password = os.environ.get('DB_PASS')  # Fixed: use DB_PASS to match settings.py
        db_host = os.environ.get('DB_HOST', 'db')
        backup_dir = os.environ.get('BACKUP_DIR', 'backups')
        yandex_token = os.environ.get('YADISK_TOKEN')  # Optional for upload
        
        # Validate required environment variables
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
        
        # Create backup directory if it doesn't exist
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except OSError as e:
            self.stdout.write(self.style.ERROR(f'Failed to create backup directory {backup_dir}: {e}'))
            return
        
        backup_file = f"{backup_dir}/{db_name}_{method}_{timestamp}.sql.gz"

        os.environ['PGPASSWORD'] = db_password  # For pg_dump security

        try:
            # Step 1: Local Backup with pg_dump (compressed, best for logical restore)
            cmd = f"pg_dump -h {db_host} -U {db_user} {db_name} | gzip > {backup_file}"
            subprocess.check_call(cmd, shell=True)
            self.stdout.write(self.style.SUCCESS(f'Local backup completed: {backup_file}'))

            # Step 2: Upload to Yandex Disk (create /backups/ dir if needed)
            if yandex_token:
                try:
                    y = yadisk.YaDisk(token=yandex_token)
                    if not y.check_token():
                        self.stdout.write(self.style.ERROR('Invalid Yandex token'))
                        return
                    remote_dir = '/backups/'  # Your Yandex folder
                    if not y.exists(remote_dir):
                        y.mkdir(remote_dir)
                    remote_path = f"{remote_dir}{os.path.basename(backup_file)}"
                    y.upload(backup_file, remote_path, overwrite=True)
                    self.stdout.write(self.style.SUCCESS(f'Uploaded to Yandex Disk: {remote_path}'))
                except yadisk.exceptions.YaDiskError as e:
                    self.stdout.write(self.style.ERROR(f'Yandex upload failed: {e}'))
                    self.stdout.write(self.style.WARNING(
                        'Local backup completed successfully. '
                        'Check Yandex token permissions - it needs "cloud_api:disk.app_folder" scope.'
                    ))
            else:
                self.stdout.write(self.style.WARNING('Yandex token not set—skipping upload.'))

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'Backup failed: {e}'))
            raise
