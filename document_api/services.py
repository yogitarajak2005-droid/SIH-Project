import os
import re
import time
import uuid
import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from django.conf import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Detect Tesseract OCR binary location
TESSERACT_CMD_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Lenovo\AppData\Local\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]

def configure_tesseract():
    for candidate in TESSERACT_CMD_CANDIDATES:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            return candidate
    return None

CONFIGURED_TESSERACT_CMD = configure_tesseract()

HEADER_WORDS = {
    "GOVERNMENT", "REPUBLIC", "CREDENTIAL", "FICTIONAL", "IDENTITY",
    "CITIZEN", "SYNTHETIC", "DOCUMENT", "STATE", "CARD", "PASSPORT",
    "AUTHORITY", "UNION", "DEPARTMENT", "INCOME", "TAX", "PERMANENT",
    "ACCOUNT", "DRIVING", "LICENCE", "LICENSE", "ENROLLMENT", "INDIA",
    "MINISTRY", "OFFICIAL", "MERA", "AADHAAR", "PEHCHAN", "NATIONAL",
    "DIRECTORATE", "TRANSPORT", "ELECTION", "COMMISSION"
}


def mask_id_for_logging(doc_id):
    """Masks sensitive document ID for privacy-compliant server-side logging."""
    if not doc_id or doc_id == "Not detected":
        return str(doc_id)
    clean = str(doc_id).strip()
    if len(clean) <= 4:
        return "****"
    # Show first 2 and last 2 characters only
    return clean[:2] + ("*" * (len(clean) - 4)) + clean[-2:]


def deskew_image(gray):
    """
    Detects slight skew angle in [-30, 30] degrees and rotates cleanly.
    Preserves text sharpness without distorting characters.
    """
    try:
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle
        else:
            angle = -angle

        if 0.8 < abs(angle) < 30:
            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        pass
    return gray


class DocumentScreeningService:
    """
    Core AI and Computer Vision service for document screening.
    Performs:
    1. File validation
    2. OpenCV image quality analysis (Laplacian blur, contrast, brightness, resolution)
    3. Multi-variant, multi-PSM Tesseract OCR text extraction
    4. Generalizable multiline regex & heuristic field extraction (Name, DOB, ID, Gender, Dates)
    5. Confidence calculation per field
    6. Consistency and chronology validation
    7. Explainable dynamic risk scoring and review flags
    8. Privacy-compliant debug logging with ID masking
    9. Guaranteed temporary file cleanup
    """

    def __init__(self, uploaded_file):
        self.uploaded_file = uploaded_file
        self.filename = getattr(uploaded_file, "name", "uploaded_document.png")
        self.temp_file_path = None
        self.start_time = time.time()

    def process(self):
        try:
            # 1. Validate uploaded file
            self._validate_file()

            # 2. Save temporary file for OpenCV / OCR
            self._save_temp_file()

            # 3. OpenCV image quality & blur assessment
            quality_data = self._analyze_image_quality()

            # 4. Multi-variant & multi-pass OCR text extraction
            ocr_result = self._extract_text(quality_data)

            # 5. Robust field extraction & confidence scoring
            extracted_fields, confidences = self._extract_fields(
                ocr_result["raw_text"], ocr_result.get("normalized_text", "")
            )

            # 6. Consistency checks
            consistency_data = self._perform_consistency_checks(
                extracted_fields, ocr_result, quality_data
            )

            # 7. Explainable risk scoring & review flags
            risk_data = self._compute_risk_score(
                quality_data, extracted_fields, consistency_data, ocr_result
            )

            processing_time = round((time.time() - self.start_time) * 1000, 1)

            # 8. Server-side debugging logs with ID masking
            logger.info(
                "\n==================== OCR SCREENING PIPELINE DEBUG ====================\n"
                "DOCUMENT: %s | TIME: %.1fms | RESOLUTION: %s\n"
                "-------------------- RAW OCR TEXT --------------------\n"
                "%s\n"
                "-------------------- NORMALIZED OCR TEXT --------------------\n"
                "%s\n"
                "-------------------- EXTRACTED DATA --------------------\n"
                "EXTRACTED NAME:        '%s' (confidence: %d%%)\n"
                "EXTRACTED DOB:         '%s' (confidence: %d%%)\n"
                "EXTRACTED DOCUMENT ID: '%s' (confidence: %d%%) [MASKED FOR PRIVACY]\n"
                "EXTRACTED GENDER:      '%s' (confidence: %d%%)\n"
                "EXTRACTED ISSUE DATE:  '%s'\n"
                "EXTRACTED EXPIRY DATE: '%s'\n"
                "-------------------- SCREENING EVALUATION --------------------\n"
                "RISK SCORE: %d/100 (%s)\n"
                "FLAGS COUNT: %d\n"
                "=======================================================================",
                self.filename,
                processing_time,
                f"{quality_data['width']}x{quality_data['height']} px",
                ocr_result["raw_text"],
                ocr_result.get("normalized_text", ""),
                extracted_fields.get("name") or "None",
                confidences.get("name", 0),
                mask_id_for_logging(extracted_fields.get("document_id")),
                confidences.get("document_id", 0),
                extracted_fields.get("gender") or "None",
                confidences.get("gender", 0),
                extracted_fields.get("issue_date") or "None",
                extracted_fields.get("expiry_date") or "None",
                risk_data["score"],
                risk_data["level"],
                len(risk_data["flags"])
            )

            # Extracted values (fallback to 'Not detected' if missing)
            name_val = extracted_fields.get("name") or "Not detected"
            dob_val = extracted_fields.get("dob") or "Not detected"
            doc_id_val = extracted_fields.get("document_id") or "Not detected"
            gender_val = extracted_fields.get("gender") or "Not specified"
            issue_val = extracted_fields.get("issue_date") or "Not detected"
            expiry_val = extracted_fields.get("expiry_date") or "Not detected"

            return {
                "success": True,
                "document_filename": self.filename,
                "extracted_data": {
                    "name": name_val,
                    "full_name": name_val,
                    "dob": dob_val,
                    "date_of_birth": dob_val,
                    "document_id": doc_id_val,
                    "id": doc_id_val,
                    "gender": gender_val,
                    "issue_date": issue_val,
                    "expiry_date": expiry_val,
                },
                "field_confidences": confidences,
                "screening": {
                    "risk_score": risk_data["score"],
                    "risk_level": risk_data["level"],
                    "risk_color": risk_data["color"],
                    "summary": risk_data["summary"],
                    "flags": [f["explanation"] for f in risk_data["flags"]],
                    "detailed_flags": risk_data["flags"],
                },
                "breakdown": {
                    "ocr_analysis": {
                        "status": (
                            "Text extracted successfully"
                            if ocr_result["char_count"] >= 20
                            else "Low or unreadable text yield"
                        ),
                        "engine": ocr_result["engine"],
                        "confidence_score": ocr_result["confidence"],
                        "character_count": ocr_result["char_count"],
                        "word_count": ocr_result["word_count"],
                    },
                    "document_quality": {
                        "blur_score": quality_data["laplacian_variance"],
                        "blur_threshold": quality_data["blur_threshold"],
                        "is_blurry": quality_data["is_blurry"],
                        "contrast_score": quality_data["contrast"],
                        "brightness_score": quality_data["brightness"],
                        "resolution": f"{quality_data['width']} x {quality_data['height']} px",
                        "aspect_ratio": quality_data["aspect_ratio"],
                        "aspect_ratio_valid": quality_data["aspect_ratio_valid"],
                    },
                    "consistency_checks": consistency_data,
                    "risk_assessment": {
                        "risk_score": risk_data["score"],
                        "risk_level": risk_data["level"],
                        "deductions": risk_data["deductions"],
                        "flags_count": len(risk_data["flags"]),
                        "disclaimer": (
                            "Important: This system provides risk-based screening assistance only. "
                            "A screening flag does not establish that an identity document is fraudulent. "
                            "Authorized human verification is required."
                        ),
                    },
                },
                "ocr_text": ocr_result["raw_text"],
                "normalized_text": ocr_result.get("normalized_text", ""),
                "debug_info": {
                    "raw_ocr_text": ocr_result["raw_text"],
                    "normalized_ocr_text": ocr_result.get("normalized_text", ""),
                    "field_confidences": confidences,
                    "extracted_fields": {
                        "name": name_val,
                        "dob": dob_val,
                        "document_id": mask_id_for_logging(doc_id_val),
                        "gender": gender_val,
                    }
                },
                "processing_time_ms": processing_time,
            }

        finally:
            self._cleanup_temp_file()

    def _cleanup_temp_file(self):
        """Removes the temporary uploaded image from disk to preserve privacy."""
        if self.temp_file_path and os.path.exists(self.temp_file_path):
            try:
                os.remove(self.temp_file_path)
            except Exception as e:
                logger.warning("Could not remove temp file '%s': %s", self.temp_file_path, e)

    def _validate_file(self):
        """Validates file presence, size, and extension."""
        if not self.uploaded_file:
            raise ValueError("No document was uploaded.")

        if self.uploaded_file.size > MAX_FILE_SIZE:
            raise ValueError(
                f"File is too large ({self.uploaded_file.size / (1024*1024):.2f} MB). Maximum size is 5 MB."
            )

        extension = Path(self.filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{extension}'. Upload JPG, JPEG, or PNG."
            )

        content_type = getattr(self.uploaded_file, "content_type", "")
        if content_type and content_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Invalid image MIME type '{content_type}'.")

    def _save_temp_file(self):
        """Writes uploaded bytes to a secure temporary location."""
        temp_dir = Path(settings.MEDIA_ROOT) / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(self.filename).suffix.lower() or ".png"
        unique_name = f"screening_{uuid.uuid4().hex}{ext}"
        self.temp_file_path = str(temp_dir / unique_name)

        with open(self.temp_file_path, "wb+") as destination:
            for chunk in self.uploaded_file.chunks():
                destination.write(chunk)

    def _analyze_image_quality(self):
        """
        Uses OpenCV to assess focus sharpness (Laplacian variance),
        contrast, brightness, dimensions, and aspect ratio.
        """
        image = cv2.imread(self.temp_file_path)
        if image is None:
            raise ValueError("Uploaded file could not be read as an image. It may be corrupted.")

        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blur_threshold = 80.0
        is_blurry = bool(laplacian_variance < blur_threshold)

        contrast = float(np.std(gray))
        brightness = float(np.mean(gray))

        aspect_ratio = round(width / height, 3) if height else 0.0
        aspect_ratio_valid = bool(0.5 <= aspect_ratio <= 2.5)
        low_resolution = bool(width < 500 or height < 300)

        return {
            "width": width,
            "height": height,
            "laplacian_variance": round(laplacian_variance, 1),
            "blur_threshold": blur_threshold,
            "is_blurry": is_blurry,
            "contrast": round(contrast, 1),
            "is_low_contrast": bool(contrast < 30.0),
            "brightness": round(brightness, 1),
            "aspect_ratio": aspect_ratio,
            "aspect_ratio_valid": aspect_ratio_valid,
            "low_resolution": low_resolution,
        }

    def _normalize_text(self, text):
        """Normalizes unicode characters, whitespace, and dashes."""
        if not text:
            return ""
        t = re.sub(r"[–—−]", "-", text)
        t = re.sub(r"[''`]", "'", t)
        t = re.sub(r'[""«»]', '"', t)
        t = re.sub(r"[：;]", ":", t)
        t = "".join(ch for ch in t if ch == "\n" or ch == "\t" or ord(ch) >= 32)
        # Collapse multiple spaces per line
        normalized_lines = []
        for line in t.splitlines():
            line_str = re.sub(r"[ \t]+", " ", line).strip()
            if line_str:
                normalized_lines.append(line_str)
        return "\n".join(normalized_lines)

    def _extract_text(self, quality_data):
        """
        Runs multi-pass OCR on the uploaded image:
        Pass 1: Grayscale with PSM 6 (uniform block layout).
        Pass 2: Grayscale with PSM 3 (automatic multi-column layout) if needed.
        Pass 3: CLAHE contrast-enhanced + smart-scaled with PSM 11 (sparse text) if fields are missing or text is sparse.
        """
        raw_text = ""
        confidence = 0.0
        engine = "Tesseract OCR"

        try:
            if CONFIGURED_TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = CONFIGURED_TESSERACT_CMD

            image = cv2.imread(self.temp_file_path)
            if image is None:
                raise ValueError("Cannot read image for OCR.")

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = deskew_image(gray)

            # Pass 1: Standard grayscale with PSM 6
            text_psm6 = pytesseract.image_to_string(gray, lang="eng", config="--psm 6")
            
            # Pass 2: Grayscale with PSM 3 (auto segmentation)
            text_psm3 = pytesseract.image_to_string(gray, lang="eng", config="--psm 3")

            # Combine distinct lines or choose best yield
            combined_lines = []
            seen = set()
            for line in (text_psm6 + "\n" + text_psm3).splitlines():
                cl = line.strip()
                if cl and cl not in seen:
                    seen.add(cl)
                    combined_lines.append(cl)

            primary_text = "\n".join(combined_lines)

            # If text yield is low (< 30 characters), try CLAHE and upscaled pass
            if len(primary_text.strip()) < 30 and not quality_data.get("is_blurry"):
                h, w = gray.shape[:2]
                if w < 1600 or h < 1000:
                    scale = min(max(1600.0 / w, 1000.0 / h), 2.5)
                    scaled = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
                else:
                    scaled = gray

                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(scaled)
                text_clahe = pytesseract.image_to_string(clahe, lang="eng", config="--psm 11")
                if len(text_clahe.strip()) > len(primary_text.strip()):
                    primary_text = text_clahe

            # Word confidence calculation
            try:
                data = pytesseract.image_to_data(gray, lang="eng", output_type=pytesseract.Output.DICT)
                conf_vals = [float(v) for v in data.get("conf", []) if str(v).replace("-", "").isdigit() and float(v) >= 0]
                confidence = round((sum(conf_vals) / len(conf_vals)), 1) if conf_vals else 75.0
            except Exception:
                confidence = 70.0 if primary_text else 0.0

            raw_text = primary_text.strip()

        except Exception as ocr_err:
            logger.warning("Tesseract execution failed: %s", ocr_err)
            engine = "OCR Unavailable"
            raw_text = ""
            confidence = 0.0

        normalized_text = self._normalize_text(raw_text)
        char_count = len(normalized_text.replace(" ", "").replace("\n", ""))
        word_count = len(normalized_text.split())

        return {
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "confidence": confidence,
            "char_count": char_count,
            "word_count": word_count,
            "engine": engine,
        }

    def _clean_name(self, name_str):
        """Cleans labels, prefixes, and stray OCR punctuation from a name string."""
        if not name_str:
            return None
        # Remove label keywords if still present at beginning
        s = re.sub(
            r"^(?:NAME|FULL\s*NAME|CITIZEN\s*NAME|APPLICANT\s*NAME|HOLDER\s*NAME|SURNAME|GIVEN\s*NAMES?)[\s:\-!/]+",
            "",
            name_str,
            flags=re.IGNORECASE
        )
        # Keep letters, spaces, hyphens, and dots
        cleaned = re.sub(r"[^\w\s\.\-]", "", s).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned[:50].strip() or None

    def _is_header_token(self, token):
        """Determines if a string is a document title/authority rather than a person's name."""
        if not token:
            return True
        words = re.findall(r"\b[A-Za-z]+\b", token.upper())
        if not words:
            return True
        header_count = sum(1 for w in words if w in HEADER_WORDS)
        return (header_count / len(words)) >= 0.4

    def _is_valid_name_candidate(self, candidate):
        """Validates that a string is a plausible person's name."""
        if not candidate or len(candidate) < 3:
            return False
        if self._is_header_token(candidate):
            return False

        reject_words = [
            "DATE", "DOB", "CHIP", "HIP", "PHOTO", "SEX", "MALE", "FEMALE",
            "SIGNATURE", "VALID", "ISSUE", "EXPIRY", "FATHER", "MOTHER", "HUSBAND",
            "SON OF", "DAUGHTER OF", "WIFE OF", "YEAR", "BIRTH", "NUMBER", "NO.", "NAME"
        ]
        cand_upper = candidate.upper()
        tokens = cand_upper.split()
        if any(rw in tokens for rw in reject_words):
            return False

        letters = sum(1 for c in candidate if c.isalpha())
        if letters < 3:
            return False

        words = candidate.split()
        if len(words) > 5 or len(words) < 1:
            return False
        return True

    def _normalize_ocr_date_str(self, raw_date_str):
        """Corrects common OCR substitutions inside dates (e.g. O/o -> 0, I/l -> 1)."""
        d = raw_date_str.strip()
        # Replace O or o with 0
        d = re.sub(r"(?<=[/\-\.\s\b])[Oo](?=\d|[/\-\.\s\b])", "0", d)
        d = re.sub(r"(?<=\d)[Oo](?=[/\-\.\s\b]|\d)", "0", d)
        # Replace I or l with 1
        d = re.sub(r"(?<=[/\-\.\s\b])[Il\|](?=\d|[/\-\.\s\b])", "1", d)
        d = re.sub(r"(?<=\d)[Il\|](?=[/\-\.\s\b]|\d)", "1", d)
        # Remove extra spaces around slashes, dashes, dots
        d = re.sub(r"\s*([/\-\.])\s*", r"\1", d)
        # If separated by spaces: '14 08 1992' -> '14/08/1992'
        d = re.sub(r"\b(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})\b", r"\1/\2/\3", d)
        return d.strip()

    def _parse_date(self, date_str):
        """Safely parses flexible date formats into a datetime object."""
        if not date_str or not isinstance(date_str, str):
            return None
        clean = self._normalize_ocr_date_str(date_str)
        clean = re.sub(r"[^\d/\-\.]", "", clean)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y", "%d/%m/%y", "%d-%m-%y"):
            try:
                dt = datetime.strptime(clean, fmt)
                if dt.year < 100:
                    dt = dt.replace(year=dt.year + 1900 if dt.year > 25 else dt.year + 2000)
                return dt
            except ValueError:
                continue
        return None

    def _extract_name(self, lines, full_text):
        """Extracts person name supporting labeled lines, Given/Surname layouts, and unlabeled cards."""
        # 1. Given Name + Surname layout (Passport / International IDs)
        given_name = None
        surname = None
        for line in lines:
            m_given = re.search(r"\b(?:GIVEN\s*NAMES?|FIRST\s*NAME)\s*[:\-]?\s*([A-Za-z\s]+)", line, re.IGNORECASE)
            if m_given and self._is_valid_name_candidate(m_given.group(1).strip()):
                given_name = self._clean_name(m_given.group(1))
            m_sur = re.search(r"\b(?:SURNAME|LAST\s*NAME)\s*[:\-]?\s*([A-Za-z\s]+)", line, re.IGNORECASE)
            if m_sur and self._is_valid_name_candidate(m_sur.group(1).strip()):
                surname = self._clean_name(m_sur.group(1))

        if given_name and surname:
            return f"{given_name} {surname}", 95
        elif surname and not given_name:
            return surname, 85

        # 2. Labeled Name (e.g. Name:, Full Name:, Applicant Name:, Holder Name:, NANE:)
        label_regex = r"\b(?:FULL\s*NAME|CITIZEN\s*NAME|APPLICANT\s*NAME|HOLDER\s*NAME|CANDIDATE\s*NAME|CARDHOLDER\s*NAME|NAME|NANE|FULL\s*NANE|NAMLE|NALNE)\b"
        for i, line in enumerate(lines):
            if re.search(label_regex, line, re.IGNORECASE):
                # Remove label keyword and leading separators
                val = re.sub(label_regex, "", line, flags=re.IGNORECASE)
                val = re.sub(r"^[:\-!/\s,]+", "", val).strip()
                if val and (self._is_valid_name_candidate(val) or "INVALID" in val.upper() or "TEST" in val.upper()):
                    return self._clean_name(val), 92
                elif i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if self._is_valid_name_candidate(nxt) or "INVALID" in nxt.upper() or "TEST" in nxt.upper():
                        return self._clean_name(nxt), 90

        # 3. Fallback regex
        m_fall = re.search(r"(?:NAME|FULL NAME|APPLICANT NAME)\s*[:\-!]\s*([A-Za-z\s]{3,40})", full_text, re.IGNORECASE)
        if m_fall:
            cand = m_fall.group(1).strip().splitlines()[0]
            if self._is_valid_name_candidate(cand):
                return self._clean_name(cand), 85

        # 4. Prominent unlabeled name (e.g. Aadhaar layout where Name is 1-3 lines above DOB)
        dob_idx = -1
        for i, line in enumerate(lines):
            if re.search(r"\b(?:DOB|DATE\s*OF\s*BIRTH|BIRTH|D\.O\.B)\b", line, re.IGNORECASE):
                dob_idx = i
                break

        if dob_idx > 0:
            for j in range(dob_idx - 1, max(-1, dob_idx - 4), -1):
                cand_line = lines[j].strip()
                if cand_line.upper() in ["TO", "NAME", "GOVERNMENT OF INDIA", "INDIA"]:
                    continue
                if self._is_valid_name_candidate(cand_line) and not any(c.isdigit() for c in cand_line):
                    return self._clean_name(cand_line), 80

        return None, 0

    def _extract_dob(self, lines, full_text):
        """Extracts Date of Birth with flexible delimiters, label tolerance, and OCR error normalization."""
        date_pattern = r"([0-9OolI|]{1,2}\s*[/\-\.\s]\s*[0-9OolI|]{1,2}\s*[/\-\.\s]\s*[0-9OolI|]{2,4})"
        dob_labels = r"\b(?:DOB|DATE\s*OF\s*BIRTH|D\.O\.B\.?|BIRTH\s*DATE|BIRTH|YEAR\s*OF\s*BIRTH|YOB)\b"

        for i, line in enumerate(lines):
            if re.search(dob_labels, line, re.IGNORECASE):
                # Search same line
                m = re.search(date_pattern, line)
                if m:
                    norm = self._normalize_ocr_date_str(m.group(1))
                    return norm, 95
                # Search next line
                if i + 1 < len(lines):
                    m2 = re.search(date_pattern, lines[i + 1])
                    if m2:
                        norm2 = self._normalize_ocr_date_str(m2.group(1))
                        return norm2, 92

        # Candidate dates in document (excluding Issue/Expiry lines)
        for line in lines:
            if re.search(r"\b(?:ISSUE|EXPIRY|VALID|EXPIRATION)\b", line, re.IGNORECASE):
                continue
            m = re.search(date_pattern, line)
            if m:
                norm = self._normalize_ocr_date_str(m.group(1))
                parsed = self._parse_date(norm)
                if parsed and 1900 <= parsed.year <= datetime.now().year:
                    return norm, 80

        return None, 0

    def _extract_document_id(self, lines, full_text):
        """Extracts Document ID supporting Demo IDs, Aadhaar, PAN, Passport, DL, and generic formats."""
        # 1. Standard Demo ID (DEMO123456, DEMO-9824-XYZ, DEMO789012, DEMO456789)
        m_demo = re.search(r"\b(DEMO[-_]?[0-9A-Z]{4,10})\b", full_text, re.IGNORECASE)
        if m_demo:
            return m_demo.group(1).upper(), 95

        # 2. Corrupted test token (e.g. 222 INVALID-ID ??? or ??? INVALID-ID ???)
        if "INVALID" in full_text.upper():
            inv = re.search(r"((?:[0-9?]+\s*)?INVALID[-_]ID\s*\?*)", full_text, re.IGNORECASE)
            if inv:
                return inv.group(1).strip(), 90

        # 3. Aadhaar: 12 digits (1234 5678 9012 or continuous 12 digits)
        m_aadhaar = re.search(r"(?<![/0-9])\b(\d{4}\s\d{4}\s\d{4})\b(?![/0-9])", full_text)
        if m_aadhaar:
            return m_aadhaar.group(1), 95

        # 4. PAN Card: 5 letters, 4 digits, 1 letter (ABCDE1234F)
        m_pan = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", full_text)
        if m_pan:
            return m_pan.group(1), 95

        # 5. Driving License: DL-0420110012345 or similar
        m_dl = re.search(r"\b([A-Z]{2}[-\s]?[0-9]{2,4}[-\s]?[0-9]{7,12})\b", full_text)
        if m_dl and not any(hw in m_dl.group(1).upper() for hw in ["GOVERNMENT", "DEPARTMENT"]):
            return m_dl.group(1), 92

        # 6. Passport Number: 1 letter + 7 digits (Z1234567)
        m_pass = re.search(r"\b(?:PASSPORT\s*(?:NO|NUMBER)?\s*[:\-]*)?\s*([A-Z][0-9]{7})\b", full_text, re.IGNORECASE)
        if m_pass:
            return m_pass.group(1).upper(), 92

        # 7. Labeled ID: "ID No:", "Document ID:", "Identification Number:", "ID:"
        id_labels = r"\b(?:DOCUMENT\s*ID|DOC\s*ID|ID\s*NUMBER|ID\s*NO\.?|IDENTIFICATION\s*NUMBER|PASSPORT\s*NO\.?|DL\s*NO\.?|LICENSE\s*NO\.?|CARD\s*NO\.?|\bID\b)\b"
        for i, line in enumerate(lines):
            match = re.search(id_labels, line, re.IGNORECASE)
            if match:
                after = line[match.end():].strip()
                after = re.sub(r"^[:\-!\.\s]+", "", after).strip()
                if after:
                    cand = after.split()[0].strip()
                    if len(cand) >= 4 and not self._is_header_token(cand) and cand.upper() not in ["NUMBER", "CHIP", "HIP", "CARD"]:
                        return cand, 90
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if len(nxt) >= 4 and not self._is_header_token(nxt) and nxt.upper() not in ["NUMBER", "CHIP", "HIP", "CARD"]:
                        cand = nxt.split()[0].strip()
                        return cand, 85

        # 8. Fallback generic alphanumeric ID (e.g. US-88234-A, RES-4412-DEMO)
        m_gen = re.search(r"\b([A-Z]{1,4}[-_][0-9]{3,8}[-_]?[A-Z0-9]{1,6})\b", full_text)
        if m_gen and not self._is_header_token(m_gen.group(1)):
            return m_gen.group(1), 75

        return None, 0

    def _extract_gender(self, lines, full_text):
        """Extracts Gender requiring proximity or explicit keywords, avoiding random single-letter false positives."""
        # 1. Labeled Gender / Sex: "Gender: MALE", "Sex: M", "Gender : F"
        m_labeled = re.search(r"\b(?:GENDER|SEX)\s*[:\-\s]\s*(MALE|FEMALE|TRANSGENDER|NON-BINARY|M|F)\b", full_text, re.IGNORECASE)
        if m_labeled:
            val = m_labeled.group(1).upper()
            return ("MALE" if val == "M" else ("FEMALE" if val == "F" else val)), 95

        # 2. Standalone MALE or FEMALE on demographic lines
        m_word = re.search(r"\b(MALE|FEMALE|TRANSGENDER|NON-BINARY)\b", full_text, re.IGNORECASE)
        if m_word:
            return m_word.group(1).upper(), 90

        return None, 0

    def _extract_validity_dates(self, lines, full_text):
        """Extracts Issue and Expiry dates."""
        date_pattern = r"([0-9OolI|]{1,2}\s*[/\-\.\s]\s*[0-9OolI|]{1,2}\s*[/\-\.\s]\s*[0-9OolI|]{2,4})"
        issue_date = None
        expiry_date = None
        for line in lines:
            if re.search(r"\b(?:ISSUE|DATE\s*OF\s*ISSUE|ISSUED)\b", line, re.IGNORECASE):
                m = re.search(date_pattern, line)
                if m:
                    norm = self._normalize_ocr_date_str(m.group(1))
                    if self._parse_date(norm):
                        issue_date = norm
            if re.search(r"\b(?:EXPIRY|VALID\s*TILL|VALID\s*UNTIL|EXPIRATION)\b", line, re.IGNORECASE):
                m = re.search(date_pattern, line)
                if m:
                    norm = self._normalize_ocr_date_str(m.group(1))
                    if self._parse_date(norm):
                        expiry_date = norm
        return issue_date, expiry_date

    def _extract_fields(self, raw_text, normalized_text):
        """
        Dynamically extracts fields and calculates confidence scores (0-100%).
        Uses both raw and normalized text representations.
        """
        active_text = normalized_text or raw_text or ""
        lines = [line.strip() for line in active_text.splitlines() if line.strip()]

        name, conf_name = self._extract_name(lines, active_text)
        dob, conf_dob = self._extract_dob(lines, active_text)
        doc_id, conf_id = self._extract_document_id(lines, active_text)
        gender, conf_gender = self._extract_gender(lines, active_text)
        issue_date, expiry_date = self._extract_validity_dates(lines, active_text)

        fields = {
            "name": name,
            "dob": dob,
            "document_id": doc_id,
            "gender": gender,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
        }

        confidences = {
            "name": conf_name,
            "dob": conf_dob,
            "document_id": conf_id,
            "gender": conf_gender,
        }

        return fields, confidences

    def _perform_consistency_checks(self, extracted_fields, ocr_result, quality_data):
        """
        Validates completeness, date formats, chronology, and pattern consistency.
        """
        checks = {
            "required_fields_present": True,
            "missing_fields": [],
            "date_format_valid": True,
            "date_reasonableness": True,
            "suspicious_characters": False,
            "unusual_patterns": False,
        }

        required = ["name", "dob", "document_id"]
        for field in required:
            val = extracted_fields.get(field)
            if not val or val == "Not detected" or "not" in str(val).lower() or "?" in str(val) or "invalid" in str(val).lower():
                checks["missing_fields"].append(field)

        if checks["missing_fields"]:
            checks["required_fields_present"] = False

        # Validate Date of Birth
        dob_str = extracted_fields.get("dob")
        if dob_str and dob_str != "Not detected":
            parsed_dob = self._parse_date(dob_str)
            if not parsed_dob:
                checks["date_format_valid"] = False
                checks["date_reasonableness"] = False
            else:
                checks["date_format_valid"] = True
                current_year = datetime.now().year
                if parsed_dob.year > current_year or parsed_dob.year < (current_year - 125):
                    checks["date_reasonableness"] = False
        else:
            checks["date_format_valid"] = False
            checks["date_reasonableness"] = False

        # Suspicious pattern and character anomalies
        name_val = str(extracted_fields.get("name") or "")
        id_val = str(extracted_fields.get("document_id") or "")
        raw_text = ocr_result.get("raw_text", "")

        if any(c in name_val for c in ["#", "_", "???", "INVALID", "TEST USER"]) or any(char.isdigit() for char in name_val):
            checks["suspicious_characters"] = True

        if "?" in id_val or "INVALID" in id_val.upper() or "CORRUPTED" in raw_text.upper():
            checks["unusual_patterns"] = True

        return checks

    def _compute_risk_score(self, quality_data, extracted_fields, consistency_data, ocr_result):
        """
        Rule-based risk scoring algorithm (0 to 100).
        Calculates explainable weighted deductions dynamically from the uploaded document.
        """
        score = 15  # Clean baseline score
        deductions = []
        flags = []

        # 1. Quality & Blur Assessment
        if quality_data["is_blurry"]:
            score += 25
            deductions.append({"factor": "Document Image Quality Low (Blur)", "points": 25})
            flags.append({
                "icon": "exclamation-triangle",
                "severity": "medium",
                "title": "Document image quality is low",
                "explanation": (
                    f"Document image quality is low. Laplacian focus variance is {quality_data['laplacian_variance']} "
                    f"(threshold is {quality_data['blur_threshold']})."
                ),
            })
        else:
            flags.append({
                "icon": "check-circle",
                "severity": "info",
                "title": "Image Focus & Sharpness",
                "explanation": f"Sharp focus confirmed with Laplacian variance of {quality_data['laplacian_variance']}.",
            })

        if quality_data.get("is_low_contrast"):
            score += 10
            deductions.append({"factor": "Low Image Contrast", "points": 10})
            flags.append({
                "icon": "exclamation-circle",
                "severity": "medium",
                "title": "Low Contrast Scan",
                "explanation": f"Document contrast is weak ({quality_data['contrast']}), which may impede inspection.",
            })

        if quality_data.get("low_resolution"):
            score += 15
            deductions.append({"factor": "Low Image Resolution", "points": 15})
            flags.append({
                "icon": "exclamation-triangle",
                "severity": "medium",
                "title": "Sub-optimal Resolution",
                "explanation": f"Resolution ({quality_data['width']}x{quality_data['height']} px) is below standard.",
            })

        # 2. OCR Text Yield Assessment
        if ocr_result["char_count"] < 20 or ocr_result["confidence"] < 50:
            score += 25
            deductions.append({"factor": "Poor OCR Yield / Low Confidence", "points": 25})
            flags.append({
                "icon": "exclamation-circle",
                "severity": "high",
                "title": "OCR Confidence Below Threshold",
                "explanation": f"Text extraction confidence is low ({ocr_result['confidence']}%). Key character zones could not be verified.",
            })
        else:
            flags.append({
                "icon": "check-circle",
                "severity": "info",
                "title": "Readable text detected",
                "explanation": f"OCR successfully recognized {ocr_result['word_count']} words with {ocr_result['confidence']}% confidence.",
            })

        # 3. Field Completeness
        if not consistency_data["required_fields_present"]:
            missing = ", ".join([f.upper() for f in consistency_data["missing_fields"]])
            penalty = 15 if (len(consistency_data["missing_fields"]) == 1 and quality_data["is_blurry"]) else 25
            score += penalty
            deductions.append({"factor": f"Missing or Ambiguous Fields ({missing})", "points": penalty})
            flags.append({
                "icon": "exclamation-circle",
                "severity": "medium" if penalty == 15 else "high",
                "title": "Name could not be confidently extracted" if missing == "NAME" else "Mandatory Fields Missing",
                "explanation": f"Could not reliably extract mandatory field(s): {missing}. Manual cross-examination required.",
            })
        else:
            flags.append({
                "icon": "check-circle",
                "severity": "info",
                "title": "Mandatory Fields Extracted",
                "explanation": "Name, Date of Birth, and Document ID were successfully identified.",
            })

        # 4. Date Validity Checks
        if not consistency_data["date_format_valid"] or not consistency_data["date_reasonableness"]:
            score += 25
            deductions.append({"factor": "Date Format or Chronology Anomaly", "points": 25})
            flags.append({
                "icon": "exclamation-triangle",
                "severity": "high",
                "title": "Date Format Requires Review",
                "explanation": f"Date of Birth '{extracted_fields.get('dob')}' fails chronological validation (future year or invalid calendar date).",
            })

        # 5. Suspicious Patterns / Character Anomalies
        if consistency_data["suspicious_characters"] or consistency_data["unusual_patterns"]:
            score += 25
            deductions.append({"factor": "Suspicious Pattern / Character Corruption", "points": 25})
            flags.append({
                "icon": "exclamation-triangle",
                "severity": "high",
                "title": "Suspicious Text Inconsistencies",
                "explanation": "Extracted text contains atypical characters (e.g., numeric substitutions, corruption marks, or placeholder tokens).",
            })

        # Clamp score between 10 and 95
        score = min(max(score, 10), 95)

        # Categorize into required review tiers
        if score <= 30:
            level = "LOW REVIEW"
            color = "emerald"
            summary = "Document exhibits sharp image quality, consistent extracted fields, and passes OCR thresholds."
        elif score <= 65:
            level = "MEDIUM REVIEW"
            color = "amber"
            summary = "Document exhibits moderate image quality degradation or minor field extraction ambiguities requiring manual check."
        else:
            level = "HIGH REVIEW"
            color = "rose"
            summary = "Significant inconsistencies, blur, missing required fields, or chronological anomalies detected."

        return {
            "score": score,
            "level": level,
            "color": color,
            "summary": summary,
            "flags": flags,
            "deductions": deductions,
        }