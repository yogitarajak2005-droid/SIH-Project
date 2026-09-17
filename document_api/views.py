import os
import logging
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .services import DocumentScreeningService
from .serializers import DocumentUploadSerializer
from .models import ScreeningLog

logger = logging.getLogger(__name__)

def index_view(request):
    """Renders the main single-page modern cybersecurity application."""
    return render(request, 'index.html')

class ScreenDocumentView(APIView):
    """
    POST /api/screen/
    Accepts an uploaded image file ('document'), validates it,
    performs OpenCV image quality analysis, OCR, heuristic field extraction,
    and returns an explainable risk-based screening evaluation.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            # Extract clean error message
            errors = serializer.errors
            err_msg = "Invalid upload."
            if 'document' in errors:
                err_msg = errors['document'][0]
            return Response({"success": False, "error": str(err_msg)}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data['document']

        try:
            # Execute screening pipeline
            service = DocumentScreeningService(uploaded_file)
            result = service.process()

            # Record non-sensitive audit log in DB (document itself is NOT stored)
            try:
                ScreeningLog.objects.create(
                    document_filename=uploaded_file.name,
                    document_type="Synthetic Demo Credential",
                    risk_score=result["screening"]["risk_score"],
                    risk_level=result["screening"]["risk_level"],
                    image_quality_score=result["breakdown"]["document_quality"]["contrast_score"],
                    blur_detected=result["breakdown"]["document_quality"]["is_blurry"],
                    extracted_name=result["extracted_data"].get("name"),
                    extracted_id=result["extracted_data"].get("document_id"),
                    flags_count=len(result["screening"]["flags"]),
                    processing_time_ms=result["processing_time_ms"]
                )
            except Exception as log_err:
                logger.warning(f"Could not persist audit log: {log_err}")

            return Response(result, status=status.HTTP_200_OK)

        except ValueError as val_err:
            return Response({"success": False, "error": str(val_err)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error in document screening pipeline")
            return Response({
                "success": False,
                "error": f"An unexpected analysis error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminStatsView(APIView):
    """
    GET /api/stats/
    Returns analytical metrics for the Admin / Analytics Dashboard:
    Total screened, risk level distributions, and recent screening history table.
    """
    def get(self, request, *args, **kwargs):
        # Baseline sample statistics specified in requirements
        base_screened = 128
        base_low = 72
        base_medium = 39
        base_high = 17

        # Add live session log increments
        live_logs = ScreeningLog.objects.all()
        live_count = live_logs.count()
        total_screened = base_screened + live_count

        total_low = base_low + live_logs.filter(risk_level='LOW REVIEW').count()
        total_medium = base_medium + live_logs.filter(risk_level='MEDIUM REVIEW').count()
        total_high = base_high + live_logs.filter(risk_level='HIGH REVIEW').count()

        # Build recent screening activity records (combining live + rich synthetic history)
        recent_records = []
        for log in live_logs[:5]:
            recent_records.append({
                "id": str(log.id)[:8],
                "date": log.timestamp.strftime("%Y-%m-%d %H:%M"),
                "document_type": log.document_type,
                "risk_score": log.risk_score,
                "risk_level": log.risk_level,
                "review_status": "Human Verified" if log.risk_score < 35 else "Pending Review",
                "extracted_id": log.extracted_id or "N/A"
            })

        # Pre-populate with realistic synthetic logs to make the admin table look active
        mock_history = [
            {"id": "SCR-9012", "date": "2026-09-16 22:15", "document_type": "Synthetic National ID", "risk_score": 18, "risk_level": "LOW REVIEW", "review_status": "Verified Clean", "extracted_id": "DEMO-9824-XYZ"},
            {"id": "SCR-9011", "date": "2026-09-16 21:40", "document_type": "Demo Resident Permit", "risk_score": 42, "risk_level": "MEDIUM REVIEW", "review_status": "Pending Human Review", "extracted_id": "RES-4412-DEMO"},
            {"id": "SCR-9010", "date": "2026-09-16 20:05", "document_type": "Synthetic Driver Card", "risk_score": 78, "risk_level": "HIGH REVIEW", "review_status": "Flagged Inconsistent", "extracted_id": "??? INVALID-ID ???"},
            {"id": "SCR-9009", "date": "2026-09-16 18:30", "document_type": "Demo Citizen Card", "risk_score": 22, "risk_level": "LOW REVIEW", "review_status": "Verified Clean", "extracted_id": "DEMO-1093-ABC"},
            {"id": "SCR-9008", "date": "2026-09-16 17:12", "document_type": "Synthetic Pass Credential", "risk_score": 58, "risk_level": "MEDIUM REVIEW", "review_status": "Pending Human Review", "extracted_id": "PASS-8831-SYN"}
        ]

        combined_records = (recent_records + mock_history)[:8]

        return Response({
            "success": True,
            "metrics": {
                "total_screened": total_screened,
                "low_review": total_low,
                "medium_review": total_medium,
                "high_review": total_high
            },
            "distribution": [
                {"label": "Low Review", "count": total_low, "color": "#10B981"},
                {"label": "Medium Review", "count": total_medium, "color": "#F59E0B"},
                {"label": "High Review", "count": total_high, "color": "#F43F5E"}
            ],
            "recent_activity": combined_records
        })


class DemoSamplesView(APIView):
    """
    GET /api/demo-samples/
    Lists available synthetic sample documents for 1-click testing.
    """
    def get(self, request, *args, **kwargs):
        samples = [
            {
                "id": "valid",
                "name": "Synthetic Clean Credential",
                "description": "High resolution, sharp focus, consistent fields (Expected: LOW REVIEW)",
                "filename": "sample_valid.png",
                "url": "/static/samples/sample_valid.png",
                "expected_risk": "LOW REVIEW"
            },
            {
                "id": "blurry",
                "name": "Low Quality / Blurry Scan",
                "description": "Simulated camera motion blur and reduced contrast (Expected: MEDIUM REVIEW)",
                "filename": "sample_blurry.png",
                "url": "/static/samples/sample_blurry.png",
                "expected_risk": "MEDIUM REVIEW"
            },
            {
                "id": "inconsistent",
                "name": "Inconsistent / Corrupted Data",
                "description": "Corrupted date format, future year, and invalid ID tokens (Expected: HIGH REVIEW)",
                "filename": "sample_inconsistent.png",
                "url": "/static/samples/sample_inconsistent.png",
                "expected_risk": "HIGH REVIEW"
            }
        ]
        return Response({"success": True, "samples": samples})
