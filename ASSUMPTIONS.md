# MediVerify System Assumptions & Design Decisions

This document outlines key technical, domain, and operational assumptions made during the design and implementation of **MediVerify**.

---

## 1. Domain & Operational Assumptions

1. **Kenyan Pharmaceutical Context**:
   - Regulatory authority modelled after the **Pharmacy and Poisons Board (PPB)** of Kenya.
   - Initial county list focused on major regions: Nairobi, Mombasa, Kisumu, Nakuru, Uasin Gishu, Nyeri, Kiambu, Machakos.
   - Dual-language support covers **English** (official/medical) and **Swahili** (national/public).

2. **Code Generation & Cryptography**:
   - Each medicine unit is assigned an unguessable serial code formatted as `MV-[BATCH_ID_PREFIX]-[HMAC_TOKEN]`.
   - HMAC-SHA256 signature is derived from a server-side `SECRET_KEY` and unit serial sequence.
   - Offline verification without server check is explicitly disallowed to prevent token cloning/replication.

3. **Geolocation & Channel Capabilities**:
   - Web browser scans request HTML5 Geolocation API coordinates (`latitude`, `longitude`). If user denies geolocation, scan is logged with `None` coordinates and IP geolocation fallback.
   - SMS and USSD verification channels do not provide exact GPS coordinates; physical location is inferred from cell tower data (simulated) or regional code prefixes where applicable.

4. **Cloned-Code Detection Parameters**:
   - Max velocity threshold default is **800 km/h** (equivalent to commercial flight speed limit; higher velocity implies impossible physical movement).
   - Rolling window for IP entropy is **15 minutes** with a threshold of **3 distinct IPs**.
   - Default scan count threshold per individual unit token before flagging is **3 scans** (since individual consumer unit packs are expected to be verified 1-2 times).

5. **SMS & USSD Gateway Integration**:
   - Sandbox environment provided by **Africa's Talking**.
   - Built-in interactive frontend simulator allows offline/local demonstration of USSD menus (`*384#`) and SMS shortcodes without requiring live telecom subscriptions or active internet sandbox credentials.

6. **Database & Infrastructure**:
   - Default local database is **SQLite** (`db.sqlite3`) for simple zero-dependency setup.
   - Dynamic switch to **PostgreSQL** via `DATABASE_URL` environment variable for production readiness.

## 7. AI Feature Assumptions

1. **Clone model input**: The current scan record is named `VerificationScan`; it is used instead of the requested generic `ScanEvent` name. Device identity is approximated by the stored user-agent string because the existing schema has no stable device identifier. Locations are grouped by rounded latitude/longitude (0.1 degree) and pharmacy location when GPS is absent.
2. **Hybrid model**: Isolation Forest is an unsupervised anomaly detector, not a counterfeit classifier. The application maps its decision score into 0–100 using the trained model's lower-tail threshold, then combines it with the unchanged rule score using configurable weights. Rules remain active when no model file exists.
3. **Synthetic data**: Generated scan scenarios are labeled for evaluation only and are not treated as verified real-world labels. They use reproducible patterns for repeated, distant, nearby, and slow low-rate clones.
4. **OCR**: Pack images are kept in memory, re-encoded to remove image metadata, and are not stored by the OCR API. `EXP MM/YYYY` is normalized to the final calendar day of that month. OCR output is only a suggestion; the pharmacist must edit or confirm it before using the batch number to add inventory.
5. **Medicine information**: Seeded bilingual medicine entries are explicitly marked `SAMPLE - must be reviewed by a pharmacist`, have no reviewer or review date, and must not be presented as approved clinical guidance. The chatbot refuses unsupported requests and is not a diagnosis or treatment service.
6. **LLM and privacy**: With a configured provider, only the user's question and selected medicine record context are sent to the configured endpoint. Database question logs store a keyed fingerprint, language, and category rather than raw text. Conversation messages are kept only in the Django session.
7. **API paths**: The requested `/api/ocr/pack/` and `/api/chat/` paths are exposed, with equivalent `/api/v1/` paths so the existing frontend API prefix remains unchanged.
8. **Frontend packages**: No additional JavaScript package is required: camera capture uses the browser file input and existing Axios handles uploads and chat requests.
