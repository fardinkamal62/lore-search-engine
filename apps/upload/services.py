import logging
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
    def delete_file(uploaded_file):
        """
        Soft delete the file by marking it as deleted
        """
        file_name = uploaded_file.original_filename
        user = uploaded_file.uploaded_by.username

        uploaded_file.deleted_at = timezone.now()
        uploaded_file.status = 'deleted'
        uploaded_file.save()

        logger.info('File deleted: name=%s user=%s', file_name, user)
