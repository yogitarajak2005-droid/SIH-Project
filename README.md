# VerifyAI: AI-Based Fake Identity & Document Screening System

> **Smart India Hackathon (SIH) Prototype**  
> Problem Statement: *AI-Based Fake Identity & Document Screening System*  
> **Important Disclaimer:** *This system provides risk-based screening assistance only. A screening flag does not establish that an identity document is fraudulent. Authorized human verification is required.*

---

## 1. Project Overview

**VerifyAI** is an AI-assisted cybersecurity prototype designed to help authorized personnel screen uploaded identity credentials for inconsistencies, low-quality scans, character anomalies, and potential data mismatches.

Rather than making definitive, opaque claims (e.g. marking a document as "FAKE"), **VerifyAI** implements an **explainable decision-support model**. It processes the document through Computer Vision (OpenCV) and Optical Character Recognition (OCR), extracts key fields (Name, Date of Birth, Document ID), performs consistency checks, and produces an auditable **Risk Score (0–100)** categorized into:
- 🟢 **LOW REVIEW** (0–30): High image quality, consistent extracted fields, no anomalies detected.
- 🟡 **MEDIUM REVIEW** (31–65): Minor blur, low contrast, or ambiguous field extraction requiring manual verification.
- 🔴 **HIGH REVIEW** (66–100): Significant image degradation, missing required fields, or chronological anomalies (e.g., future birth dates, corrupted identifiers).

---

## 2. Key Features

- **Cybersecurity & AI Dashboard Aesthetic:** Dark navy/black theme, glowing cyan accents, glassmorphic cards, and radar scanning animations.
- **OpenCV Image Quality Engine:** Measures focus sharpness via Laplacian variance (blur detection), calculates contrast standard deviation, and validates resolution and aspect ratios.
- **Dual-Engine OCR:** Direct integration with `Tesseract OCR` (via `pytesseract`), backed by an intelligent heuristic fallback parser for zero-downtime demonstration environments.
- **Heuristic & Regex Field Parsing:** Automatically identifies Full Name, Date of Birth, Document ID, Gender, Issue Date, and Expiry Date.
- **Explainable Review Flags:** Clear, severity-labeled flags detailing *why* an image was flagged (e.g., *"Document image quality is low. Laplacian focus variance is 1.5 (threshold is 100.0)"*).
- **1-Click Synthetic Demo Mode:** Built-in fictional demo documents (**Clean**, **Blurry**, and **Corrupted**) allowing instant demonstration without requiring physical document files.
- **Privacy-Aware Architecture:** Uploaded document images are temporarily analyzed in memory/scratch and **immediately deleted** from disk upon completion. Only non-sensitive audit metrics are retained for analytics.
- **Admin Analytics Dashboard:** Dynamic Chart.js distribution charts, KPI counters (128 screened, 72 low, 39 medium, 17 high), and an interactive audit log.

---

## 3. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.12, Django 5+, Django REST Framework | RESTful routing, multipart file validation, CSRF security |
| **Computer Vision** | OpenCV (`opencv-python`), Pillow | Laplacian blur detection, contrast and resolution analysis |
| **OCR Engine** | Tesseract OCR & `pytesseract` | Text extraction, bounding boxes, character confidence |
| **Frontend** | HTML5, Tailwind CSS, Vanilla JavaScript (ES6+) | Responsive dashboard, drag & drop upload, step animation |
| **Visualizations** | Chart.js, FontAwesome 6 | Risk distribution doughnut charts, cybersecurity iconography |

---

## 4. Project Structure

```
sih ps/
├── manage.py                     # Django management script
├── requirements.txt              # Locked project dependencies
├── generate_samples.py           # Synthetic demo document generator
├── screening/                    # Project configuration
│   ├── __init__.py
│   ├── settings.py               # Django settings (DRF, Static, Media, Security)
│   ├── urls.py                   # Master routing
│   └── wsgi.py
│
├── document_api/                 # Core screening application
│   ├── __init__.py
│   ├── admin.py                  # Admin dashboard registration
│   ├── models.py                 # Non-sensitive ScreeningLog audit model
│   ├── serializers.py            # Upload & validation serializers
│   ├── services.py               # Core CV, OCR, extraction & scoring engine
│   ├── tests.py                  # Automated unit test suite (8 tests)
│   ├── urls.py                   # API and web routes
│   └── views.py                  # API endpoints and template controllers
│
├── templates/
│   └── index.html                # Unified single-page responsive application
├── static/
│   ├── css/
│   │   └── custom.css            # Glassmorphism, radar scan, cyber theme
│   ├── js/
│   │   └── app.js                # Upload handling, animations, API fetch, charts
│   └── samples/                  # Pre-generated synthetic demo identity cards
│       ├── sample_valid.png
│       ├── sample_blurry.png
│       └── sample_inconsistent.png
└── media/
    └── temp/                     # Scratch folder for active processing (auto-cleaned)
```

---

## 5. Installation & Setup

### Prerequisites
- **Python 3.10+** (Tested on Python 3.12)
- **pip** package manager

### Step 1: Clone or Navigate to the Project Directory
```bash
cd "c:\Users\Lenovo\Documents\sih ps"
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

*(Installed packages: `Django`, `djangorestframework`, `Pillow`, `opencv-python`, `pytesseract`, `numpy`)*

### Step 3: Run Database Migrations
```bash
python manage.py migrate
```

### Step 4: Generate Synthetic Demo Documents
```bash
python generate_samples.py
```

---

## 6. Tesseract OCR Setup (Optional)

The prototype includes an **Intelligent Synthetic OCR Fallback Engine** that works immediately without installing external binaries. If you would like to run native Tesseract OCR:

### On Windows:
1. Download the Windows installer from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. Run the installer (default directory: `C:\Program Files\Tesseract-OCR`).
3. Verify that `C:\Program Files\Tesseract-OCR` is added to your system `PATH`, or the service will automatically detect it in standard locations.

### On Ubuntu/Debian Linux:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

---

## 7. Running the Server

Start the Django development server:
```bash
python manage.py runserver 127.0.0.1:8000
```

Open your web browser and navigate to:
```
http://127.0.0.1:8000/
```

---

## 8. API Endpoint Documentation

### `POST /api/screen/`
Primary screening endpoint. Accepts a multipart file upload.

- **Request:**
  - Method: `POST`
  - Content-Type: `multipart/form-data`
  - Body: `document` (Image file: `.jpg`, `.jpeg`, `.png`, max 5 MB)

- **Example Response:**
  ```json
  {
    "success": true,
    "document_filename": "sample_blurry.png",
    "extracted_data": {
      "name": "????? DOE",
      "dob": "14/08/1992",
      "document_id": "DEMO-9824-XYZ",
      "gender": "MALE",
      "issue_date": "10/01/2020",
      "expiry_date": "09/01/2030"
    },
    "screening": {
      "risk_score": 40,
      "risk_level": "MEDIUM REVIEW",
      "risk_color": "amber",
      "summary": "Document exhibits moderate image quality degradation or minor field extraction ambiguities requiring manual check.",
      "flags": [
        "Document image quality is low. Laplacian focus variance is 1.5 (threshold is 100.0).",
        "Could not reliably extract mandatory field(s): NAME. Manual cross-examination required."
      ],
      "detailed_flags": [
        {
          "icon": "exclamation-triangle",
          "severity": "medium",
          "title": "Document image quality is low",
          "explanation": "Document image quality is low. Laplacian focus variance is 1.5 (threshold is 100.0)."
        }
      ]
    },
    "breakdown": {
      "ocr_analysis": {
        "status": "Text extracted successfully",
        "engine": "VerifyAI Intelligent Synthetic OCR Engine",
        "confidence_score": 64.0,
        "character_count": 240,
        "word_count": 28
      },
      "document_quality": {
        "blur_score": 1.5,
        "blur_threshold": 100.0,
        "is_blurry": true,
        "contrast_score": 38.2,
        "brightness_score": 142.1,
        "resolution": "800 x 500 px",
        "aspect_ratio": 1.6,
        "aspect_ratio_valid": true
      },
      "consistency_checks": {
        "required_fields_present": false,
        "missing_fields": ["name"],
        "date_format_valid": true,
        "date_reasonableness": true,
        "suspicious_characters": false,
        "unusual_patterns": false,
        "mrz_consistency": true
      },
      "risk_assessment": {
        "risk_score": 40,
        "risk_level": "MEDIUM REVIEW",
        "disclaimer": "Important: This system provides risk-based screening assistance only. A screening flag does not establish that an identity document is fraudulent. Authorized human verification is required."
      }
    },
    "ocr_text": "...",
    "processing_time_ms": 118.4
  }
  ```

### `GET /api/stats/`
Retrieves live & baseline screening audit counts, risk distribution metrics, and recent screening logs for the analytics dashboard.

### `GET /api/demo-samples/`
Returns metadata and URLs for the synthetic test documents.

---

## 9. How to Test the Prototype

### Method 1: Using the 1-Click Demo Selector (Recommended for Presentations)
1. Open `http://127.0.0.1:8000/`.
2. Scroll to the **"Screen Your Document"** section.
3. Click any of the three quick sample buttons:
   - **1. Clean Sample (Low):** Generates a crisp synthetic document (Score: ~15, `LOW REVIEW`).
   - **2. Blurry Sample (Med):** Demonstrates blur detection and degraded confidence (Score: ~40, `MEDIUM REVIEW`).
   - **3. Corrupted Sample (High):** Demonstrates chronological anomaly (future DOB) and corrupted ID (Score: ~90, `HIGH REVIEW`).
4. Click **"Analyze Document"**.
5. Observe the 5-step animated pipeline followed by the dynamic circular risk gauge, extracted field tables, and explainable review flags.

### Method 2: Custom Document Upload
1. Drag and drop any `.png`, `.jpg`, or `.jpeg` file into the upload zone (or click to browse).
2. Click **"Analyze Document"**.
3. Review the generated breakdown.

### Running Automated Test Suite
Execute the full Django test suite:
```bash
python manage.py test document_api
```
All 8 automated tests verify API responses, file validation, security constraints, and scoring tiers.

---

## 10. System Limitations & Ethical Considerations

- **Prototype Scope:** Designed strictly as an assistive decision-support tool. It does not replace authorized human verification officers or statutory registry checks.
- **Synthetic Data Compliance:** Tested exclusively on synthetic/fictional identities to protect personal privacy and ensure zero exposure of personally identifiable information (PII).
- **Physical Security Features:** Optical screening cannot verify physical security inks, embedded NFC chips, or tactile elements without specialized physical scanning hardware.
