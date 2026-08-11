from typing import Any, Dict

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.catalog_schemas import ProductCreateRequest
from app.services import catalog_service
from app.services import store_page_service


class ToolExecutionResult:
    def __init__(self, tool_name: str, output: Any, is_error: bool):
        self.tool_name = tool_name
        self.output = output
        self.is_error = is_error


async def execute_tool(
    tool_name: str, raw_input: Dict[str, Any], tenant_slug: str, db: AsyncSession
) -> ToolExecutionResult:
    """
    Executes a single tool call by name, always scoped to `tenant_slug` — the
    tenant bound server-side from the authenticated admin's JWT, never from the
    model's own function-call arguments (any tenant/vendor-like field in
    `raw_input` is simply never read below). Errors are caught and returned as a
    structured tool result instead of propagating, so a single bad tool call
    surfaces to the agent loop (and the user) instead of crashing the chat turn.
    """
    try:
        if tool_name == "list_page_targets":
            targets = await store_page_service.list_page_targets_service(tenant_slug, db)
            return ToolExecutionResult(tool_name, [t.model_dump(mode="json") for t in targets], False)

        if tool_name == "list_categories":
            categories = await catalog_service.list_public_categories_service(tenant_slug, db)
            return ToolExecutionResult(tool_name, [c.model_dump(mode="json") for c in categories], False)

        if tool_name == "get_page_schema":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            if not page_key or page_type not in ("static_page", "template"):
                raise ValueError("page_key and a valid page_type are required")
            schema = await store_page_service.get_page_schema_service(tenant_slug, page_key, page_type, db)
            return ToolExecutionResult(tool_name, schema.model_dump(mode="json"), False)

        if tool_name == "update_page_sections":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            sections = raw_input.get("sections")
            if not page_key or page_type not in ("static_page", "template") or not isinstance(sections, list):
                raise ValueError("page_key, page_type, and a sections array are required")
            schema = await store_page_service.upsert_page_sections_service(
                tenant_slug, page_key, page_type, sections, db,
                background_color=raw_input.get("background_color"),
                text_color=raw_input.get("text_color"),
            )
            return ToolExecutionResult(tool_name, schema.model_dump(mode="json"), False)

        if tool_name == "create_product":
            req = ProductCreateRequest(
                category_id=raw_input.get("category_id"),
                name=raw_input.get("name") or {},
                slug=raw_input.get("slug", ""),
                description=raw_input.get("description"),
                base_price=raw_input.get("base_price"),
                variants=raw_input.get("variants") or [],
                images=raw_input.get("images") or [],
            )
            product = await catalog_service.create_product_service(tenant_slug, req, db)
            return ToolExecutionResult(tool_name, product.model_dump(mode="json"), False)

        return ToolExecutionResult(tool_name, {"error": f"Unknown tool: {tool_name}"}, True)
    except HTTPException as exc:
        return ToolExecutionResult(tool_name, {"error": exc.detail}, True)
    except ValidationError as exc:
        return ToolExecutionResult(tool_name, {"error": exc.errors()}, True)
    except ValueError as exc:
        return ToolExecutionResult(tool_name, {"error": str(exc)}, True)
