from rest_framework import serializers
from .models import ScreeningLog

class DocumentUploadSerializer(serializers.Serializer):
    document = serializers.FileField(required=True)

    def validate_document(self, value):
        # 5 MB max size check
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds the 5 MB limit.")
        
        valid_extensions = ['.jpg', '.jpeg', '.png']
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(f"Invalid file type '{ext}'. Only JPG, JPEG, and PNG files are accepted.")
        return value

class ScreeningLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningLog
        fields = '__all__'
