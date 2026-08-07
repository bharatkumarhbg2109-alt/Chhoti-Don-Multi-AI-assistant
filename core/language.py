"""
Chhoti Don - Language Processing
Language detection, Hinglish support, and translation utilities.
Phase 2.2 - Full Upgrade
"""

import re

SUPPORTED_LANGS = {"en", "hi", "es", "zh-cn", "ja", "fr", "de", "ar"}

# Hinglish indicator words
HINGLISH_INDICATORS = [
    "karo", "kya", "hai", "mein", "ka", "ki", "ke", "se", "pe",
    "aur", "nahi", "hain", "tum", "main", "mera", "tera", "acha",
    "theek", "shukriya", "batao", "samjhao", "banao", "likho",
    "chalao", "dekho", "bolo", "kaise", "kyun", "kab", "yaar",
    "ek",
]


def detect_language(text: str) -> str:
    """
    Detect language with Hinglish support.
    Preserved + upgraded.
    """
    if not isinstance(text, str) or not text.strip():
        return "en"

    text_lower = text.lower()

    # Hinglish detection (before langdetect)
    hinglish_score = sum(1 for word in HINGLISH_INDICATORS if word in text_lower)
    if hinglish_score >= 2:
        return "hi"

    # Try langdetect
    try:
        from langdetect import detect
        lang = detect(text.strip())
        return lang if lang in SUPPORTED_LANGS else "en"
    except Exception:
        pass

    # Fallback — check common Hindi/Devanagari script
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"

    return "en"


def is_hinglish(text: str) -> bool:
    """Is text Hinglish (Hindi-English mix)?"""
    text_lower = text.lower()
    hindi_count = sum(1 for w in HINGLISH_INDICATORS if w in text_lower)
    english_words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    return hindi_count >= 1 and len(english_words) >= 1


def get_response_language(input_text: str) -> str:
    """Determine what language to respond in."""
    lang = detect_language(input_text)
    if lang == "hi" or is_hinglish(input_text):
        return "hinglish"
    return "en"


def translate_to_english(text: str) -> str:
    """Placeholder for translation. Preserved."""
    if not isinstance(text, str):
        return ""
    return text


def translate_back(text: str, target_lang: str) -> str:
    """Placeholder for reverse translation. Preserved."""
    if not isinstance(text, str):
        return ""
    return text
