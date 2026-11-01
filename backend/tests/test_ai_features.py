import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.ai.chat import answer_medicine_question, detect_language
from apps.ai.clone_model.features import FEATURE_NAMES, extract_code_features
from apps.ai.clone_model.service import score_code, train_model
from apps.ai.models import MedicineInfo
from apps.ai.ocr import extract_pack_fields
from apps.products.models import UnitCode
from apps.reports.models import SystemSettings
from apps.verification.models import VerificationScan


OCR_SAMPLES = [
    ('Batch No: 24A117\nEXP 06/2027', '24A117', '2027-06-30'),
    ('BN 24A118\nEXP: 06-2027', '24A118', '2027-06-30'),
    ('LOT 24A119\nExp. Date 30/06/2027', '24A119', '2027-06-30'),
    ('BATCH NUMBER: 24A120\nEXPIRY DATE: 2027-06-30', '24A120', '2027-06-30'),
    ('LOT NO 24A121\nUSE BY 30-06-2027', '24A121', '2027-06-30'),
    ('BN: 24A122\nEXP 6/2027', '24A122', '2027-06-30'),
    ('Batch No 24A123\nEXP 06/27', '24A123', '2027-06-30'),
    ('LOT: 24A124\nEXP 1/2028', '24A124', '2028-01-31'),
    ('BATCH 24A125\nEXP. DATE 01-2028', '24A125', '2028-01-31'),
    ('BN 24A126\nEXP 31.12.2028', '24A126', '2028-12-31'),
    ('Batch No: 24A127\nMfg 06/2024\nEXP 06/2027', '24A127', '2027-06-30'),
    ('LOT 24A128\nMFG DATE 30/06/2024\nEXP DATE 30/06/2027', '24A128', '2027-06-30'),
    ('BN 24A129\nMFD: 2024-06-30\nEXP: 2027-06-30', '24A129', '2027-06-30'),
    ('Batch Number 24A130\nMFG 06-2024\nEXP 06-2027', '24A130', '2027-06-30'),
    ('LOT NO: 24A131\nEXPIRY 12/2029', '24A131', '2029-12-31'),
    ('BN: 24A132\nEXP 02/2030', '24A132', '2030-02-28'),
    ('Batch No 24A133\nExpiry Date 15/02/2030', '24A133', '2030-02-15'),
    ('LOT 24A134\nEXP: 15-02-30', '24A134', '2030-02-15'),
    ('BN 24A135\nExp. 2028/12/31', '24A135', '2028-12-31'),
    ('BATCH NO 24A136\nEXP 29/02/2028', '24A136', '2028-02-29'),
    ('LOT 24A137\nEXP 31/04/2028', '24A137', None),
    ('BN 24A138\nMfg. Date 05/2024\nEXP 08/2027', '24A138', '2027-08-31'),
    ('Batch No: 24A139\nMfd 05-2024\nExpiry: 08-2027', '24A139', '2027-08-31'),
    ('LOT 24A140\nEXP DATE: 2027.08.31', '24A140', '2027-08-31'),
    ('BN 24A141\nExp 08/2O27', '24A141', '2027-08-31'),
    ('BN 24A142\nEXP O8/2027', '24A142', '2027-08-31'),
    ('BATCH NO 24AI43\nEXP 08/2027', '24A143', '2027-08-31'),
    ('BATCH 24A144\nMFG 06/2O24\nEXP 08/2027', '24A144', '2027-08-31'),
    ('L0T 24A145\nEXP 08/2027', '24A145', '2027-08-31'),
    ('BN 24A146\nEXPIRY DATE: 08/2027', '24A146', '2027-08-31'),
]


@pytest.mark.parametrize(('label', 'batch', 'expiry'), OCR_SAMPLES)
def test_ocr_parser_handles_label_variants(label, batch, expiry):
    fields = extract_pack_fields(label)
    assert fields['batch_number']['value'] == batch
    assert fields['expiry_date']['value'] == expiry


def test_ocr_parser_extracts_manufacturing_date():
    fields = extract_pack_fields('Batch No: 24A117\nMfg 06/2024\nEXP 06/2027')
    assert fields['manufacturing_date']['value'] == '2024-06-30'


def test_ocr_parser_returns_confidence_for_fields():
    fields = extract_pack_fields('BN 24A117\nEXP 06/2027', confidence=0.91)
    assert fields['batch_number']['confidence'] == 0.91
    assert fields['expiry_date']['confidence'] == 0.91


def _sample_image():
    fixture = Path(__file__).parent / 'fixtures' / 'ocr' / 'CT-BATCH-2026-001__2027-06-30.png'
    return fixture.read_bytes()


def test_pack_ocr_endpoint_returns_registry_match(auth_client_pharmacist, sample_batch):
    sample_batch.batch_number = 'CT-BATCH-2026-001'
    sample_batch.save(update_fields=['batch_number'])
    upload = SimpleUploadedFile('pack.png', _sample_image(), content_type='image/png')
    with patch('apps.ai.views.read_pack_image', return_value={
        'raw_text': 'BATCH NO: CT-BATCH-2026-001\nEXP 06/2027',
        'batch_number': {'value': sample_batch.batch_number, 'confidence': 0.92},
        'expiry_date': {'value': '2027-06-30', 'confidence': 0.9},
        'manufacturing_date': {'value': None, 'confidence': 0},
        'processing_ms': 12.5,
    }):
        response = auth_client_pharmacist.post('/api/ocr/pack/', {'image': upload}, format='multipart')
    assert response.status_code == 200
    assert response.data['registry_match']['batch_number'] == sample_batch.batch_number
    assert response.data['expiry_date']['value'] == '2027-06-30'


def test_pack_ocr_is_pharmacist_only(api_client, auth_client_regulator):
    upload = SimpleUploadedFile('pack.png', _sample_image(), content_type='image/png')
    response = api_client.post('/api/ocr/pack/', {'image': upload}, format='multipart')
    assert response.status_code == 403
    upload = SimpleUploadedFile('pack.png', _sample_image(), content_type='image/png')
    response = auth_client_regulator.post('/api/ocr/pack/', {'image': upload}, format='multipart')
    assert response.status_code == 403


def test_pack_ocr_rejects_uploads_over_5mb(auth_client_pharmacist):
    upload = SimpleUploadedFile('large.png', b'x' * (5 * 1024 * 1024 + 1), content_type='image/png')
    response = auth_client_pharmacist.post('/api/ocr/pack/', {'image': upload}, format='multipart')
    assert response.status_code == 400


def _genuine_scan(unit_code):
    return VerificationScan.objects.create(
        unit_code=unit_code,
        raw_code=unit_code.secure_code,
        channel='WEB_MANUAL',
        result_status='GENUINE',
        ip_address='192.0.2.1',
    )


def test_chat_offline_fallback_returns_matching_section(sample_unit_code, monkeypatch):
    MedicineInfo.objects.create(
        generic_name='Testamine',
        uses_en='Used for mild pain.',
        uses_sw='Hutumika kwa maumivu madogo.',
        source='SAMPLE - must be reviewed by a pharmacist',
    )
    _genuine_scan(sample_unit_code)
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    result = answer_medicine_question(sample_unit_code.secure_code, 'What is it used for?')
    assert result['language'] == 'en'
    assert 'Used for mild pain.' in result['answer']
    assert 'not medical advice' in result['answer']


def test_seeded_beta_flagyl_chat_returns_registered_side_effects(sample_unit_code, monkeypatch):
    product = sample_unit_code.batch.product
    product.brand_name = 'Beta-Flagyl'
    product.generic_name = 'Metronidazole'
    product.save(update_fields=['brand_name', 'generic_name'])
    _genuine_scan(sample_unit_code)
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    call_command('seed_medicine_info')

    result = answer_medicine_question(
        sample_unit_code.secure_code,
        'What are common side effects?',
    )

    assert 'Metallic taste, dark urine, and nausea.' in result['answer']
    assert 'I don\'t know' not in result['answer']


def test_chat_refuses_out_of_context_and_personalized_requests(sample_unit_code):
    MedicineInfo.objects.create(
        generic_name='Testamine',
        uses_en='Used for mild pain.',
        uses_sw='Hutumika kwa maumivu madogo.',
    )
    _genuine_scan(sample_unit_code)
    outside = answer_medicine_question(sample_unit_code.secure_code, 'Does it interact with warfarin?')
    personal = answer_medicine_question(sample_unit_code.secure_code, 'How much should I take?')
    assert "don't know" in outside['answer']
    assert "don't know" in personal['answer']


def test_chat_emergency_overrides_retrieval():
    result = answer_medicine_question('not-a-code', 'I have difficulty breathing')
    assert result['emergency'] is True
    assert 'Seek medical care now' in result['answer']


def test_chat_language_detection_and_toggle():
    assert detect_language('Dawa hii hutumika kwa nini?') == 'sw'
    assert detect_language('Dawa hii hutumika kwa nini?', requested='en') == 'en'


def test_chat_endpoint_logs_only_fingerprint_and_keeps_history_in_session(api_client, sample_unit_code):
    from apps.ai.models import ChatQuestionLog

    MedicineInfo.objects.create(
        generic_name='Testamine',
        uses_en='Used for mild pain.',
        uses_sw='Hutumika kwa maumivu madogo.',
    )
    _genuine_scan(sample_unit_code)
    response = api_client.post('/api/chat/', {
        'code': sample_unit_code.secure_code,
        'question': 'What is it used for?',
    }, format='json')
    assert response.status_code == 200
    assert 'Used for mild pain.' in response.data['answer']
    assert 'medicine_chat_history' in api_client.session
    log = ChatQuestionLog.objects.get()
    assert log.question_category == 'uses'
    assert not hasattr(log, 'question')


def test_chat_endpoint_rejects_overlong_question(api_client, db):
    response = api_client.post('/api/chat/', {'code': 'MV-INVALID', 'question': 'x' * 1001}, format='json')
    assert response.status_code == 400


def test_chat_rejects_ungrounded_llm_output(sample_unit_code, monkeypatch):
    MedicineInfo.objects.create(
        generic_name='Testamine',
        uses_en='Used for mild pain.',
        uses_sw='Hutumika kwa maumivu madogo.',
    )
    _genuine_scan(sample_unit_code)
    fake = type('FakeProvider', (), {'answer': lambda self, question, context, language: 'It cures cancer.'})()
    monkeypatch.setattr('apps.ai.providers.create_provider', lambda: fake)
    result = answer_medicine_question(sample_unit_code.secure_code, 'What is it used for?')
    assert "don't know" in result['answer']


def test_clone_features_include_activity_and_channels(sample_unit_code):
    now = timezone.now()
    events = [
        ('WEB_QR', '192.0.2.1', 'phone-a', -1.2864, 36.8172, 45),
        ('SMS', '192.0.2.2', 'phone-b', -4.0435, 39.6682, 20),
    ]
    for channel, ip, device, latitude, longitude, minutes_ago in events:
        event = VerificationScan.objects.create(
            unit_code=sample_unit_code,
            raw_code=sample_unit_code.secure_code,
            channel=channel,
            result_status='GENUINE',
            ip_address=ip,
            user_agent=device,
            latitude=latitude,
            longitude=longitude,
        )
        event.scanned_at = now - timedelta(minutes=minutes_ago)
        event.save(update_fields=['scanned_at'])
    vector, features = extract_code_features(
        sample_unit_code,
        current_lat=-0.0917,
        current_lon=34.7680,
        current_ip='192.0.2.3',
        current_ua='phone-c',
        channel='USSD',
        now=now,
    )
    assert len(vector) == len(FEATURE_NAMES)
    assert features['scan_total'] == 3
    assert features['scans_1h'] == 3
    assert features['distinct_devices'] == 3
    assert features['distinct_ips'] == 3
    assert features['distinct_locations'] == 3
    assert features['max_speed_kmh'] > 1000
    assert features['channel_sms_ratio'] > 0
    assert features['channel_ussd_ratio'] > 0


def test_clone_model_trains_scores_under_100ms(sample_batch, tmp_path, monkeypatch):
    import apps.ai.clone_model.service as clone_service

    codes = []
    for index in range(12):
        serial = f'ML-TRAIN-{index}'
        secure_code, signature = UnitCode.generate_hmac_code(str(sample_batch.id), serial)
        unit_code = UnitCode.objects.create(
            batch=sample_batch,
            serial_number=serial,
            secure_code=secure_code,
            hmac_signature=signature,
        )
        VerificationScan.objects.create(
            unit_code=unit_code,
            raw_code=secure_code,
            channel='WEB_QR',
            result_status='GENUINE',
            ip_address=f'198.51.100.{index + 1}',
            user_agent=f'device-{index}',
        )
        codes.append(unit_code)
    monkeypatch.setattr(clone_service, 'MODEL_FILE', tmp_path / 'clone_model.joblib')
    version = train_model(seed=9)
    assert version.training_samples == len(codes)
    started = time.perf_counter()
    result = score_code(codes[0])
    assert (time.perf_counter() - started) < 0.1
    assert 0 <= result['score'] <= 100
    assert version.version.startswith('1.')


def test_clone_model_falls_back_to_rules_without_artifact(sample_unit_code, monkeypatch):
    import apps.ai.clone_model.service as clone_service
    from apps.verification.engine import CloneDetectionEngine

    monkeypatch.setattr(clone_service, '_load_artifact', lambda: None)
    config = SystemSettings.get_settings()
    config.ml_enabled = True
    config.save()
    result = CloneDetectionEngine(sample_unit_code).evaluate()
    assert result['ml_score'] is None
    assert result['risk_score'] == result['rule_risk_score']


def test_synthetic_scan_command_accepts_reproducible_seed(db):
    call_command('generate_synthetic_scans', '--seed', '301', '--genuine', '10', '--clones-per-type', '1')
    from apps.ai.models import CloneEvaluationCase

    assert CloneEvaluationCase.objects.filter(attack_type='GENUINE').count() == 10
    assert CloneEvaluationCase.objects.filter(attack_type='DISTANT').count() == 1


@pytest.mark.django_db
def test_seed_data_reuses_manufacturers_on_repeat_runs():
    from apps.products.models import Manufacturer

    call_command('seed_data', verbosity=0)
    call_command('seed_data', verbosity=0)

    assert Manufacturer.objects.count() == 3
    assert Manufacturer.objects.filter(user__isnull=False).count() == 3


@pytest.mark.django_db
def test_clone_evaluation_command_writes_csv_and_chart(tmp_path, monkeypatch):
    import apps.ai.clone_model.service as clone_service
    from apps.ai.models import CloneEvaluationCase

    monkeypatch.setattr(clone_service, 'MODEL_FILE', tmp_path / 'clone_model.joblib')
    call_command('generate_synthetic_scans', '--seed', '302', '--genuine', '10', '--clones-per-type', '2')
    call_command('train_clone_model', '--seed', '42')
    output = tmp_path / 'evaluation'
    call_command('evaluate_clone_detection', '--output-dir', str(output))
    assert CloneEvaluationCase.objects.count() == 18
    assert (output / 'clone_detection_results.csv').is_file()
    assert (output / 'clone_detection_results.png').is_file()


def test_ocr_evaluation_command_reports_exact_match(tmp_path):
    from apps.ai.management.commands import evaluate_ocr

    images = Path(__file__).parent / 'fixtures' / 'ocr'
    output = tmp_path / 'evaluation'
    result = {
        'batch_number': {'value': 'CT-BATCH-2026-001'},
        'expiry_date': {'value': '2027-06-30'},
    }
    with patch.object(evaluate_ocr, 'read_pack_image', return_value=result):
        call_command('evaluate_ocr', '--images', str(images), '--output-dir', str(output))
    assert (output / 'ocr_evaluation_results.csv').is_file()


@pytest.mark.django_db
def test_chatbot_evaluation_command_uses_bilingual_sample_set(monkeypatch, capsys):
    monkeypatch.delenv('LLM_API_KEY', raising=False)
    call_command('evaluate_chatbot')
    output = capsys.readouterr().out
    assert 'Question/answer pairs: 60' in output
    assert 'Refusal correctness:' in output
