"""
Management command: reindex

Usage examples:
    # Re-index a single file by ID
    python manage.py reindex --file-id 42

    # Re-index all pending/failed files for a specific user
    python manage.py reindex --user fardin

    # Full corpus re-score for all users (fixes TF-IDF eventual-consistency drift)
    python manage.py reindex --all

    # Combine: full re-score for one user only
    python manage.py reindex --all --user fardin
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.indexer.pipeline import index_document, reindex_user_corpus

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Re-index uploaded files (backfill pending/failed or full corpus re-score).'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--file-id',
            type=int,
            metavar='ID',
            help='Re-index a single UploadedFile by primary key.',
        )
        group.add_argument(
            '--all',
            action='store_true',
            help='Full corpus re-score (clears and rebuilds all index entries).',
        )
        group.add_argument(
            '--pending',
            action='store_true',
            help='Index all files currently in pending or failed status.',
        )
        parser.add_argument(
            '--user',
            type=str,
            metavar='USERNAME',
            help='Limit operation to a specific user (by username).',
        )

    def handle(self, *args, **options):
        user_filter = options.get('user')
        target_user = None

        if user_filter:
            try:
                target_user = User.objects.get(username=user_filter)
            except User.DoesNotExist:
                raise CommandError(f'User "{user_filter}" not found.')

        if options['file_id']:
            self._reindex_single(options['file_id'])

        elif options['all']:
            self._reindex_all(target_user)

        elif options['pending']:
            self._reindex_pending(target_user)

    # ---------------------------------------------------------------------- #
    # Handlers
    # ---------------------------------------------------------------------- #

    def _reindex_single(self, file_id: int):
        from apps.upload.models import UploadedFile
        from apps.indexer.models import InvertedIndex

        try:
            f = UploadedFile.objects.get(pk=file_id)
        except UploadedFile.DoesNotExist:
            raise CommandError(f'UploadedFile with id={file_id} not found.')

        self.stdout.write(f'Re-indexing file id={file_id} ({f.original_filename}) …')

        # Reset + clear for a clean rebuild
        f.status = 'pending'
        f.save(update_fields=['status'])
        InvertedIndex.objects.filter(document=f).delete()

        ok = index_document(file_id)
        if ok:
            self.stdout.write(self.style.SUCCESS(f'✓ File {file_id} indexed successfully.'))
        else:
            self.stdout.write(self.style.ERROR(f'✗ File {file_id} indexing failed.'))

    def _reindex_all(self, target_user=None):
        users = [target_user] if target_user else list(User.objects.filter(is_active=True))
        self.stdout.write(f'Full corpus re-score for {len(users)} user(s) …')

        total_ok = total_fail = 0
        for user in users:
            self.stdout.write(f'  User: {user.username}')
            stats = reindex_user_corpus(user)
            total_ok += stats['reindexed']
            total_fail += stats['failed']
            self.stdout.write(
                f'    reindexed={stats["reindexed"]}  failed={stats["failed"]}'
            )

        summary = f'Done. Total reindexed={total_ok}  failed={total_fail}'
        if total_fail:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

    def _reindex_pending(self, target_user=None):
        from apps.upload.models import UploadedFile

        qs = UploadedFile.objects.filter(status__in=['pending', 'failed'], deleted_at=None)
        if target_user:
            qs = qs.filter(uploaded_by=target_user)

        files = list(qs)
        self.stdout.write(f'Indexing {len(files)} pending/failed file(s) …')

        ok_count = fail_count = 0
        for f in files:
            ok = index_document(f.pk)
            if ok:
                ok_count += 1
                self.stdout.write(f'  ✓ {f.pk} {f.original_filename}')
            else:
                fail_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ {f.pk} {f.original_filename}'))

        summary = f'Done. indexed={ok_count}  failed={fail_count}'
        if fail_count:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

