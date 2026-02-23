from rest_framework.exceptions import APIException
from rest_framework import status


class FileTypeNotAllowed(APIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_detail = 'The uploaded file type is not allowed.'
    default_code = 'file_type_not_allowed'


class FileSizeExceeded(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'The uploaded file exceeds the maximum allowed size.'
    default_code = 'file_size_exceeded'


class FileNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested file was not found.'
    default_code = 'file_not_found'


class UnauthorizedFileAccess(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to access this file.'
    default_code = 'unauthorized_file_access'
