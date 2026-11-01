import calendar
import io
import os
import re
import time
import unicodedata
from datetime import date

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps, UnidentifiedImageError

if os.environ.get('TESSERACT_CMD'):
    pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_CMD']


MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
DATE_DIGITS = r'[0-9OQILS]'
DATE_PATTERN = re.compile(
    rf'(?<![0-9])({DATE_DIGITS}{{4}}[-/.]{DATE_DIGITS}{{1,2}}[-/.]{DATE_DIGITS}{{1,2}}|'
    rf'{DATE_DIGITS}{{1,2}}[-/.]{DATE_DIGITS}{{1,2}}[-/.]{DATE_DIGITS}{{2,4}}|'
    rf'{DATE_DIGITS}{{1,2}}[-/.]{DATE_DIGITS}{{2,4}})(?![0-9])'
)
DATE_DIGIT_FIX = str.maketrans({'O': '0', 'Q': '0', 'I': '1', 'L': '1', 'S': '5'})
LABEL_DIGIT_FIX = str.maketrans({'O': '0', 'Q': '0', 'I': '1', 'L': '1', 'S': '5'})


def _clean_ocr_confusions(value):
    return value.upper().translate(DATE_DIGIT_FIX)


def parse_date(value):
    value = _clean_ocr_confusions(value).replace('.', '/').replace('-', '/')
    parts = value.split('/')
    try:
        if len(parts) == 3 and len(parts[0]) == 4:
            year, month, day = map(int, parts)
        elif len(parts) == 3:
            day, month, year = map(int, parts)
            if year < 100:
                year += 2000
        elif len(parts) == 2:
            month, year = map(int, parts)
            if year < 100:
                year += 2000
            day = calendar.monthrange(year, month)[1]
        else:
            return None
        return date(year, month, day)
    except (ValueError, OverflowError):
        return None


def _field(value, confidence):
    return {'value': value, 'confidence': round(max(0.0, min(1.0, confidence)), 2)}


def extract_pack_fields(text, confidence=0.75):
    normalized = unicodedata.normalize('NFKC', text or '')
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    batch = None
    expiry = None
    manufacture = None
    for line in lines:
        upper = line.upper()
        batch_match = re.search(
            r'\b(?:BATCH(?:\s*(?:NO|NUMBER))?|L[O0Q]T(?:\s*(?:NO|NUMBER))?|B[N0]N?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]{2,30})',
            upper,
        )
        if batch is None and batch_match:
            batch = _clean_ocr_confusions(batch_match.group(1)).strip('-/')

        for label, key in (
            (r'(?:EXP(?:IRY)?\.?(?:\s*DATE)?|USE\s*BY)', 'expiry'),
            (r'(?:MFG|MFD|MANUFACTURED|MANUFACTURING)(?:\.?\s*DATE)?', 'manufacture'),
        ):
            match = re.search(label + r'\s*[:#-]?\s*(.{0,30})', upper)
            if not match:
                continue
            date_match = DATE_PATTERN.search(match.group(1))
            if not date_match:
                continue
            parsed = parse_date(date_match.group(1))
            if parsed:
                value = parsed.isoformat()
                if key == 'expiry' and expiry is None:
                    expiry = value
                elif key == 'manufacture' and manufacture is None:
                    manufacture = value

    confidence_adjustment = 0.1 if confidence < 0.55 else 0
    return {
        'batch_number': _field(batch, confidence - confidence_adjustment if batch else 0),
        'expiry_date': _field(expiry, confidence - confidence_adjustment if expiry else 0),
        'manufacturing_date': _field(manufacture, confidence - confidence_adjustment if manufacture else 0),
    }


def _deskew(image):
    points = np.column_stack(np.where(image < 255))
    if len(points) < 10:
        return image
    angle = cv2.minAreaRect(points)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.5 or abs(angle) > 15:
        return image
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_image(image_bytes):
    if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError('Image must be non-empty and no larger than 5 MB.')
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise ValueError('Only JPEG, PNG, and WEBP image files are supported.')
            if source.width * source.height > 20_000_000:
                raise ValueError('Image dimensions exceed the supported limit.')
            source.verify()
        with Image.open(io.BytesIO(image_bytes)) as source:
            if source.width * source.height > 20_000_000:
                raise ValueError('Image dimensions exceed the supported limit.')
            image = ImageOps.exif_transpose(source).convert('RGB')
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            clean_bytes = buffer.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('The uploaded file is not a valid supported image.') from exc

    decoded = cv2.imdecode(np.frombuffer(clean_bytes, np.uint8), cv2.IMREAD_COLOR)
    if decoded is None:
        raise ValueError('The uploaded image could not be decoded.')
    gray = cv2.cvtColor(decoded, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 12, 7, 21)
    enlarged = cv2.resize(denoised, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    thresholded = cv2.adaptiveThreshold(
        enlarged, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11,
    )
    return _deskew(thresholded)


def read_pack_image(image_bytes):
    started = time.perf_counter()
    prepared = preprocess_image(image_bytes)
    data = pytesseract.image_to_data(prepared, output_type=pytesseract.Output.DICT, config='--psm 6')
    text = pytesseract.image_to_string(prepared, config='--psm 6')
    confidences = [
        float(value) for value, word in zip(data.get('conf', []), data.get('text', []))
        if word.strip() and str(value).strip() not in ('', '-1')
    ]
    mean_confidence = max(0.0, min(1.0, (sum(confidences) / len(confidences) / 100) if confidences else 0.0))
    fields = extract_pack_fields(text, mean_confidence)
    return {
        'raw_text': text,
        **fields,
        'processing_ms': round((time.perf_counter() - started) * 1000, 1),
    }
