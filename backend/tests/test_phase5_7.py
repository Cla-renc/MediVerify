"""
test_phase5_7.py — Tests for Phases 5, 6, and 7 (previously uncovered):
  - Phase 5: Pharmacy inventory add-stock, alerts, trust score
  - Phase 6: Suspicious report submission, heatmap endpoint
  - Phase 7: USSD webhook, SMS webhook, clone alert resolve
"""
import pytest
from datetime import timedelta
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def pharmacy(db):
    from apps.inventory.models import Pharmacy
    return Pharmacy.objects.create(
        name='Nairobi Central Pharmacy',
        license_number='PHARM-TEST-CT-001',
        address='Tom Mboya Street, Nairobi',
        county='Nairobi',
        latitude=-1.286389,
        longitude=36.817223,
    )


@pytest.fixture
def pharmacy_with_user(db, pharmacist_user):
    from apps.inventory.models import Pharmacy
    p = Pharmacy.objects.create(
        user=pharmacist_user,
        name='Test Pharmacist Pharmacy',
        license_number='PHARM-TEST-CT-002',
        address='Kimathi Street, Nairobi',
        county='Nairobi',
    )
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Pharmacy Inventory & Trust Rating
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestInventoryAddStock:
    """Tests for POST /api/v1/pharmacy/stock/add_by_code/"""

    def test_add_stock_by_batch_number_returns_201(
        self, auth_client_pharmacist, sample_batch
    ):
        payload = {
            'secure_code_or_batch': sample_batch.batch_number,
            'quantity': 50,
            'purchase_price': '120.00',
            'selling_price': '150.00',
            'supplier_name': 'Cosmos Distributor',
        }
        response = auth_client_pharmacist.post(
            '/api/v1/pharmacy/stock/add_by_code/', payload, format='json'
        )
        assert response.status_code == 201
        data = response.json()
        assert 'inventory_item' in data
        assert data['inventory_item']['quantity'] == 50

    def test_add_stock_by_unit_code_returns_201(
        self, auth_client_pharmacist, sample_unit_code
    ):
        payload = {
            'secure_code_or_batch': sample_unit_code.secure_code,
            'quantity': 10,
            'purchase_price': '200.00',
            'selling_price': '250.00',
        }
        response = auth_client_pharmacist.post(
            '/api/v1/pharmacy/stock/add_by_code/', payload, format='json'
        )
        assert response.status_code == 201

    def test_add_stock_invalid_code_returns_404(self, auth_client_pharmacist):
        payload = {
            'secure_code_or_batch': 'NONEXISTENT-BATCH-XYZ',
            'quantity': 5,
            'purchase_price': '0',
            'selling_price': '0',
        }
        response = auth_client_pharmacist.post(
            '/api/v1/pharmacy/stock/add_by_code/', payload, format='json'
        )
        assert response.status_code == 404

    def test_add_stock_unauthenticated_returns_401(self, api_client, sample_batch):
        payload = {
            'secure_code_or_batch': sample_batch.batch_number,
            'quantity': 5,
            'purchase_price': '0',
            'selling_price': '0',
        }
        response = api_client.post(
            '/api/v1/pharmacy/stock/add_by_code/', payload, format='json'
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestInventoryAlerts:
    """Tests for GET /api/v1/pharmacy/stock/alerts_and_expiry/"""

    def test_alerts_endpoint_returns_200(self, auth_client_pharmacist):
        response = auth_client_pharmacist.get('/api/v1/pharmacy/stock/alerts_and_expiry/')
        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data
        assert 'recalled_alerts' in data
        assert 'expiring_30_days' in data
        assert 'expired' in data

    def test_expired_batch_appears_in_alerts(
        self, auth_client_pharmacist, pharmacist_user, sample_product
    ):
        from apps.products.models import Batch
        from apps.inventory.models import Pharmacy, InventoryItem

        pharmacy, _ = Pharmacy.objects.get_or_create(
            user=pharmacist_user,
            defaults={
                'name': "Test Pharmacist Pharmacy",
                'license_number': 'PHARM-TEST-CT-003',
                'address': 'Nairobi',
            }
        )
        expired_batch = Batch.objects.create(
            product=sample_product,
            batch_number='EXPIRED-BATCH-TEST-001',
            manufacture_date=timezone.now().date() - timedelta(days=400),
            expiry_date=timezone.now().date() - timedelta(days=30),
            total_quantity=100
        )
        InventoryItem.objects.create(
            pharmacy=pharmacy,
            batch=expired_batch,
            quantity=20,
        )

        response = auth_client_pharmacist.get('/api/v1/pharmacy/stock/alerts_and_expiry/')
        assert response.status_code == 200
        data = response.json()
        assert data['summary']['expired_count'] >= 1


@pytest.mark.django_db
class TestPharmacyTrustRating:
    """Tests for Pharmacy.update_trust_score() algorithm."""

    def test_trust_score_degrades_with_recalled_stock(self, pharmacy):
        # Start at 100, 2 recalled items → 100 - (2 × 15) = 70 → WATCH
        pharmacy.update_trust_score(
            expired_count=0, recalled_count=2, suspicious_reports_count=0
        )
        pharmacy.refresh_from_db()
        assert pharmacy.trust_score == pytest.approx(70.0)
        assert pharmacy.trust_rating == 'WATCH'

    def test_trust_score_flagged_with_many_issues(self, pharmacy):
        # 3 recalled + 5 expired → 100 - 45 - 25 = 30 → FLAGGED
        pharmacy.update_trust_score(
            expired_count=5, recalled_count=3, suspicious_reports_count=0
        )
        pharmacy.refresh_from_db()
        assert pharmacy.trust_score < 50.0
        assert pharmacy.trust_rating == 'FLAGGED'

    def test_trust_score_trusted_when_clean(self, pharmacy):
        pharmacy.update_trust_score(
            expired_count=0, recalled_count=0, suspicious_reports_count=0
        )
        pharmacy.refresh_from_db()
        assert pharmacy.trust_score == pytest.approx(100.0)
        assert pharmacy.trust_rating == 'TRUSTED'

    def test_trust_score_clamped_at_zero(self, pharmacy):
        # Extreme: 10 recalled = 150 penalty → clamped at 0
        pharmacy.update_trust_score(
            expired_count=10, recalled_count=10, suspicious_reports_count=10
        )
        pharmacy.refresh_from_db()
        assert pharmacy.trust_score == pytest.approx(0.0)
        assert pharmacy.trust_rating == 'FLAGGED'


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Suspicious Reports & Heatmap
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSuspiciousReportSubmission:
    """Tests for POST /api/v1/reports/suspicious/"""

    def test_submit_report_returns_201(self, api_client):
        payload = {
            'product_name': 'Fake Paracetamol',
            'description': 'Pills look different — discoloured and crumble easily.',
            'reporter_name': 'Jane Doe',
            'reporter_phone': '+254712345678',
            'county': 'Nairobi',
            'latitude': -1.286389,
            'longitude': 36.817223,
        }
        response = api_client.post(
            '/api/v1/reports/suspicious/', payload, format='json'
        )
        assert response.status_code == 201

    def test_report_requires_product_name(self, api_client):
        payload = {'description': 'Missing product name.', 'county': 'Mombasa'}
        response = api_client.post(
            '/api/v1/reports/suspicious/', payload, format='json'
        )
        assert response.status_code == 400

    def test_heatmap_endpoint_returns_200(self, api_client):
        response = api_client.get('/api/v1/reports/heatmap/')
        assert response.status_code == 200
        data = response.json()
        assert 'markers' in data
        assert 'total_markers' in data

    def test_heatmap_includes_suspicious_reports(self, api_client):
        from apps.reports.models import SuspiciousReport
        SuspiciousReport.objects.create(
            product_name='Counterfeit Amoxicillin',
            description='Reported at Gikomba market.',
            county='Nairobi',
            latitude=-1.286389,
            longitude=36.817223,
        )
        response = api_client.get('/api/v1/reports/heatmap/')
        data = response.json()
        report_markers = [m for m in data['markers'] if m['type'] == 'SUSPICIOUS_REPORT']
        assert len(report_markers) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — USSD / SMS Gateway
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUSSDGateway:
    """Tests for POST /api/v1/gateway/ussd/"""

    def test_root_menu_returned_when_no_input(self, api_client):
        payload = {
            'sessionId': 'test-session-001',
            'serviceCode': '*384#',
            'phoneNumber': '+254700000000',
            'text': '',
        }
        response = api_client.post('/api/v1/gateway/ussd/', payload, format='json')
        assert response.status_code == 200
        assert response.content.startswith(b'CON')
        assert b'Verify' in response.content

    def test_option_1_prompts_for_code(self, api_client):
        payload = {
            'sessionId': 'test-session-002',
            'serviceCode': '*384#',
            'phoneNumber': '+254700000000',
            'text': '1',
        }
        response = api_client.post('/api/v1/gateway/ussd/', payload, format='json')
        assert response.status_code == 200
        assert response.content.startswith(b'CON')
        assert b'serial code' in response.content.lower() or b'medicine' in response.content.lower()

    def test_valid_code_verification_via_ussd(self, api_client, sample_unit_code, system_settings):
        payload = {
            'sessionId': 'test-session-003',
            'serviceCode': '*384#',
            'phoneNumber': '+254712000001',
            'text': f'1*{sample_unit_code.secure_code}',
        }
        response = api_client.post('/api/v1/gateway/ussd/', payload, format='json')
        assert response.status_code == 200
        assert response.content.startswith(b'END')
        assert b'GENUINE' in response.content

    def test_invalid_code_returns_invalid_message(self, api_client, system_settings):
        payload = {
            'sessionId': 'test-session-004',
            'serviceCode': '*384#',
            'phoneNumber': '+254712000002',
            'text': '1*MV-FAKE-CODE-000000000000',
        }
        response = api_client.post('/api/v1/gateway/ussd/', payload, format='json')
        assert response.status_code == 200
        assert b'INVALID' in response.content

    def test_option_2_report_submission(self, api_client):
        payload = {
            'sessionId': 'test-session-005',
            'serviceCode': '*384#',
            'phoneNumber': '+254712000003',
            'text': '2*Fake Paracetamol at Gikomba Pharmacy',
        }
        response = api_client.post('/api/v1/gateway/ussd/', payload, format='json')
        assert response.status_code == 200
        assert response.content.startswith(b'END')
        assert b'submitted' in response.content.lower() or b'Thank you' in response.content

    def test_option_3_language_switch(self, api_client):
        payload = {
            'sessionId': 'test-session-006',
            'serviceCode': '*384#',
            'phoneNumber': '+254712000004',
            'text': '3*2',
        }
        response = api_client.post('/api/v1/gateway/ussd/', payload, format='json')
        assert response.status_code == 200
        # Swahili menu
        assert b'Hakiki' in response.content or b'Ripoti' in response.content


@pytest.mark.django_db
class TestSMSGateway:
    """Tests for POST /api/v1/gateway/sms/"""

    def test_empty_sms_returns_help_message(self, api_client):
        payload = {'from': '+254700000000', 'text': ''}
        response = api_client.post('/api/v1/gateway/sms/', payload, format='json')
        assert response.status_code == 200
        data = response.json()
        assert 'response' in data

    def test_valid_code_sms_returns_genuine(
        self, api_client, sample_unit_code, system_settings
    ):
        payload = {
            'from': '+254712000010',
            'text': sample_unit_code.secure_code,
        }
        response = api_client.post('/api/v1/gateway/sms/', payload, format='json')
        assert response.status_code == 200
        data = response.json()
        assert 'reply_message' in data
        assert 'GENUINE' in data['reply_message']

    def test_invalid_code_sms_returns_invalid(self, api_client, system_settings):
        payload = {
            'from': '+254712000011',
            'text': 'MV-BOGUS-XXXX-999999999999',
        }
        response = api_client.post('/api/v1/gateway/sms/', payload, format='json')
        assert response.status_code == 200
        data = response.json()
        assert 'INVALID' in data['reply_message']


@pytest.mark.django_db
class TestCloneAlertResolve:
    """Tests for POST /api/v1/verify/clones/alerts/{id}/resolve/"""

    @pytest.fixture(autouse=True)
    def setup(self, db, sample_unit_code, system_settings):
        from apps.verification.models import CloneAlert
        self.unit_code = sample_unit_code
        self.alert = CloneAlert.objects.create(
            unit_code=sample_unit_code,
            risk_score=75.0,
            status='PENDING',
            trigger_reasons=['High Frequency: Code scanned 5 times (Threshold: 3)']
        )

    def test_regulator_can_confirm_alert(self, auth_client_regulator):
        url = f'/api/v1/verify/clones/alerts/{self.alert.id}/resolve/'
        response = auth_client_regulator.post(url, {'status': 'CONFIRMED'}, format='json')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'CONFIRMED'

        # Unit code should be flagged
        self.unit_code.refresh_from_db()
        assert self.unit_code.is_flagged_clone is True

    def test_regulator_can_dismiss_alert(self, auth_client_regulator):
        url = f'/api/v1/verify/clones/alerts/{self.alert.id}/resolve/'
        response = auth_client_regulator.post(url, {'status': 'DISMISSED'}, format='json')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'DISMISSED'

    def test_invalid_status_returns_400(self, auth_client_regulator):
        url = f'/api/v1/verify/clones/alerts/{self.alert.id}/resolve/'
        response = auth_client_regulator.post(url, {'status': 'BOGUS'}, format='json')
        assert response.status_code == 400

    def test_unauthenticated_resolve_returns_401(self, api_client):
        url = f'/api/v1/verify/clones/alerts/{self.alert.id}/resolve/'
        response = api_client.post(url, {'status': 'CONFIRMED'}, format='json')
        assert response.status_code == 401

    def test_confirmed_clone_flagged_on_next_verify(self, auth_client_regulator, api_client):
        """After CONFIRMED, next public scan of the same code should return SUSPECTED_CLONE."""
        url = f'/api/v1/verify/clones/alerts/{self.alert.id}/resolve/'
        auth_client_regulator.post(url, {'status': 'CONFIRMED'}, format='json')

        # Public scan
        resp = api_client.post(
            '/api/v1/verify/',
            {'code': self.unit_code.secure_code, 'channel': 'WEB_MANUAL'},
            format='json'
        )
        assert resp.status_code == 200
        assert resp.json()['result_status'] == 'SUSPECTED_CLONE'
