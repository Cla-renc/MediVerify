import logging

from rest_framework import views, status
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings

from apps.products.models import UnitCode
from apps.verification.models import VerificationScan
from apps.reports.models import SuspiciousReport
from apps.reports.models import SystemSettings
from rest_framework.throttling import ScopedRateThrottle
from apps.verification.engine import CloneDetectionEngine
from apps.gateway.africastalking import AfricaTalkingError, callback_is_authorized, send_sms

logger = logging.getLogger(__name__)


class USSDCallbackThrottle(ScopedRateThrottle):
    scope = 'ussd_gateway'


class USSDCallbackAPIView(views.APIView):
    """
    Africa's Talking USSD Gateway Webhook Handler.
    Expected POST params: sessionId, serviceCode, phoneNumber, text
    """
    authentication_classes = []
    permission_classes = []
    throttle_classes = [USSDCallbackThrottle]

    def post(self, request):
        if not callback_is_authorized(request):
            return HttpResponse('END Unauthorized callback', status=status.HTTP_403_FORBIDDEN, content_type='text/plain')

        session_id = request.data.get('sessionId', request.POST.get('sessionId', ''))
        service_code = request.data.get('serviceCode', request.POST.get('serviceCode', '*384#'))
        phone_number = request.data.get('phoneNumber', request.POST.get('phoneNumber', '+254700000000'))
        text = request.data.get('text', request.POST.get('text', '')).strip()

        user_inputs = text.split('*') if text else []

        if not text:
            # Root Menu
            response_text = "CON Welcome to MediVerify Kenya:\n1. Verify Medicine Code\n2. Report Suspicious Product\n3. Badilisha Lugha (Kiswahili)"
        elif user_inputs[0] == '1':
            if len(user_inputs) == 1:
                response_text = "CON Enter medicine serial code (e.g. MV-SER-0001-A1B2):"
            else:
                code_entered = user_inputs[1].strip()
                # Process verification
                res_msg = self._verify_code_for_ussd(code_entered, phone_number, lang='en')
                response_text = f"END {res_msg}"
        elif user_inputs[0] == '2':
            if len(user_inputs) == 1:
                response_text = "CON Enter product name and pharmacy name/location:"
            else:
                details = "*".join(user_inputs[1:])
                SuspiciousReport.objects.create(
                    reporter_phone=phone_number,
                    product_name=details[:100],
                    description=f"Report filed via USSD by {phone_number}: {details}",
                    county="USSD Channel"
                )
                response_text = "END Thank you. Your report has been submitted to the Pharmacy and Poisons Board Kenya."
        elif user_inputs[0] == '3':
            if len(user_inputs) == 1:
                response_text = "CON Chagua Lugha / Select Language:\n1. English\n2. Swahili"
            elif user_inputs[1] == '2':
                response_text = "CON Karibu MediVerify Kenya:\n1. Hakiki Nambari ya Dawa\n2. Ripoti Dawa ya Bandia"
            else:
                response_text = "CON Welcome to MediVerify Kenya:\n1. Verify Medicine Code\n2. Report Suspicious Product"
        else:
            response_text = "END Invalid option selected. Please try again."

        return HttpResponse(response_text, content_type='text/plain')

    def _verify_code_for_ussd(self, code_entered, phone_number, lang='en'):
        try:
            uc = UnitCode.objects.select_related('batch', 'batch__product', 'batch__product__manufacturer').get(secure_code__iexact=code_entered)
        except UnitCode.DoesNotExist:
            VerificationScan.objects.create(raw_code=code_entered, channel='USSD', result_status='INVALID', phone_number=phone_number)
            return "INVALID CODE: Code not found in registry. DO NOT consume this product."

        detector = CloneDetectionEngine(unit_code=uc)
        res = detector.evaluate()

        batch = uc.batch
        product = batch.product

        if batch.is_recalled:
            status_str = "RECALLED"
            msg = f"RECALLED BATCH ({batch.batch_number}): Do not consume. Return to pharmacy."
        elif res['is_clone']:
            status_str = "SUSPECTED_CLONE"
            msg = f"SUSPECTED CLONE CODE (Risk: {res['risk_score']}%): Duplicated code alert. Report to PPB."
        elif batch.is_expired:
            status_str = "EXPIRED"
            msg = f"EXPIRED MEDICINE: Expired on {batch.expiry_date}. Do not use."
        else:
            status_str = "GENUINE"
            msg = f"GENUINE: {product.brand_name} {product.strength} by {product.manufacturer.name}. Exp: {batch.expiry_date}."

        uc.scan_count += 1
        uc.save()

        VerificationScan.objects.create(
            unit_code=uc,
            raw_code=code_entered,
            channel='USSD',
            result_status=status_str if status_str in ['GENUINE', 'EXPIRED', 'RECALLED', 'SUSPECTED_CLONE'] else 'INVALID',
            phone_number=phone_number
        )

        return msg

class SMSCallbackAPIView(views.APIView):
    """
    Africa's Talking SMS Webhook Handler.
    Expected POST params: from, text
    """
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'sms_info'

    def post(self, request):
        if not callback_is_authorized(request):
            return Response({'error': 'Unauthorized callback.'}, status=status.HTTP_403_FORBIDDEN)

        sender_phone = request.data.get('from', request.POST.get('from', '+254700000000'))
        sms_text = request.data.get('text', request.POST.get('text', '')).strip()

        if not sms_text:
            reply_message = "Send medicine code (e.g. MV-SER-0001-A1B2) to verify."
            if settings.AFRICASTALKING_ENABLED:
                return self._send_live_reply(sender_phone, reply_message, sms_text)
            return Response({"response": reply_message}, status=status.HTTP_200_OK)

        if sms_text.upper().startswith('INFO '):
            if not SystemSettings.get_settings().chatbot_enabled:
                reply_message = 'Medicine information chat is currently unavailable.'
            else:
                parts = sms_text.split()
                if len(parts) not in (2, 3) or (len(parts) == 3 and parts[2].upper() != 'SW'):
                    reply_message = 'Use INFO <code> or INFO <code> SW.'
                else:
                    code = parts[1]
                    language = 'sw' if len(parts) == 3 else 'en'
                    verify_message = USSDCallbackAPIView()._verify_code_for_ussd(code, sender_phone, lang=language)
                    if not verify_message.startswith('GENUINE:'):
                        reply_message = verify_message
                    else:
                        from apps.ai.chat import answer_medicine_question, log_question

                        question = 'What is this medicine used for?' if language == 'en' else 'Dawa hii hutumika kwa nini?'
                        log_question(question, language)
                        reply_message = answer_medicine_question(code, question, requested_language=language)['answer']
            reply_message = reply_message[:157] + '...' if len(reply_message) > 160 else reply_message
            if settings.AFRICASTALKING_ENABLED:
                return self._send_live_reply(sender_phone, reply_message, sms_text)
            return Response({
                'sender': sender_phone,
                'received_text': sms_text,
                'reply_message': reply_message,
                'status': 'SUCCESS',
            }, status=status.HTTP_200_OK)

        # Execute code verification
        ussd_handler = USSDCallbackAPIView()
        reply_message = ussd_handler._verify_code_for_ussd(sms_text, sender_phone, lang='en')

        if settings.AFRICASTALKING_ENABLED:
            return self._send_live_reply(sender_phone, reply_message, sms_text)

        return Response({
            "sender": sender_phone,
            "received_text": sms_text,
            "reply_message": reply_message,
            "status": "SUCCESS"
        }, status=status.HTTP_200_OK)

    @staticmethod
    def _send_live_reply(sender_phone, reply_message, sms_text):
        try:
            send_sms(sender_phone, reply_message)
        except AfricaTalkingError:
            logger.exception("Could not send Africa's Talking SMS response.")
            return Response(
                {'error': 'SMS delivery failed. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({
            'sender': sender_phone,
            'received_text': sms_text,
            'status': 'SUCCESS',
        }, status=status.HTTP_200_OK)
