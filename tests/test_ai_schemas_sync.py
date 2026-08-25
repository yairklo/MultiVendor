from app.schemas.ai_schemas import CARD_STYLES

def test_card_styles_include_apple_ui_variants():
    assert "glass" in CARD_STYLES
    assert "elevated" in CARD_STYLES
    assert "default" in CARD_STYLES
    assert "framed" in CARD_STYLES
    assert "minimal" in CARD_STYLES
    assert len(CARD_STYLES) == 5
