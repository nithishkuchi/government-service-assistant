"""Shared translation language configuration for the knowledge base."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TranslationLanguage:
    code: str
    name: str
    native_name: str
    category: str
    supported_now: bool = True
    model_code: str | None = None
    notes: str = ""


SCHEDULED_LANGUAGES: List[TranslationLanguage] = [
    TranslationLanguage("hi", "Hindi", "Hindi", "scheduled", model_code="hin_Deva"),
    TranslationLanguage("bn", "Bengali", "Bangla", "scheduled", model_code="ben_Beng"),
    TranslationLanguage("te", "Telugu", "Telugu", "scheduled", model_code="tel_Telu"),
    TranslationLanguage("mr", "Marathi", "Marathi", "scheduled", model_code="mar_Deva"),
    TranslationLanguage("ta", "Tamil", "Tamil", "scheduled", model_code="tam_Taml"),
    TranslationLanguage("ur", "Urdu", "Urdu", "scheduled", model_code="urd_Arab"),
    TranslationLanguage("gu", "Gujarati", "Gujarati", "scheduled", model_code="guj_Gujr"),
    TranslationLanguage("kn", "Kannada", "Kannada", "scheduled", model_code="kan_Knda"),
    TranslationLanguage("ml", "Malayalam", "Malayalam", "scheduled", model_code="mal_Mlym"),
    TranslationLanguage("or", "Odia", "Odia", "scheduled", model_code="ory_Orya"),
    TranslationLanguage("pa", "Punjabi", "Punjabi", "scheduled", model_code="pan_Guru"),
    TranslationLanguage("as", "Assamese", "Assamese", "scheduled", model_code="asm_Beng"),
    TranslationLanguage("mai", "Maithili", "Maithili", "scheduled", model_code="mai_Deva"),
    TranslationLanguage("sa", "Sanskrit", "Sanskrit", "scheduled", model_code="san_Deva"),
    TranslationLanguage("sat", "Santali", "Santali", "scheduled", model_code="sat_Beng"),
    TranslationLanguage("ks", "Kashmiri", "Kashmiri", "scheduled", model_code="kas_Arab"),
    TranslationLanguage("ne", "Nepali", "Nepali", "scheduled", model_code="npi_Deva"),
    TranslationLanguage("sd", "Sindhi", "Sindhi", "scheduled", model_code="snd_Arab"),
    TranslationLanguage("gom", "Konkani", "Konkani", "scheduled", supported_now=False, notes="Model does not support Konkani directly."),
    TranslationLanguage("doi", "Dogri", "Dogri", "scheduled", supported_now=False, notes="Model does not support Dogri directly."),
    TranslationLanguage("brx", "Bodo", "Bodo", "scheduled", supported_now=False, notes="Model does not support Bodo directly."),
    TranslationLanguage("mni", "Manipuri", "Meitei", "scheduled", model_code="mni_Beng"),
]


ADDITIONAL_LANGUAGES: List[TranslationLanguage] = [
    TranslationLanguage("tcy", "Tulu", "Tulu", "additional", supported_now=False, notes="Needs separate backend support."),
    TranslationLanguage("bho", "Bhojpuri", "Bhojpuri", "additional", model_code="bho_Deva"),
    TranslationLanguage("raj", "Rajasthani", "Rajasthani", "additional", supported_now=False, notes="Needs separate backend support."),
    TranslationLanguage("hne", "Chhattisgarhi", "Chhattisgarhi", "additional", model_code="hne_Deva"),
    TranslationLanguage("bgc", "Haryanvi", "Haryanvi", "additional", supported_now=False, notes="Needs separate backend support."),
    TranslationLanguage("mag", "Magahi", "Magahi", "additional", model_code="mag_Deva"),
    TranslationLanguage("awa", "Awadhi", "Awadhi", "additional", model_code="awa_Deva"),
    TranslationLanguage("mwr", "Marwari", "Marwari", "additional", supported_now=False, notes="Needs separate backend support."),
    TranslationLanguage("bns", "Bundeli", "Bundeli", "additional", supported_now=False, notes="Needs separate backend support."),
    TranslationLanguage("gon", "Gondi", "Gondi", "additional", supported_now=False, notes="Needs separate backend support."),
    TranslationLanguage("kru", "Kurukh", "Kurukh", "additional", supported_now=False, notes="Needs separate backend support."),
]


ALL_REQUESTED_LANGUAGES: List[TranslationLanguage] = SCHEDULED_LANGUAGES + ADDITIONAL_LANGUAGES


def get_supported_languages() -> List[TranslationLanguage]:
    """Languages we plan to generate with the free first-pass pipeline."""
    return [lang for lang in ALL_REQUESTED_LANGUAGES if lang.supported_now]
