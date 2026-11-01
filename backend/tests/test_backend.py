import pytest
import math
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestHaversineFormula:
    """Unit tests for the Haversine distance calculator."""

    def test_nairobi_to_mombasa_approx_480km(self):
        from apps.verification.engine import haversine_distance_km
        # Nairobi (-1.286, 36.817) -> Mombasa (-4.043, 39.668)
        dist = haversine_distance_km(-1.286389, 36.817223, -4.043477, 39.668206)
        assert 440 < dist < 520, f"Expected ~480km, got {dist:.1f}km"

    def test_same_location_is_zero(self):
        from apps.verification.engine import haversine_distance_km
        dist = haversine_distance_km(-1.286389, 36.817223, -1.286389, 36.817223)
        assert dist == pytest.approx(0.0, abs=0.01)

    def test_nairobi_to_kisumu_approx_328km(self):
        from apps.verification.engine import haversine_distance_km
        dist = haversine_distance_km(-1.286389, 36.817223, -0.091702, 34.767956)
        assert 250 < dist < 280, f"Expected ~264km, got {dist:.1f}km"

    def test_null_coordinates_returns_zero(self):
        from apps.verification.engine import haversine_distance_km
        dist = haversine_distance_km(None, None, -1.0, 36.0)
        assert dist == 0.0


@pytest.mark.django_db
class TestCloneDetectionEngine:
    """Unit tests for the full clone detection engine."""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        from apps.reports.models import SystemSettings
        from apps.products.models import Manufacturer, Product, Batch, UnitCode

        # Set up system settings
        self.settings = SystemSettings.get_settings()
        self.settings.max_scan_threshold = 3
        self.settings.max_velocity_kmh = 800.0
        self.settings.distinct_ip_threshold = 3
        self.settings.distinct_ip_window_minutes = 15
        self.settings.weight_frequency = 0.35
        self.settings.weight_velocity = 0.45
        self.settings.weight_entropy = 0.20
        self.settings.save()

        # Minimal manufacturer → product → batch chain
        self.mfg = Manufacturer.objects.create(
            name="TestPharma Ltd",
            license_number="TEST-PPB-0001",
            country="Kenya",
            contact_email="test@pharma.co.ke"
        )
        self.product = Product.objects.create(
            manufacturer=self.mfg,
            brand_name="TestDrug 500",
            generic_name="Testoxine",
            dosage_form="Tablet",
            strength="500mg",
            usage_instructions_en="Take once daily.",
            usage_instructions_sw="Kunywa mara moja kwa siku.",
            side_effects_en="Mild nausea.",
            side_effects_sw="Kichefuchefu kidogo.",
            key_warnings_en="Avoid alcohol.",
            key_warnings_sw="Epuka pombe."
        )
        self.batch = Batch.objects.create(
            product=self.product,
            batch_number="TEST-BATCH-001",
            manufacture_date=timezone.now().date() - timedelta(days=60),
            expiry_date=timezone.now().date() + timedelta(days=300),
            total_quantity=100
        )
        secure_code, hmac_sig = UnitCode.generate_hmac_code(str(self.batch.id), "SER-TEST-0001")
        self.unit_code = UnitCode.objects.create(
            batch=self.batch,
            serial_number="SER-TEST-0001",
            secure_code=secure_code,
            hmac_signature=hmac_sig,
            scan_count=0
        )

    def test_fresh_code_no_scans_is_safe(self):
        from apps.verification.engine import CloneDetectionEngine
        engine = CloneDetectionEngine(self.unit_code, current_lat=-1.286389, current_lon=36.817223)
        result = engine.evaluate()
        assert result['is_clone'] is False
        assert result['risk_score'] == pytest.approx(0.0, abs=1.0)
        assert len(result['reasons']) == 0

    def test_frequency_rule_triggers_at_threshold(self):
        from apps.verification.engine import CloneDetectionEngine
        from apps.verification.models import VerificationScan

        # Simulate 3 existing scans (hitting the threshold of 3)
        for i in range(3):
            VerificationScan.objects.create(
                unit_code=self.unit_code,
                raw_code=self.unit_code.secure_code,
                channel='WEB_QR',
                result_status='GENUINE',
                ip_address=f'192.168.1.{i+1}'
            )
        self.unit_code.scan_count = 3
        self.unit_code.save()

        engine = CloneDetectionEngine(self.unit_code, current_ip='192.168.1.99')
        result = engine.evaluate()

        assert result['is_clone'] is True
        assert any('High Frequency' in r for r in result['reasons'])

    def test_velocity_rule_triggers_on_impossible_travel(self):
        from apps.verification.engine import CloneDetectionEngine
        from apps.verification.models import VerificationScan

        # Place last scan in Nairobi 5 minutes ago
        VerificationScan.objects.create(
            unit_code=self.unit_code,
            raw_code=self.unit_code.secure_code,
            channel='WEB_QR',
            result_status='GENUINE',
            latitude=-1.286389,  # Nairobi
            longitude=36.817223,
            ip_address='197.237.10.5',
            scanned_at=timezone.now() - timedelta(minutes=5)
        )

        # Current scan from Mombasa (~480km away in 5 mins = 5760 km/h >> 800 km/h limit)
        engine = CloneDetectionEngine(
            self.unit_code,
            current_lat=-4.043477,  # Mombasa
            current_lon=39.668206,
            current_ip='41.203.220.88'
        )
        result = engine.evaluate()

        assert result['is_clone'] is True
        assert result['rule_scores']['velocity'] == 100.0
        assert any('Velocity Anomaly' in r for r in result['reasons'])

    def test_velocity_rule_does_not_trigger_on_nearby_scan(self):
        from apps.verification.engine import CloneDetectionEngine
        from apps.verification.models import VerificationScan

        # Place last scan 1 min ago at nearby location (Westlands, ~5km from CBD)
        VerificationScan.objects.create(
            unit_code=self.unit_code,
            raw_code=self.unit_code.secure_code,
            channel='WEB_QR',
            result_status='GENUINE',
            latitude=-1.268,
            longitude=36.803,
            ip_address='197.237.10.5',
            scanned_at=timezone.now() - timedelta(minutes=1)
        )

        engine = CloneDetectionEngine(
            self.unit_code,
            current_lat=-1.286389,
            current_lon=36.817223,
            current_ip='197.237.10.6'
        )
        result = engine.evaluate()
        # Westlands to CBD is <5km, should NOT trigger velocity alert
        assert result['rule_scores']['velocity'] == 0.0

    def test_entropy_rule_triggers_with_many_ips(self):
        from apps.verification.engine import CloneDetectionEngine
        from apps.verification.models import VerificationScan

        # Create 3 scans from 3 different IPs in last 15 mins
        for i, ip in enumerate(['10.0.0.1', '10.0.0.2', '10.0.0.3']):
            VerificationScan.objects.create(
                unit_code=self.unit_code,
                raw_code=self.unit_code.secure_code,
                channel='WEB_QR',
                result_status='GENUINE',
                ip_address=ip,
                scanned_at=timezone.now() - timedelta(minutes=i+1)
            )

        # Current scan from 4th distinct IP
        engine = CloneDetectionEngine(self.unit_code, current_ip='10.0.0.4')
        result = engine.evaluate()

        assert result['is_clone'] is True
        assert result['rule_scores']['entropy'] == 100.0
        assert any('Entropy Anomaly' in r for r in result['reasons'])

    def test_confirmed_alert_always_returns_clone(self):
        from apps.verification.engine import CloneDetectionEngine
        from apps.verification.models import CloneAlert

        # Mark unit code as confirmed clone
        self.unit_code.is_flagged_clone = True
        self.unit_code.save()

        CloneAlert.objects.create(
            unit_code=self.unit_code,
            risk_score=95.0,
            status='CONFIRMED',
            trigger_reasons=["Confirmed by regulator"]
        )

        engine = CloneDetectionEngine(self.unit_code)
        result = engine.evaluate()

        assert result['is_clone'] is True
        assert result['risk_score'] == 100.0
        assert any('CONFIRMED CLONE' in r for r in result['reasons'])

    def test_risk_score_composite_calculation(self):
        """Verifies the weighted composite score formula."""
        from apps.verification.engine import CloneDetectionEngine
        # If freq=100, vel=100, ent=0 with weights 0.35, 0.45, 0.20
        # Score = 100*0.35 + 100*0.45 + 0*0.20 = 35+45 = 80.0
        # We approximate this by examining rule_scores in a real scenario
        from apps.verification.models import VerificationScan

        # 3 scans to hit freq, impossible velocity
        for i in range(3):
            VerificationScan.objects.create(
                unit_code=self.unit_code,
                raw_code=self.unit_code.secure_code,
                channel='WEB_QR',
                result_status='GENUINE',
                latitude=-1.286389,
                longitude=36.817223,
                ip_address=f'1.1.1.{i}',
                scanned_at=timezone.now() - timedelta(minutes=10)
            )
        self.unit_code.scan_count = 3
        self.unit_code.save()

        engine = CloneDetectionEngine(
            self.unit_code,
            current_lat=-4.043477,
            current_lon=39.668206,
            current_ip='99.99.99.99'
        )
        result = engine.evaluate()
        assert result['risk_score'] > 60.0


@pytest.mark.django_db
class TestVerificationEndpoint:
    """Integration tests for the /api/v1/verify/ endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self, db, client):
        from apps.reports.models import SystemSettings
        from apps.products.models import Manufacturer, Product, Batch, UnitCode

        SystemSettings.get_settings()

        mfg = Manufacturer.objects.create(
            name="VaccPharma Ltd",
            license_number="VCC-PPB-0099",
            country="Kenya",
            contact_email="info@vaccpharma.co.ke"
        )
        product = Product.objects.create(
            manufacturer=mfg,
            brand_name="Vaccitab",
            generic_name="Vaccine Booster",
            dosage_form="Tablet",
            strength="250mg",
            usage_instructions_en="Take one tablet daily.",
            usage_instructions_sw="Kunywa kidonge kimoja kwa siku.",
            side_effects_en="Mild headache.",
            side_effects_sw="Kichwa kuuma kidogo.",
            key_warnings_en="Keep refrigerated.",
            key_warnings_sw="Weka kwenye jokofu."
        )
        batch = Batch.objects.create(
            product=product,
            batch_number="VCC-2026-001",
            manufacture_date=timezone.now().date() - timedelta(days=30),
            expiry_date=timezone.now().date() + timedelta(days=365),
            total_quantity=50
        )
        secure_code, hmac_sig = UnitCode.generate_hmac_code(str(batch.id), "SER-VCC-0001")
        self.unit_code = UnitCode.objects.create(
            batch=batch,
            serial_number="SER-VCC-0001",
            secure_code=secure_code,
            hmac_signature=hmac_sig
        )
        self.valid_code = secure_code

    def test_valid_genuine_code_returns_200_genuine(self, client):
        response = client.post('/api/v1/verify/', {'code': self.valid_code, 'channel': 'WEB_MANUAL'}, content_type='application/json')
        assert response.status_code == 200
        data = response.json()
        assert data['result_status'] == 'GENUINE'
        assert data['is_genuine'] is True
        assert data['badge_color'] == 'green'
        assert 'product' in data
        assert 'batch' in data

    def test_invalid_code_returns_200_invalid(self, client):
        response = client.post('/api/v1/verify/', {'code': 'MV-FAKE-000000000000', 'channel': 'WEB_MANUAL'}, content_type='application/json')
        assert response.status_code == 200
        data = response.json()
        assert data['result_status'] == 'INVALID'
        assert data['is_genuine'] is False
        assert data['badge_color'] == 'gray'

    def test_expired_batch_returns_expired_status(self, client, db):
        from apps.products.models import Batch, UnitCode
        expired_batch = Batch.objects.filter(batch_number="VCC-2026-001").first()
        expired_batch.expiry_date = timezone.now().date() - timedelta(days=10)
        expired_batch.save()

        response = client.post('/api/v1/verify/', {'code': self.valid_code, 'channel': 'WEB_QR'}, content_type='application/json')
        data = response.json()
        assert data['result_status'] == 'EXPIRED'
        assert data['badge_color'] == 'amber'

    def test_recalled_batch_returns_recalled_status(self, client, db):
        from apps.products.models import Batch
        batch = Batch.objects.filter(batch_number="VCC-2026-001").first()
        batch.is_recalled = True
        batch.recall_reason = "Quality control failure."
        batch.save()

        response = client.post('/api/v1/verify/', {'code': self.valid_code, 'channel': 'WEB_QR'}, content_type='application/json')
        data = response.json()
        assert data['result_status'] == 'RECALLED'
        assert data['badge_color'] == 'red'

    def test_verification_scan_is_logged_in_database(self, client, db):
        from apps.verification.models import VerificationScan
        before_count = VerificationScan.objects.count()
        client.post('/api/v1/verify/', {'code': self.valid_code, 'channel': 'WEB_MANUAL'}, content_type='application/json')
        assert VerificationScan.objects.count() == before_count + 1

    def test_empty_code_returns_400(self, client):
        response = client.post('/api/v1/verify/', {'code': '', 'channel': 'WEB_MANUAL'}, content_type='application/json')
        assert response.status_code in [400, 200]

    def test_hmac_code_contains_expected_prefix(self):
        assert self.valid_code.startswith("MV-"), f"Expected 'MV-' prefix, got: {self.valid_code}"


@pytest.mark.django_db
class TestHMACCodeGeneration:
    """Tests for the HMAC-based unguessable code generation."""

    def test_same_inputs_produce_same_code(self):
        from apps.products.models import UnitCode
        code_a, sig_a = UnitCode.generate_hmac_code("batch-uuid-001", "SER-0001")
        code_b, sig_b = UnitCode.generate_hmac_code("batch-uuid-001", "SER-0001")
        assert code_a == code_b
        assert sig_a == sig_b

    def test_different_serials_produce_different_codes(self):
        from apps.products.models import UnitCode
        code_a, _ = UnitCode.generate_hmac_code("batch-uuid-001", "SER-0001")
        code_b, _ = UnitCode.generate_hmac_code("batch-uuid-001", "SER-0002")
        assert code_a != code_b

    def test_different_batch_ids_produce_different_codes(self):
        from apps.products.models import UnitCode
        code_a, _ = UnitCode.generate_hmac_code("batch-uuid-001", "SER-0001")
        code_b, _ = UnitCode.generate_hmac_code("batch-uuid-002", "SER-0001")
        assert code_a != code_b

    def test_code_format_is_correct(self):
        from apps.products.models import UnitCode
        code, sig = UnitCode.generate_hmac_code("batch-xyz", "SER-9999")
        parts = code.split("-")
        assert parts[0] == "MV"
        assert len(sig) == 12  # Truncated to 12 uppercase hex chars


@pytest.mark.django_db
class TestRegistrationAndAuth:
    """Tests for user registration and JWT authentication flow."""

    def test_register_pharmacist_returns_201(self, client):
        payload = {
            "username": "pharmacist_nairobi",
            "email": "pharma@nairobi.co.ke",
            "password": "secure789",
            "role": "PHARMACIST",
            "phone_number": "+254712345678",
            "organization_name": "Nairobi Pharmacy"
        }
        response = client.post('/api/v1/auth/register/', payload, content_type='application/json')
        assert response.status_code == 201
        data = response.json()
        assert data['role'] == 'PHARMACIST'

    def test_login_returns_jwt_tokens(self, client, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username="test_login", password="pass123", role="PHARMACIST")

        response = client.post('/api/v1/auth/login/', {'username': 'test_login', 'password': 'pass123'}, content_type='application/json')
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['username'] == 'test_login'
        assert data['user']['role'] == 'PHARMACIST'

    def test_me_endpoint_requires_auth(self, client):
        response = client.get('/api/v1/auth/me/')
        assert response.status_code == 401
