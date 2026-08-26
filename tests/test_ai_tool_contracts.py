"""Schema ↔ service contract: every AI tool field must map to a real service input."""
from app.schemas.ai_schemas import Section
from app.schemas.catalog_schemas import CategoryCreateRequest, CategoryUpdateRequest, ProductCreateRequest, ProductUpdateRequest
from app.schemas.order_schemas import CouponCreateRequest, CouponUpdateRequest
from app.schemas.tenant_schemas import TenantSettingsUpdateSchema
from app.services.ai_pending_action_service import GATED_TOOLS
from app.services.ai_tool_executor import READ_TOOLS, TOOL_PROPERTIES, WRITE_TOOLS
from app.services.ai_tools import _SECTION_SCHEMA_DEFS, ai_tools


PASSTHROUGH_MODELS = {
    "create_product": (ProductCreateRequest, set()),
    "update_product": (ProductUpdateRequest, {"product_id"}),
    "create_category": (CategoryCreateRequest, set()),
    "update_category": (CategoryUpdateRequest, {"category_id"}),
    "create_coupon": (CouponCreateRequest, set()),
    "update_coupon": (CouponUpdateRequest, {"coupon_id"}),
    "update_store_settings": (TenantSettingsUpdateSchema, set()),
}

ALWAYS_GATED = {
    "delete_product", "delete_category", "delete_coupon", "delete_shipping_config",
    "publish_page", "revert_page_version", "apply_storefront_template", "upgrade_subscription",
}


def test_every_declared_tool_is_classified_read_or_write():
    names = {t["name"] for t in ai_tools}
    assert names == set(TOOL_PROPERTIES)
    assert names == READ_TOOLS | WRITE_TOOLS
    assert READ_TOOLS.isdisjoint(WRITE_TOOLS)


def test_passthrough_tool_fields_exist_on_service_request_models():
    for tool_name, (model, extras) in PASSTHROUGH_MODELS.items():
        schema_fields = TOOL_PROPERTIES[tool_name]
        model_fields = set(model.model_fields)
        unmapped = schema_fields - extras - model_fields
        assert not unmapped, f"{tool_name} schema fields missing from {model.__name__}: {unmapped}"


def test_section_schema_defs_match_section_model():
    section_props = set(_SECTION_SCHEMA_DEFS["Section"]["properties"])
    assert section_props == set(Section.model_fields)


def test_gated_tools_are_registered_for_human_confirmation():
    assert ALWAYS_GATED <= set(GATED_TOOLS)
    for name in ALWAYS_GATED:
        assert name in TOOL_PROPERTIES
        assert name in WRITE_TOOLS
