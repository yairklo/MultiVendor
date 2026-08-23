"""Marker mixin for ORM models that belong to exactly one tenant.

TenantAwareSession auto-filters SELECT/UPDATE/DELETE against these classes and
stamps tenant_id on INSERT. Models that happen to have a tenant_id column but
live on the platform plane (MarketplaceCartItem, UserStoreMembership) must NOT
inherit this mixin.
"""


class TenantScoped:
    pass
