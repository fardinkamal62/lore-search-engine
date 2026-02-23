from rest_framework import serializers
from .models import UploadedFile
from .utils import UploadUtils


class FileUploadSerializer(serializers.Serializer):
    """Serializer used to validate and accept an incoming file upload"""
    file = serializers.FileField()

    def validate_file(self, file):
        valid, error = UploadUtils.validate_file(file)
        if not valid:
            raise serializers.ValidationError(error)
        return file


class UploadedFileSerializer(serializers.ModelSerializer):
    """Serializer for returning uploaded file details"""
    uploaded_by = serializers.StringRelatedField(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = (
            'id',
            'original_filename',
            'file_type',
            'file_size',
            'status',
            'uploaded_by',
            'uploaded_at',
            'updated_at',
            'file_url',
        )
        read_only_fields = fields

    def get_file_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url
