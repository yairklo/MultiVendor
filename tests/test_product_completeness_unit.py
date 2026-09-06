from types import SimpleNamespace

from app.services.product_completeness import (
    completeness_required,
    gaps_for_product,
    missing_i18n_langs,
    product_completeness_gaps,
    product_is_store_eligible,
    supported_languages_of,
)


def test_completeness_required_or_forced():
    assert completeness_required(None) is False
    assert completeness_required(SimpleNamespace(require_product_completeness=False, force_product_completeness=False)) is False
    assert completeness_required(SimpleNamespace(require_product_completeness=True, force_product_completeness=False)) is True
    assert completeness_required(SimpleNamespace(require_product_completeness=False, force_product_completeness=True)) is True


def test_missing_i18n_langs():
    assert missing_i18n_langs({"he": "שם", "en": "Name"}, ["he", "en"]) == []
    assert missing_i18n_langs({"he": "שם", "en": "  "}, ["he", "en"]) == ["en"]
    assert missing_i18n_langs("plain", ["he"]) == ["he"]


def test_complete_product_has_no_gaps():
    gaps = product_completeness_gaps(
        name={"he": "חולצה", "en": "Shirt"},
        description={"he": "כותנה", "en": "Cotton"},
        slug="shirt",
        base_price=20,
        product_type="physical",
        digital_file_url=None,
        variant_skus=["SHIRT-M"],
        image_urls=["http://test.com/shirt.png"],
        supported_langs=["he", "en"],
    )
    assert gaps == []


def test_incomplete_product_reports_missing_fields():
    gaps = product_completeness_gaps(
        name={"he": "חולצה"},
        description=None,
        slug="shirt",
        base_price=20,
        product_type="digital",
        digital_file_url=None,
        variant_skus=["SHIRT-M"],
        image_urls=[],
        supported_langs=["he", "en"],
    )
    assert any("name translations" in g for g in gaps)
    assert any("description translations" in g for g in gaps)
    assert "at least one image" in gaps
    assert "digital_file_url" in gaps


def test_store_eligibility_respects_flags_and_is_active():
    product = SimpleNamespace(
        is_active=True,
        name={"he": "שם"},
        description={"he": "תיאור"},
        slug="p",
        base_price=10,
        product_type="physical",
        digital_file_url=None,
        variants=[SimpleNamespace(sku="SKU")],
        images=[SimpleNamespace(image_url="http://x")],
    )
    off = SimpleNamespace(require_product_completeness=False, force_product_completeness=False, supported_languages=["he"])
    on = SimpleNamespace(require_product_completeness=True, force_product_completeness=False, supported_languages=["he", "en"])
    assert product_is_store_eligible(product, off) is True
    assert product_is_store_eligible(product, on) is False
    product.is_active = False
    assert product_is_store_eligible(product, off) is False


def test_supported_languages_default_hebrew():
    assert supported_languages_of(None) == ["he"]
    assert supported_languages_of(SimpleNamespace(supported_languages=["ja", "he"])) == ["ja", "he"]


def test_gaps_for_product_uses_related_collections():
    product = SimpleNamespace(
        name={"he": "שם", "en": "Name"},
        description={"he": "תיאור", "en": "Desc"},
        slug="p",
        base_price=5,
        product_type="physical",
        digital_file_url=None,
        variants=[SimpleNamespace(sku="A")],
        images=[SimpleNamespace(image_url="http://x")],
    )
    assert gaps_for_product(product, ["he", "en"]) == []
