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
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'errors': serializer.errors,
                'message': 'Upload failed. Please check the provided file.',
            }, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = FileUploadService.save_file(
            user=request.user,
            file=serializer.validated_data['file'],
        )

        return Response({
            'file': UploadedFileSerializer(uploaded_file, context={'request': request}).data,
            'message': 'File uploaded successfully.',
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
