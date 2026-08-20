from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ImportRowPreview(BaseModel):
    row_number: int
    data: Dict[str, Any]
    errors: List[str]


class ImportPreviewResponse(BaseModel):
    rows: List[ImportRowPreview]
    valid_count: int
    total_count: int


class ImportCommitRequest(BaseModel):
    rows: List[ImportRowPreview]


class ImportRowOutcome(BaseModel):
    row_number: int
    sku: Optional[str] = None
    error: Optional[str] = None
    product_id: Optional[int] = None
    variant_id: Optional[int] = None


class ImportSummaryResponse(BaseModel):
    created_count: int
    updated_count: int
    failed_count: int
    created: List[ImportRowOutcome]
    updated: List[ImportRowOutcome]
    failed: List[ImportRowOutcome]
