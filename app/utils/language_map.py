SPEECH_TO_TRANSLATOR_LANG = {
    "ko-KR": "ko",
    "en-US": "en",
    "ja-JP": "ja",
    "zh-CN": "zh-Hans",
    "zh-Hans": "zh-Hans",
    "ko": "ko",
    "en": "en",
    "ja": "ja",
}


def normalize_language(lang: str | None) -> str | None:
    if not lang:
        return None
    return SPEECH_TO_TRANSLATOR_LANG.get(lang, lang)