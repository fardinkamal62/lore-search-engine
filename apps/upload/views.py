from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import FileNotFound, UnauthorizedFileAccess
from .serializers import FileUploadSerializer, UploadedFileSerializer
from .services import FileUploadService


class FileUploadListView(APIView):
    """
    GET  /api/upload/  - list the authenticated user's uploaded files
    POST /api/upload/  - upload a new file (multipart/form-data, field name: 'file')
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        # Only retrieve files uploaded by the authenticated user
        files = FileUploadService.get_user_files(request.user)
        serializer = UploadedFileSerializer(files, many=True, context={'request': request})
        return Response({
            'files': serializer.data,
            'count': files.count(),
        }, status=status.HTTP_200_OK)

    def post(self, request):
        # Support both single-file ('file') and multi-file ('files') uploads
        raw_files = request.FILES.getlist('files') or request.FILES.getlist('file')
        if not raw_files:
            return Response({
                'errors': {'files': ['No file was submitted.']},
                'message': 'Upload failed. Please attach at least one file.',
            }, status=status.HTTP_400_BAD_REQUEST)

        saved, failed = [], []
        for raw_file in raw_files:
            serializer = FileUploadSerializer(data={'file': raw_file})
            if not serializer.is_valid():
                failed.append({
                    'filename': raw_file.name,
                    'errors': serializer.errors,
                })
                continue
            uploaded_file = FileUploadService.save_file(
                user=request.user,
                file=serializer.validated_data['file'],
            )
            saved.append(UploadedFileSerializer(uploaded_file, context={'request': request}).data)

        if not saved:
            return Response({
                'failed': failed,
                'message': 'All uploads failed. Please check the files.',
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'files': saved,
            'failed': failed,
            'count': len(saved),
            'message': (
                f'{len(saved)} file(s) uploaded successfully.'
                + (f' {len(failed)} file(s) failed.' if failed else '')
            ),
        }, status=status.HTTP_201_CREATED)


class FileDetailDeleteView(APIView):
    """
    GET    /api/upload/<id>/  - retrieve details of a specific file
    DELETE /api/upload/<id>/  - delete a specific file
    """
    permission_classes = [IsAuthenticated]

    def _get_file_or_raise(self, file_id, user):
        uploaded_file = FileUploadService.get_file_by_id(file_id, user)
        if not uploaded_file:
            # Distinguish between "does not exist" and "belongs to someone else"
            from .models import UploadedFile
            if UploadedFile.objects.filter(id=file_id).exists():
                raise UnauthorizedFileAccess()
            raise FileNotFound()
        return uploaded_file

    def get(self, request, pk):
        uploaded_file = self._get_file_or_raise(pk, request.user)
        serializer = UploadedFileSerializer(uploaded_file, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        uploaded_file = self._get_file_or_raise(pk, request.user)
        FileUploadService.delete_file(uploaded_file)
        return Response({'message': 'File deleted successfully.'}, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        uploaded_file = self._get_file_or_raise(pk, request.user)
        new_name = request.data.get('original_filename', '').strip()
        if not new_name:
            return Response(
                {'error': 'original_filename must not be empty.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            uploaded_file = FileUploadService.rename_file(uploaded_file, new_name)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = UploadedFileSerializer(uploaded_file, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

