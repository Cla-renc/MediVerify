import logging

import pytesseract
import requests
from django.db import DatabaseError
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, views
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.ai.chat import answer_medicine_question, detect_language, log_question
from apps.ai.models import AIActionAudit
from apps.ai.ocr import MAX_IMAGE_BYTES, read_pack_image
from apps.ai.serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    PackOCRRequestSerializer,
    PackOCRResponseSerializer,
)
from apps.products.models import Batch
from apps.reports.models import SystemSettings

logger = logging.getLogger(__name__)


class PharmacistOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'PHARMACIST'
        )


class OCRUploadThrottle(ScopedRateThrottle):
    scope = 'ocr_upload'


class ChatThrottle(ScopedRateThrottle):
    scope = 'ai_chat'


class PackOCRAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, PharmacistOnly]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [OCRUploadThrottle]

    @extend_schema(
        operation_id='pack_ocr',
        summary='Extract batch and date fields from a medicine pack photo',
        request=PackOCRRequestSerializer,
        responses={
            200: PackOCRResponseSerializer,
            400: {'type': 'object', 'additionalProperties': True},
            503: {'type': 'object', 'additionalProperties': True},
        },
    )
    def post(self, request):
        if not SystemSettings.get_settings().ocr_enabled:
            return Response({'error': 'Pack OCR is disabled by the administrator.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        image_file = request.FILES.get('image')
        if not image_file:
            _audit_ocr(request.user, 'rejected', 'missing_image')
            return Response({'error': 'An image upload is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if image_file.size <= 0 or image_file.size > MAX_IMAGE_BYTES:
            _audit_ocr(request.user, 'rejected', 'invalid_size')
            return Response({'error': 'Image must be non-empty and no larger than 5 MB.'}, status=status.HTTP_400_BAD_REQUEST)
        if image_file.content_type not in ('image/jpeg', 'image/pjpeg', 'image/png', 'image/webp'):
            _audit_ocr(request.user, 'rejected', 'invalid_mime')
            return Response({'error': 'Upload a JPEG, PNG, or WEBP image.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = read_pack_image(image_file.read())
        except ValueError as exc:
            AIActionAudit.objects.create(
                actor=request.user,
                action='pack_ocr',
                outcome='rejected',
                details={'reason': str(exc)},
            )
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except pytesseract.TesseractNotFoundError:
            logger.exception('Tesseract executable is unavailable for pack OCR.')
            _audit_ocr(request.user, 'unavailable', 'tesseract_not_installed')
            return Response(
                {'error': 'OCR service is not configured. Install Tesseract OCR and restart the backend.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except pytesseract.TesseractError:
            logger.exception('Tesseract failed while processing a pack image.')
            _audit_ocr(request.user, 'failed', 'tesseract_error')
            return Response({'error': 'OCR could not process this image. Try a clearer photo.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        batch_value = result['batch_number']['value']
        match = None
        if batch_value:
            match = Batch.objects.select_related('product').filter(
                batch_number__iexact=batch_value
            ).first()
        result['registry_match'] = None if match is None else {
            'batch_number': match.batch_number,
            'product': match.product.brand_name,
            'generic_name': match.product.generic_name,
        }
        _audit_ocr(request.user, 'success', registry_found=match is not None)
        return Response(result)


class MedicineChatAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ChatThrottle]

    @extend_schema(
        operation_id='medicine_chat',
        summary='Ask a grounded medicine information question',
        request=ChatRequestSerializer,
        responses={
            200: ChatResponseSerializer,
            400: {'type': 'object', 'additionalProperties': True},
            503: {'type': 'object', 'additionalProperties': True},
        },
    )
    def post(self, request):
        if not SystemSettings.get_settings().chatbot_enabled:
            return Response({'error': 'Medicine information chat is disabled by the administrator.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        values = serializer.validated_data
        language = detect_language(values['question'], values.get('language'))
        log_question(values['question'], language)
        try:
            result = answer_medicine_question(
                values['code'],
                values['question'],
                requested_language=language,
                medicine_query=values.get('medicine'),
            )
        except (ValueError, DatabaseError, requests.RequestException, KeyError, TypeError):
            logger.exception('Medicine chat request could not be completed.')
            return Response(
                {'error': 'The medicine information service is temporarily unavailable.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        history = request.session.get('medicine_chat_history', [])
        history.append({
            'question': values['question'],
            'answer': result['answer'],
            'language': result['language'],
        })
        request.session['medicine_chat_history'] = history[-10:]
        request.session.modified = True
        return Response(result)


def _audit_ocr(actor, outcome, reason=None, registry_found=None):
    details = {}
    if reason:
        details['reason'] = reason
    if registry_found is not None:
        details['registry_found'] = registry_found
    AIActionAudit.objects.create(actor=actor, action='pack_ocr', outcome=outcome, details=details)
