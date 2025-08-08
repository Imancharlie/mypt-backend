from django.core.management.base import BaseCommand
from django.conf import settings
from django.core import management
from pathlib import Path
from datetime import datetime
import shutil


class Command(BaseCommand):
    help = "Create a timestamped backup: database JSON dump and media folder copy"

    def handle(self, *args, **options):
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        backups_dir = Path(settings.BASE_DIR) / 'backups'
        backups_dir.mkdir(parents=True, exist_ok=True)

        # 1) Dump database to JSON
        dump_path = backups_dir / f'db_{timestamp}.json'
        self.stdout.write(self.style.NOTICE(f"Dumping database -> {dump_path}"))
        with open(dump_path, 'w', encoding='utf-8') as out:
            management.call_command('dumpdata', '--natural-foreign', '--natural-primary', '--indent', '2', stdout=out)

        # 2) Copy media directory if it exists
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            media_archive = backups_dir / f'media_{timestamp}'
            self.stdout.write(self.style.NOTICE(f"Copying media -> {media_archive}"))
            if media_archive.exists():
                shutil.rmtree(media_archive)
            shutil.copytree(media_root, media_archive)

        self.stdout.write(self.style.SUCCESS("Backup completed."))



