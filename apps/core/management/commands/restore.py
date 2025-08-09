from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core import management
from pathlib import Path
import shutil


class Command(BaseCommand):
    help = "Restore database from a given JSON dump file and optionally restore media directory."

    def add_arguments(self, parser):
        parser.add_argument('--db', required=True, help='Path to a dumpdata JSON file')
        parser.add_argument('--media', help='Path to a media directory to restore')

    def handle(self, *args, **options):
        dump_path = Path(options['db'])
        if not dump_path.exists():
            raise CommandError(f"Dump file not found: {dump_path}")

        self.stdout.write(self.style.NOTICE(f"Flushing database (keep auth)?"))
        management.call_command('flush', '--noinput')

        self.stdout.write(self.style.NOTICE(f"Loading data from {dump_path}"))
        management.call_command('loaddata', str(dump_path))

        media_src = options.get('media')
        if media_src:
            media_src_path = Path(media_src)
            if not media_src_path.exists():
                raise CommandError(f"Media path not found: {media_src_path}")
            media_dest = Path(settings.MEDIA_ROOT)
            if media_dest.exists():
                shutil.rmtree(media_dest)
            shutil.copytree(media_src_path, media_dest)

        self.stdout.write(self.style.SUCCESS("Restore completed."))



