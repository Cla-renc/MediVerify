import hashlib
import hmac
import re

from django.conf import settings

from apps.ai.models import ChatQuestionLog, MedicineInfo
from apps.products.models import UnitCode
from apps.verification.models import VerificationScan


DISCLAIMERS = {
    'en': 'This is general information, not medical advice. Ask a pharmacist or doctor.',
    'sw': 'Haya ni maelezo ya jumla, si ushauri wa matibabu. Muulize mfamasia au daktari.',
}
UNKNOWN = {
    'en': "I don't know from the available medicine information. Please ask a pharmacist or doctor.",
    'sw': 'Sina taarifa hii kwenye maelezo ya dawa yaliyopo. Tafadhali muulize mfamasia au daktari.',
}
EMERGENCY = {
    'en': 'This may be an emergency. Seek medical care now or contact local emergency services.',
    'sw': 'Hii inaweza kuwa dharura. Tafuta huduma ya matibabu sasa au piga huduma za dharura za eneo lako.',
}
SW_MARKERS = {
    'dawa', 'matumizi', 'madhara', 'jinsi', 'nini', 'tafadhali', 'kuhusu', 'kwa', 'naweza',
    'uhifadhi', 'hifadhi', 'kwenye', 'hutumika', 'fuata', 'mjamzito', 'ujauzito', 'muulize', 'mfamasia',
}
EMERGENCY_MARKERS = (
    'difficulty breathing', 'cannot breathe', "can't breathe", 'breathing difficulty',
    'severe allergic', 'anaphylaxis', 'face swelling', 'swollen face', 'throat closing',
    'overdose', 'overdosed', 'took too much', 'too many pills', 'chest pain',
    'pregnancy concern', 'pregnant and bleeding', 'hard to breathe',
    'pregnancy', 'pregnant', 'ujauzito', 'mjamzito',
    'kupumua kwa shida', 'kupumua kwa taabu', 'mzio mkali', 'kuvimba uso',
    'dawa nyingi', 'kumeza dawa nyingi',
    'amezidisha dawa', 'maumivu ya kifua', 'ujauzito na damu',
)
PERSONALIZED_MARKERS = (
    'should i take', 'can i take', 'how much should', 'my dose', 'what dose',
    'dose should i', 'dose for me', 'dose for my child', 'change my dose',
    'should i stop', 'should i start', 'should i change', 'should i continue',
    'can i stop', 'can i start', 'stop taking', 'start taking', 'stop my medicine',
    'start my medicine', 'change my treatment', 'change my medication',
    'ni kiasi gani', 'ninywe kiasi', 'nipe kipimo', 'kipimo changu', 'kipimo cha mtoto',
    'niache kutumia', 'nibadilishe kipimo', 'nianze kutumia',
)
STOPWORDS = {
    'a', 'an', 'the', 'is', 'are', 'what', 'how', 'when', 'where', 'why', 'do', 'does',
    'it', 'this', 'that', 'for', 'of', 'and', 'or', 'to', 'in', 'on', 'with', 'my', 'me',
    'please', 'tell', 'about', 'can', 'i', 'should', 'usually', 'medicine', 'dawa', 'hii',
    'ni', 'nini', 'jinsi', 'gani', 'ya', 'wa', 'na', 'kwa', 'kuhusu', 'tafadhali',
}


def detect_language(question, requested=None):
    if requested in ('en', 'sw'):
        return requested
    words = set(re.findall(r'[a-zA-Z]+', question.lower()))
    return 'sw' if len(words & SW_MARKERS) >= 1 else 'en'


def is_emergency(question):
    lowered = question.casefold()
    return any(marker in lowered for marker in EMERGENCY_MARKERS)


def _is_personalized_request(question):
    lowered = question.casefold()
    return any(marker in lowered for marker in PERSONALIZED_MARKERS)


def _field_value(record, field, language):
    return getattr(record, f'{field}_{language}', '').strip()


def _requested_section(question):
    words = question.casefold()
    if any(term in words for term in ('side effect', 'adverse effect', 'madhara', 'athari')):
        return 'side_effects'
    if any(term in words for term in ('store', 'storage', 'keep', 'hifadhi', 'uhifadhi')):
        return 'storage'
    if any(term in words for term in ('warning', 'caution', 'tahadhari', 'hatari')):
        return 'warnings'
    if any(term in words for term in ('doctor', 'hospital', 'daktari', 'hospitali', 'help')):
        return 'see_doctor'
    if any(term in words for term in ('what is', 'used for', 'uses', 'matumizi', 'hutumika', 'nini')):
        return 'uses'
    if any(term in words for term in ('take', 'taken', 'how to use', 'tumia', 'dose', 'kipimo', 'usual use')):
        return 'usual_use'
    return None


def _find_records(unit_code, medicine_query=None):
    records = list(MedicineInfo.objects.all())
    if medicine_query:
        needle = medicine_query.casefold().strip()
        matching = [
            item for item in records
            if needle in item.generic_name.casefold()
            or any(needle in name.casefold() for name in item.brand_names)
        ]
        if matching:
            return matching
        terms = set(re.findall(r'[a-zA-Z]{4,}', needle))
        matching = [
            item for item in records
            if any(term in item.generic_name.casefold() for term in terms)
            or any(any(term in brand.casefold() for term in terms) for brand in item.brand_names)
        ]
        if matching:
            return matching
        return []

    product = unit_code.batch.product
    names = {product.generic_name.casefold(), product.brand_name.casefold()}
    return [
        item for item in records
        if item.generic_name.casefold() in names
        or any(brand.casefold() in names for brand in item.brand_names)
    ]


def _context_for(record, language):
    fields = ('uses', 'usual_use', 'side_effects', 'warnings', 'storage', 'see_doctor')
    return '\n'.join(
        f'{field}: {_field_value(record, field, language)}'
        for field in fields
        if _field_value(record, field, language)
    )


def _direct_answer(records, section, language):
    if not section:
        return None
    values = [_field_value(record, section, language) for record in records]
    values = [value for value in values if value]
    return '\n'.join(values) if values else None


def _context_supported(answer, context):
    context_words = set(re.findall(r'\w+', context.casefold()))
    answer_words = {
        word for word in re.findall(r'\w+', answer.casefold())
        if len(word) > 2 and word not in STOPWORDS
    }
    return bool(answer_words) and answer_words.issubset(context_words)


def answer_medicine_question(code, question, requested_language=None, medicine_query=None):
    language = detect_language(question, requested_language)
    if is_emergency(question):
        return {'answer': f"{EMERGENCY[language]} {DISCLAIMERS[language]}", 'language': language, 'emergency': True}

    unit_code = UnitCode.objects.select_related('batch', 'batch__product').filter(
        secure_code__iexact=code.strip()
    ).first()
    if not unit_code:
        return {'answer': f"{UNKNOWN[language]} {DISCLAIMERS[language]}", 'language': language, 'emergency': False}
    batch = unit_code.batch
    latest_scan = VerificationScan.objects.filter(unit_code=unit_code).order_by('-scanned_at').first()
    is_genuine = (
        not batch.is_recalled
        and not batch.is_expired
        and not unit_code.is_flagged_clone
        and latest_scan is not None
        and latest_scan.result_status == 'GENUINE'
    )
    if not is_genuine:
        return {'answer': f"{UNKNOWN[language]} {DISCLAIMERS[language]}", 'language': language, 'emergency': False}

    records = _find_records(unit_code, medicine_query=medicine_query)
    if not records:
        return {'answer': f"{UNKNOWN[language]} {DISCLAIMERS[language]}", 'language': language, 'emergency': False}
    if _is_personalized_request(question):
        return {'answer': f"{UNKNOWN[language]} {DISCLAIMERS[language]}", 'language': language, 'emergency': False}

    section = _requested_section(question)
    if section is None:
        return {'answer': f"{UNKNOWN[language]} {DISCLAIMERS[language]}", 'language': language, 'emergency': False}
    contexts = [_context_for(record, language) for record in records]
    context = '\n\n'.join(
        f'medicine: {record.generic_name}\nsource: {record.source}\n{section_context}'
        for record, section_context in zip(records, contexts)
    )
    direct = _direct_answer(records, section, language)

    from apps.ai.providers import create_provider

    provider = create_provider()
    answer = direct
    if provider is not None:
        answer = provider.answer(question, context, language)
        if not answer or not _context_supported(answer, context):
            answer = None
    if not answer:
        answer = UNKNOWN[language]
    elif provider is None:
        answer = f'{answer}'
    return {'answer': f'{answer} {DISCLAIMERS[language]}', 'language': language, 'emergency': False}


def log_question(question, language):
    fingerprint = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        question.strip().casefold().encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    ChatQuestionLog.objects.create(
        language=language,
        question_category=_requested_section(question) or 'general',
        question_fingerprint=fingerprint,
    )
