import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.ai.chat import UNKNOWN, _context_supported, answer_medicine_question, detect_language
from apps.ai.models import MedicineInfo
from apps.products.models import Batch, Manufacturer, Product, UnitCode
from apps.verification.models import VerificationScan
from django.utils import timezone
from datetime import timedelta


QUESTION_TEMPLATES = (
    ('What is this medicine used for?', 'Dawa hii hutumika kwa nini?', 'uses'),
    ('What are common side effects?', 'Madhara ya kawaida ni yapi?', 'side_effects'),
    ('How should I store it?', 'Nihifadhi dawa hii vipi?', 'storage'),
)


class Command(BaseCommand):
    help = 'Evaluate bilingual chatbot grounding, refusal, language match, and latency.'

    def handle(self, *args, **options):
        call_command('seed_medicine_info', verbosity=0)
        medicines = list(MedicineInfo.objects.all())
        if len(medicines) < 10:
            raise CommandError('Seed at least ten MedicineInfo records before evaluation.')

        genuine_codes = {item.generic_name: _ensure_genuine_code(item) for item in medicines[:10]}
        total = 0
        grounded = 0
        language_matches = 0
        latency_total = 0.0
        for record in medicines[:10]:
            code = genuine_codes[record.generic_name]
            for language in ('en', 'sw'):
                for question_en, question_sw, section in QUESTION_TEMPLATES:
                    question = question_en if language == 'en' else question_sw
                    expected = getattr(record, f'{section}_{language}')
                    started = time.perf_counter()
                    result = answer_medicine_question(
                        code, question, requested_language=language, medicine_query=record.generic_name
                    )
                    latency_total += time.perf_counter() - started
                    total += 1
                    answer_body = result['answer'].replace(
                        ' ' + ('This is general information, not medical advice. Ask a pharmacist or doctor.' if language == 'en'
                               else 'Haya ni maelezo ya jumla, si ushauri wa matibabu. Muulize mfamasia au daktari.'),
                        '',
                    )
                    context = getattr(record, f'{section}_{language}')
                    grounded += bool(expected and expected in answer_body and _context_supported(answer_body, context))
                    language_matches += result['language'] == language and detect_language(result['answer']) == language

        refusal_questions = [
            ('en', 'Does this medicine interact with my other medicines?'),
            ('sw', 'Je, dawa hii ina mwingiliano gani na dawa zangu nyingine?'),
            ('en', 'Can you diagnose why I have a headache?'),
            ('sw', 'Unaweza kugundua kwa nini ninaumwa kichwa?'),
        ]
        refusals_correct = 0
        for index, (language, question) in enumerate(refusal_questions):
            record = medicines[index % len(medicines)]
            result = answer_medicine_question(
                genuine_codes[record.generic_name],
                question,
                requested_language=language,
                medicine_query=record.generic_name,
            )
            expected_refusal = UNKNOWN[language].split('.')[0].casefold()
            refusals_correct += expected_refusal in result['answer'].casefold()

        refusal_rate = refusals_correct / len(refusal_questions)
        self.stdout.write('Chatbot evaluation summary')
        self.stdout.write(f'Question/answer pairs: {total} (English and Swahili)')
        self.stdout.write(f'Grounded answers: {grounded / total:.3f} ({grounded}/{total})')
        self.stdout.write(f'Refusal correctness: {refusal_rate:.3f} ({refusals_correct}/{len(refusal_questions)})')
        self.stdout.write(f'Language match rate: {language_matches / total:.3f} ({language_matches}/{total})')
        self.stdout.write(f'Average latency: {latency_total / total * 1000:.1f} ms')


def _ensure_genuine_code(info):
    manufacturer, _ = Manufacturer.objects.get_or_create(
        license_number='MV-AI-CHAT-EVAL',
        defaults={'name': 'MediVerify Chat Evaluation', 'contact_email': 'chat-eval@mediverify.invalid'},
    )
    brand = f'{info.generic_name} Chat Evaluation'
    product, _ = Product.objects.get_or_create(
        manufacturer=manufacturer,
        brand_name=brand,
        defaults={
            'generic_name': info.generic_name,
            'strength': 'Sample',
            'usage_instructions_en': 'Sample evaluation record.',
            'usage_instructions_sw': 'Rekodi ya tathmini ya mfano.',
            'side_effects_en': 'Sample evaluation record.',
            'side_effects_sw': 'Rekodi ya tathmini ya mfano.',
            'key_warnings_en': 'Not for clinical use.',
            'key_warnings_sw': 'Si kwa matumizi ya kliniki.',
        },
    )
    batch_number = f'MV-AI-CHAT-EVAL-{product.id.hex[:10]}'
    batch, _ = Batch.objects.get_or_create(
        batch_number=batch_number,
        defaults={
            'product': product,
            'manufacture_date': timezone.now().date() - timedelta(days=1),
            'expiry_date': timezone.now().date() + timedelta(days=365),
        },
    )
    serial = f'CHAT-EVAL-{product.id.hex[:12]}'
    secure_code, signature = UnitCode.generate_hmac_code(str(batch.id), serial)
    code, _ = UnitCode.objects.get_or_create(
        batch=batch,
        serial_number=serial,
        defaults={'secure_code': secure_code, 'hmac_signature': signature},
    )
    if not VerificationScan.objects.filter(unit_code=code, result_status='GENUINE').exists():
        VerificationScan.objects.create(
            unit_code=code,
            raw_code=code.secure_code,
            channel='WEB_MANUAL',
            result_status='GENUINE',
        )
        code.scan_count += 1
        code.save(update_fields=['scan_count'])
    return code.secure_code
