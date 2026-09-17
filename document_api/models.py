import uuid
from django.db import models

class ScreeningLog(models.Model):
    """
    Non-sensitive screening log for analytics and auditing.
    Uploaded document images are NOT stored in the database for privacy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    document_filename = models.CharField(max_length=255, default="document.png")
    document_type = models.CharField(max_length=100, default="Demo Identity Credential")
    risk_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=50, default="LOW REVIEW")
    image_quality_score = models.FloatField(default=100.0)
    blur_detected = models.BooleanField(default=False)
    extracted_name = models.CharField(max_length=255, blank=True, null=True)
    extracted_id = models.CharField(max_length=100, blank=True, null=True)
    flags_count = models.IntegerField(default=0)
    processing_time_ms = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} | {self.document_type} | {self.risk_level} ({self.risk_score})"
