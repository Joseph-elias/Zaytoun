from backend.app.models.diagnosis import SupportedLanguage


SUPPORTED_LANGUAGES: tuple[SupportedLanguage, ...] = ("ar", "fr", "en")


def resolve_language(user_language: str | None) -> SupportedLanguage:
    if user_language in SUPPORTED_LANGUAGES:
        return user_language
    return "en"
