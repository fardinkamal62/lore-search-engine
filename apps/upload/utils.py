import os

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg', 'md'}

# Normalise jpg/jpeg to a single canonical key
EXTENSION_ALIAS = {'jpeg': 'jpg'}

# Maximum file size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024


class UploadUtils:
    """Utility functions for file upload validation and processing"""

    @staticmethod
    def get_file_extension(filename):
        """Return the lowercase extension (without the dot) of a filename"""
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip('.').lower()
        return EXTENSION_ALIAS.get(ext, ext)

    @staticmethod
    def is_allowed_extension(filename):
        """Return True if the file extension is in the allowed set"""
        ext = UploadUtils.get_file_extension(filename)
        return ext in ALLOWED_EXTENSIONS

    @staticmethod
    def validate_file_size(file):
        """Return (True, None) when size is acceptable, otherwise (False, message)"""
        if file.size > MAX_FILE_SIZE:
            mb = MAX_FILE_SIZE // (1024 * 1024)
            return False, f'File size exceeds the maximum allowed size of {mb} MB.'
        return True, None

    @staticmethod
    def validate_file(file):
        """
        Run all upload validations.
        Returns (True, None) on success or (False, error_message) on failure.
        """
        if not UploadUtils.is_allowed_extension(file.name):
            allowed = ', '.join(sorted(ALLOWED_EXTENSIONS))
            return False, f'File type not allowed. Allowed types: {allowed}.'

        valid, msg = UploadUtils.validate_file_size(file)
        if not valid:
            return False, msg

        return True, None

    @staticmethod
    def get_canonical_file_type(filename):
        """Return the canonical file type string stored in the model"""
        return UploadUtils.get_file_extension(filename)
