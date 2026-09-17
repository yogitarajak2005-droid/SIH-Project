from django.contrib import admin
from .models import ScreeningLog

@admin.register(ScreeningLog)
class ScreeningLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'document_type', 'risk_level', 'risk_score', 'blur_detected', 'flags_count')
    list_filter = ('risk_level', 'blur_detected', 'timestamp')
    search_fields = ('document_filename', 'extracted_name', 'extracted_id')
    readonly_fields = ('id', 'timestamp')
