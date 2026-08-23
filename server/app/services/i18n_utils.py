from typing import Any, List

from fastapi import HTTPException


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
