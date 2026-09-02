import re

import xmltodict

# Hikvision eventDirection: 1 = entering (towards camera), 2 = leaving
DIRECTION_MAP = {"1": "in", "2": "out"}


def normalize_plate(raw: str) -> str:
    """Normalize a plate string: strip spaces, uppercase, remove non-alphanumerics."""
    if not raw:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9\u0600-\u06FF]", "", raw)
    return cleaned.upper()


ARABIC_DIGITS = {"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
                 "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"}


def arabic_plate_to_latin(text: str) -> str:
    """Convert Arabic-Indic numerals common on Egyptian plates to Latin digits."""
    return "".join(ARABIC_DIGITS.get(ch, ch) for ch in text)


def _walk(node, items):
    """Recursively surface {plateNumber} records regardless of XML nesting depth."""
    if isinstance(node, dict):
        item = dict(node)
        plate = item.pop("plateNumber", None) or item.pop("Platenumber", None)
        if plate is not None:
            items.append(item | {"plateNumber": plate})
        for value in item.values():
            _walk(value, items)
    elif isinstance(node, list):
        for value in node:
            _walk(value, items)


def parse_plates(xml_text: str) -> list[dict]:
    """Parse Hikvision ISAPI TP/VehicleDetect XML into normalized plate dicts.

    Returns entries like {"plate_number": "AB123", "direction": "in", "event_time": "..."},
    with Arabic digits converted and plates normalized.
    """
    try:
        data = xmltodict.parse(xml_text)
    except Exception:
        return []
    items: list[dict] = []
    _walk(data, items)
    out = []
    for item in items:
        plate = arabic_plate_to_latin(item.get("plateNumber", ""))
        plate = normalize_plate(plate)
        if not plate:
            continue
        direction = DIRECTION_MAP.get(str(item.get("eventDirection", "")).strip(), "in")
        out.append({
            "plate_number": plate,
            "direction": direction,
            "event_time": str(item.get("eventTime", "")),
            "confidence": item.get("plateRecognitionConfidence"),
        })
    return out
