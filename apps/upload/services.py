import logging
import os
import threading
from django.utils import timezone

from .models import UploadedFile
from .utils import UploadUtils

logger = logging.getLogger(__name__)


class FileUploadService:
    """Service layer for file upload operations"""

    @staticmethod
    def save_file(user, file):
        """
        Persist an uploaded file record.
        Returns the created UploadedFile instance.
        """
        file_type = UploadUtils.get_canonical_file_type(file.name)

        uploaded_file = UploadedFile.objects.create(
            file=file,
            original_filename=file.name,
            file_type=file_type,
            file_size=file.size,
            uploaded_by=user,
            status='pending',
        )

        logger.info(
            'File uploaded: id=%s name=%s user=%s',
            uploaded_file.id, uploaded_file.original_filename, user.username,
        )

        # Trigger indexing in a daemon background thread so the upload
        # response is not blocked.  To swap in Celery later, replace this
        # block with: index_document.delay(uploaded_file.id)
        def _run_indexing(file_id):
            from apps.indexer.pipeline import index_document
            index_document(file_id)

        thread = threading.Thread(
            target=_run_indexing,
            args=(uploaded_file.id,),
            daemon=True,
            name=f'indexer-{uploaded_file.id}',
        )
        thread.start()

        return uploaded_file

    @staticmethod
    def get_user_files(user):
        """
        Return all files belonging to the given user.
        This ensures users can only access their own uploaded files.
        """
        return UploadedFile.objects.filter(uploaded_by=user, deleted_at=None)

    @staticmethod
    def get_file_by_id(file_id, user):
        """
        Return a single UploadedFile owned by `user`, or None if not found.
        """
        return UploadedFile.objects.filter(id=file_id, uploaded_by=user).first()

    @staticmethod
    def rename_file(uploaded_file, new_name: str):
        """
        Rename both the display name and the actual file on disk.

        - `original_filename` is updated to `new_name`.
        - The file is moved to the same directory with `new_name` as its filename.
        - The `file` field (stored DB path) is updated to reflect the new path.

        Raises ValueError if `new_name` is empty or a different file with that
        name already exists in the same directory.
        """
        new_name = new_name.strip()
        if not new_name:
            raise ValueError('Filename must not be empty.')

        old_abs_path = uploaded_file.file.path          # absolute path on disk
        old_rel_name = uploaded_file.file.name          # relative path stored in DB

        old_dir_abs  = os.path.dirname(old_abs_path)   # absolute directory
        old_dir_rel  = os.path.dirname(old_rel_name)    # relative directory

        new_abs_path = os.path.join(old_dir_abs, new_name)
        new_rel_name = os.path.join(old_dir_rel, new_name) if old_dir_rel else new_name

        # If the name hasn't actually changed, nothing to do
        if os.path.abspath(old_abs_path) == os.path.abspath(new_abs_path):
            uploaded_file.original_filename = new_name
            uploaded_file.save(update_fields=['original_filename', 'updated_at'])
            return uploaded_file

        # Guard: don't clobber a different existing file
        if os.path.exists(new_abs_path):
            raise ValueError(f'A file named "{new_name}" already exists in the same folder.')

        # Rename on disk
        os.rename(old_abs_path, new_abs_path)

        # Update model fields
        uploaded_file.file.name      = new_rel_name
        uploaded_file.original_filename = new_name
        uploaded_file.save(update_fields=['file', 'original_filename', 'updated_at'])

        logger.info(
            'File renamed on disk: id=%s old=%s new=%s user=%s',
            uploaded_file.id, old_abs_path, new_abs_path, uploaded_file.uploaded_by.username,
        )
        return uploaded_file

    @staticmethod
    def delete_file(uploaded_file):
        """
        Soft delete the file by marking it as deleted and purging its index entries.
        """
        file_name = uploaded_file.original_filename
        user = uploaded_file.uploaded_by.username

        # Remove all index entries for this file before soft-deleting
        try:
            from apps.indexer.services import IndexerService
            deleted_entries = IndexerService.delete_document_index(
                uploaded_file.uploaded_by, uploaded_file.pk
            )
            logger.info(
                'Index entries removed: file=%s entries=%d', file_name, deleted_entries
            )
        except Exception as exc:
            logger.error('Failed to remove index entries for file=%s: %s', file_name, exc)

        uploaded_file.deleted_at = timezone.now()
        uploaded_file.status = 'deleted'
        uploaded_file.save()

        logger.info('File deleted: name=%s user=%s', file_name, user)
