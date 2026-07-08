import re
from app.config import settings


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def remove_fillers(text: str) -> str:
    if not text:
        return text

    filler_pattern = r"\b(" + "|".join(map(re.escape, settings.filler_words)) + r")\b"
    text = re.sub(filler_pattern, "", text, flags=re.IGNORECASE)
    return normalize_whitespace(text)


def ensure_sentence_punctuation(text: str) -> str:
    if not text:
        return text
    if text[-1] not in ".!?。！？":
        return text + "."
    return text


def clean_transcript_text(text: str) -> str:
    text = normalize_whitespace(text)
    text = remove_fillers(text)
    text = ensure_sentence_punctuation(text)
    return text