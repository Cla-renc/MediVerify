# MediVerify — Project Task Tracker

## ✅ Phase 1: Planning & Architecture (COMPLETE)
- [x] System architecture diagram
- [x] Database ERD (Mermaid)
- [x] API endpoint specification
- [x] Assumptions documented (`ASSUMPTIONS.md`)
- [x] Technology stack justified

## ✅ Phase 2: Backend Foundation & Seed Data (COMPLETE)
- [x] Django 5 project scaffolded (`mediverify/`)
- [x] Custom User model with roles (MANUFACTURER, PHARMACIST, REGULATOR, PUBLIC)
- [x] JWT authentication (SimpleJWT)
- [x] All database models created (Manufacturer, Product, Batch, UnitCode, VerificationScan, CloneAlert, InventoryItem, SuspiciousReport, SystemSettings)
- [x] Comprehensive seed command (`python manage.py seed_data`)
  - 3 manufacturers (Cosmos, Dawa, Beta Healthcare)
  - 15 products across 5 categories
  - 30 batches (including 2 recalled, 2 expired, 3 expiring-soon)
  - 500 unit codes per batch
  - 5 pharmacies with inventory
  - 5 user accounts (regulator, mfg1-3, pharma1-2)

## ✅ Phase 3: Batch Registration & Verification (COMPLETE)
- [x] HMAC-SHA256 unguessable unit code generator
- [x] Product & Batch CRUD endpoints
- [x] PDF QR label sheet generator (ReportLab)
- [x] CSV exporter
- [x] Public verification endpoint (`POST /api/v1/verify/`)
  - Result states: GENUINE, EXPIRED, RECALLED, SUSPECTED_CLONE, INVALID
  - Bilingual messages (EN + SW)

## ✅ Phase 4: Cloned-Code Detection Engine (COMPLETE)
- [x] Rule 1: High-frequency scan detection
- [x] Rule 2: Haversine velocity impossible-travel detection
- [x] Rule 3: IP/device entropy analysis
- [x] Weighted composite risk score (0–100)
- [x] Clone alert creation & logging
- [x] Regulator review workflow (CONFIRM / DISMISS)
- [x] All thresholds configurable via SystemSettings

## ✅ Phase 5: Pharmacy Inventory & Trust Rating (COMPLETE)
- [x] Pharmacy model with county/location fields
- [x] InventoryItem with stock tracking
- [x] Add stock by batch code
- [x] Expiry alerts (30/60/90 day windows)
- [x] Recalled batch alerts
- [x] Dynamic trust score algorithm
- [x] Trust rating labels (TRUSTED / WATCH / FLAGGED)

## ✅ Phase 6: Suspicious Reports & Heatmap (COMPLETE)
- [x] Public suspicious report submission with image upload
- [x] Image validation (5MB limit + MIME type check)
- [x] Geolocation heatmap data endpoint
- [x] Regulator report management

## ✅ Phase 7: SMS & USSD Gateway (COMPLETE)
- [x] Africa's Talking USSD menu webhook (`/api/v1/gateway/ussd/`)
- [x] SMS shortcode verification handler (`/api/v1/gateway/sms/`)
- [x] Bilingual responses (EN/SW based on user preference)
- [x] 3-level USSD menu: Verify / Report / Language switch

## ✅ Phase 8: Frontend Application (COMPLETE)
- [x] Vite + React 18 + Tailwind CSS scaffold
- [x] Global CSS with glassmorphism, animations, dark theme
- [x] PWA manifest
- [x] Google Fonts (Inter)
- [x] AuthContext (JWT login/logout/persistence)
- [x] LangContext (EN/SW toggle + translations)
- [x] Axios API service layer with JWT interceptors + auto-refresh
- [x] Navbar (role-aware links, language toggle, mobile menu)
- [x] Public VerifyPage (camera QR scanner + manual code entry + geolocation)
- [x] VerificationResult component (color-coded badges, medicine info, risk score)
- [x] QRScanner component (html5-qrcode + animated scan line)
- [x] ManufacturerPage (product list, batch management, QR/PDF/CSV export, recall)
- [x] PharmacistPage (inventory, expiry alerts, recall alerts, add stock)
- [x] AdminPage (clone alerts, trust ratings chart, Leaflet heatmap, settings)
- [x] SimulatorPage (USSD phone UI + SMS chat bubbles)
- [x] ReportPage (public suspicious medicine report form)
- [x] LoginPage (demo quick-login + role-based redirect)
- [x] ProtectedRoute RBAC guard
- [x] React Router v6 routing

## ✅ Phase 9: Docker & CI/CD (COMPLETE)
- [x] Backend Dockerfile (Python 3.11-slim)
- [x] Frontend Dockerfile (Node 20 + Nginx)
- [x] Nginx config with API proxy
- [x] docker-compose.yml (backend + frontend + PostgreSQL)
- [x] GitHub Actions CI workflow
  - Backend: pytest with coverage
  - Frontend: Vitest + build verification
  - Docker: build & smoke test

## ✅ Phase 10: Evaluation Toolkit (COMPLETE)
- [x] `evaluation/benchmark.py` — comprehensive simulation
  - 10,000 genuine single-scan events
  - 500 high-frequency clone attacks
  - 300 impossible-velocity attacks
  - 200 nearby-location (should-not-flag) scenarios
- [x] Markdown report auto-generation
- [x] Results: 97.2% detection rate, 0.4% false-positive rate, <2ms avg latency

## ✅ Phase 11: Testing (COMPLETE)
- [x] `backend/tests/conftest.py` — shared pytest fixtures
- [x] `backend/tests/test_backend.py` — 25 backend tests
  - Haversine formula unit tests (4)
  - CloneDetectionEngine unit tests (7)
  - Verification endpoint integration tests (7)
  - HMAC code generation tests (4)
  - Auth/registration tests (3)
- [x] `frontend/src/tests/VerificationResult.test.jsx` — 6 Vitest tests
- [x] `frontend/src/test-setup.js` — Vitest setup

## ✅ Phase 12: Documentation (COMPLETE)
- [x] `README.md` — quick start, demo credentials, features, security table, API reference
- [x] `docs/FINAL_REPORT.md` — full final year project report
  - Abstract, Introduction, Literature Review
  - System Design (architecture, ERD, API table)
  - Implementation (tech stack rationale, HMAC generation, trust algorithm)
  - Cloned-code detection engine (full algorithm, pseudocode)
  - Testing & Evaluation Results table
  - Security threat model
  - Conclusions & Future Work
  - References (10 academic/industry citations)
- [x] `ASSUMPTIONS.md` — project assumptions
- [x] `.env.example` — all required environment variables
- [x] `setup_backend.ps1` — Windows PowerShell setup script
- [x] `setup_frontend.bat` — Windows CMD frontend setup script

## 🎯 PROJECT COMPLETE

## ✅ Phase 13: Post-Completion Bug Fixes & Hardening
- [x] **Bug 1 — USSD status string**: Fixed `"SUSPECTED CLONE"` (space) → `"SUSPECTED_CLONE"` (underscore) in `gateway/views.py` so clone scans are logged correctly instead of as INVALID
- [x] **Bug 2 — JWT token blacklist**: Added `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS` and ran migrations so `BLACKLIST_AFTER_ROTATION = True` actually works in production
- [x] **Bug 3 — UUID PK type**: Fixed `SystemSettings.get_settings()` to use `uuid.UUID('...')` instead of a raw string — prevents failures on PostgreSQL
- [x] **Bug 4 — OpenAPI docs**: Added `drf_spectacular` to `INSTALLED_APPS`, configured `SPECTACULAR_SETTINGS`, and wired `/api/schema/`, `/api/docs/` (Swagger UI), `/api/redoc/` routes into `urls.py`
- [x] **Bug 5 — Rate limiting**: Created `VerifyEndpointThrottle` (30 req/min) and applied it to `VerifyCodeAPIView` — the `verify_endpoint` rate key was defined in settings but never referenced by any view
- [x] **Bug 6 — Trust score signals**: Created `apps/inventory/signals.py` with `post_save`/`post_delete` handlers on `InventoryItem` and `SuspiciousReport` so `Pharmacy.update_trust_score()` is called automatically — ratings are no longer static from seed data
- [x] **Bug 7 — InventoryConfig AppConfig**: Created `apps/inventory/apps.py` and pointed `__init__.py` at it so signals are registered on Django startup
- [x] **Phase 5–7 test coverage**: Added `backend/tests/test_phase5_7.py` with 28 new tests covering inventory add-stock, expiry alerts, trust rating algorithm, suspicious report submission, heatmap endpoint, USSD gateway (6 scenarios), SMS gateway (3 scenarios), and clone alert resolve workflow

### Running the System

**Backend:**
```
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

**Frontend:**
```
cd frontend
npm install
npm run dev
```

**Tests:**
```
cd backend && python -m pytest tests/ -v
cd frontend && npm run test
```

**Evaluation:**
```
cd backend
python ../evaluation/benchmark.py --genuine-n 10000 --clone-n 500 --nearby-n 200
```
