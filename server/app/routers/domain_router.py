from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.tenant_service import resolve_tenant_by_domain_service

# Not nested under storefront_router (despite the shared /api/v1/store
# prefix): every route there carries a router-level get_current_tenant
# dependency that expects a `tenant_slug` path param, which this endpoint
# doesn't have -- it's the thing that produces a tenant_slug, not something
# that's given one.
domain_router = APIRouter(prefix="/api/v1/store", tags=["Public Storefront"])


@domain_router.get(
    "/resolve-domain",
    summary="Resolve a custom domain to a tenant slug",
    description=(
        "Looks up which active tenant, if any, has claimed the given hostname as "
        "Tenant.custom_domain. Two callers: Caddy's on_demand_tls 'ask' check "
        "(see Caddyfile) only cares about the 2xx/non-2xx status code, to decide "
        "whether to issue a TLS certificate for that hostname; the Next.js proxy "
        "(frontend/src/proxy.ts) reads tenant_slug from the body to rewrite a "
        "request on a custom domain to the matching /store/{slug} route "
        "internally. There is no separate domain-ownership challenge: as with "
        "any platform that lets a seller point their own domain at it, only "
        "whoever controls the domain's DNS can make it resolve to this server "
        "in the first place, so DNS pointing here already is the proof."
    ),
    responses={
        200: {"description": "An active tenant has claimed this domain."},
        404: {"description": "No active tenant has claimed this domain."},
    },
)
async def resolve_domain(
    domain: str = Query(..., description="Hostname to resolve, e.g. www.sellerbrand.com"),
    db: AsyncSession = Depends(get_db),
):
    slug = await resolve_tenant_by_domain_service(domain, db)
    if not slug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tenant claims this domain")
    return {"tenant_slug": slug}
