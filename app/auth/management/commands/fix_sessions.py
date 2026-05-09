from django.core.management.base import BaseCommand, CommandError
from django.contrib.sessions.models import Session
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Repair sessions that have legacy dict-shaped _auth_user_id or optionally clear sessions.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear all sessions instead of repairing')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without saving')

    def handle(self, *args, **options):
        clear = options['clear']
        dry_run = options['dry_run']

        if clear:
            sessions = Session.objects.all()
            count = sessions.count()
            if dry_run:
                self.stdout.write(f"Would delete {count} sessions (dry-run)")
                return
            sessions.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {count} sessions"))
            return

        fixed = 0
        skipped = 0
        for session in Session.objects.all():
            try:
                data = session.get_decoded()
            except Exception as e:
                logger.exception('Failed to decode session %s', session.pk)
                skipped += 1
                continue

            changed = False
            if '_auth_user_id' in data and isinstance(data['_auth_user_id'], dict):
                user_id = data['_auth_user_id'].get('user_id')
                if user_id is not None:
                    self.stdout.write(f"Session {session.pk}: converting dict user -> {user_id}")
                    data['_auth_user_id'] = str(user_id)
                    changed = True
                else:
                    self.stdout.write(f"Session {session.pk}: _auth_user_id dict has no user_id, skipping")
                    skipped += 1

            if changed:
                if not dry_run:
                    # Save back to session store (serialize and update)
                    session.session_data = Session.objects.encode(data)
                    session.save()
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed} sessions, skipped {skipped}"))
