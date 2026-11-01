# MediVerify AI Features: A Student-Friendly Guide

This note explains the three AI features in plain language. They extend the existing Django, React, and medicine-registry system; they do not replace the verification or inventory modules.

## 1. Clone detection with Isolation Forest

### What it does

The existing clone detector uses explicit rules: too many scans, impossible travel between scan locations, and too many different IP addresses in a short time. The optional Isolation Forest looks for unusual combinations of scan activity. MediVerify keeps the original rules and combines their score with the model score. The initial weights are 60% rules and 40% ML, and an administrator can change the weights and alert thresholds.

### Data it uses

The model builds one feature row per unit code from `VerificationScan` records:

- total scans and scans in the last hour, 24 hours, and 7 days;
- distinct user-agent device labels, IP addresses, and approximate locations;
- maximum speed implied by consecutive GPS points using Haversine distance;
- time since the code's first scan;
- proportions of web, SMS, and USSD scans; and
- the code's scan count relative to its batch's average.

The existing schema does not record a dedicated device ID. User-agent is therefore a rough device signal, not a dependable identity. Location grouping is approximate.

### How it works

Isolation Forest isolates unusual rows with fewer splits than typical rows. The model learns patterns from scan history without needing a manually labeled clone for every example. Its decision value is normalized to 0–100 and combined with the rule score. If the artifact is missing or ML is switched off, verification uses the existing rules only. The model artifact is stored under `backend/models/`; the database stores its version, training date, sample count, and feature baseline.

The model explanation lists features that differ most from the training average. It helps a regulator understand an alert; it is not a causal explanation or proof of cloning.

### Limitations

An unusual scan pattern is a reason to investigate, not proof of fraud. Model quality depends on scan history and representative training data. Synthetic scenarios help demonstrate the workflow but do not validate real-world accuracy. Use the evaluation report and human regulator review before relying on model scores.

## 2. OCR for batch and dates

### What it does

A pharmacist can take a photo or upload a pack image on **Add Stock**. OpenCV converts the image to grayscale, reduces noise, increases its size, applies adaptive thresholding, and corrects small skew. Tesseract reads the printed characters. A parser searches for common batch, expiry, and manufacturing labels and normalizes dates to `YYYY-MM-DD`.

The upload is limited to 5 MB, restricted to supported image formats, decoded, and re-encoded to strip metadata. The endpoint processes the image in memory and does not save it. The database is checked for the extracted batch number. A match is shown to the pharmacist.

### Confirmation and limitations

OCR can confuse similar printed characters such as `O`/`0`, `I`/`1`, and `S`/`5`. Foil, curved packaging, glare, small print, and blurry photographs can lower accuracy. The values stay editable. **No OCR result is used to add inventory until the pharmacist confirms it**, and an unregistered batch is shown as not found.

Tesseract is included in Docker. For local setup:

- Windows: install a Tesseract OCR distribution and add its executable to `PATH`; alternatively set `TESSERACT_CMD` in `.env`.
- Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`.
- Python image libraries are installed with `pip install -r requirements.txt`.

The evaluation images are synthetic label examples and are not a substitute for testing real packaging.

## 3. English/Swahili medicine information chat

### What it does

After a genuine verification, a customer can ask about a medicine. MediVerify retrieves the matching `MedicineInfo` entry and sends only that record as context to the configured LLM. The system prompt says that the context is the only allowed information source. The application also checks the generated answer against the context; an unsupported response is replaced by a refusal.

Without an LLM key, the feature works offline: it returns the matching section directly from the record. The language can be selected in the chat panel or detected from the question. SMS supports `INFO <code>` and `INFO <code> SW`.

### Safety and data

The service refuses questions outside the available record, does not diagnose, does not give personalized doses, and does not recommend starting, stopping, or changing treatment. Emergency terms trigger only an urgent seek-medical-care message. A short disclaimer is appended in English or Swahili.

The ten common seeded records (paracetamol, ibuprofen, amoxicillin, ORS, artemether-lumefantrine, metformin, amlodipine, cetirizine, omeprazole, and salbutamol), plus a Beta-Flagyl/Metronidazole record for the demo product, are **sample content**. Admin displays their sample marker, their source says `SAMPLE - must be reviewed by a pharmacist`, and they have no review date. A pharmacist must check every entry before it can be treated as reliable medicine information.

When a provider is configured, the question and matching medicine context leave the local application and are sent to that provider. Raw questions are not stored in the question log: it keeps a keyed fingerprint, language, and question category. Conversation history is kept in the user's Django session only. If that privacy boundary is unsuitable for a deployment, do not configure an external provider.

## Running and evaluating the features

From `backend/`, run:

```powershell
python manage.py migrate
python manage.py seed_data
python manage.py generate_synthetic_scans --seed 42
python manage.py train_clone_model --seed 42
python manage.py evaluate_clone_detection
python manage.py evaluate_ocr
python manage.py evaluate_chatbot
```

The clone report writes a CSV with overall and per-attack metrics/confusion counts and a PNG chart under `evaluation/`. OCR reports exact-match batch and expiry accuracy and average processing time; its image folder may be supplied with `--images`. Chat evaluation uses 60 supported question/answer pairs in both languages and refusal cases, and prints groundedness, refusal correctness, language match, and latency. These are demonstration evaluations, not certification results.

The SMS/USSD simulator is local-only. Live Africa's Talking operation requires an account, approved sender/shortcode and USSD service code, private API credentials, and a public HTTPS backend callback. Configure the `AFRICASTALKING_*` values in the root `.env` and register the callback URLs as described in the README's live SMS/USSD setup. Do not enable live delivery until those provider resources and secured callback URLs are ready.
