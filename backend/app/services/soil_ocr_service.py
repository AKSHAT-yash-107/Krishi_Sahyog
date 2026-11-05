import io
import re
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = RapidOCR()
    return _engine

def extract_soil_card(image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result, _ = _get_engine()(np.asarray(image))
    lines = [str(row[1]) for row in (result or []) if len(row) >= 2]
    raw = "\n".join(lines)
    text = raw.lower().replace("：", ":")

    def value(patterns):
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                try: return float(m.group(1).replace(",", ""))
                except ValueError: pass
        return None

    # Label-specific patterns reduce accidental capture of unrelated numbers.
    values = {
        "nitrogen": value([r"(?:available\s+)?nitrogen\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)", r"\bN\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"]),
        "phosphorus": value([r"(?:available\s+)?phosph(?:orus|orous)\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)", r"\bP\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"]),
        "potassium": value([r"(?:available\s+)?potassium\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)", r"\bK\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"]),
        "ph": value([r"(?:soil\s*)?pH\s*[:=\-]?\s*([0-9]+(?:\.[0-9]+)?)"]),
    }
    return {"extracted_values": values, "raw_text": raw,
            "missing_fields": [k for k,v in values.items() if v is None],
            "needs_review": True,
            "message": "OCR is a draft extraction. Verify every value and unit against the original laboratory report."}
