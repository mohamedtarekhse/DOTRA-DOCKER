import re


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
