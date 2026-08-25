import re
from typing import Any, List

from fastapi import HTTPException

# BCP-47-ish tags: "he", "en", "pt-BR", "zh-Hans". Sellers pick any language they
# actually sell in — we don't keep a closed allowlist on the backend.
LANG_CODE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")


def validate_language_codes(codes: List[str]) -> None:
    if not codes:
        raise HTTPException(status_code=422, detail="At least one supported language is required")
    seen: set[str] = set()
    for code in codes:
        if not isinstance(code, str) or not LANG_CODE_RE.match(code):
            raise HTTPException(status_code=422, detail=f"Invalid language code: {code}")
        if code in seen:
            raise HTTPException(status_code=422, detail=f"Duplicate language code: {code}")
        seen.add(code)


def validate_i18n(field_dict: Any, supported_langs: List[str], field_name: str) -> None:
    """Raises 422 unless field_dict has a non-empty value for every one of supported_langs.
    Shared by catalog_service.py (product name/description) and store_page_service.py
    (section text) -- one enforcement rule for every place a store's content is localized.
    """
    if not isinstance(field_dict, dict):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a dictionary of translations")
    missing = [lang for lang in supported_langs if lang not in field_dict or not str(field_dict[lang]).strip()]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required translations for {field_name} in languages: {missing}")
