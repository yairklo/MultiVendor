from sqlalchemy import event, inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, with_loader_criteria
from sqlalchemy.sql.visitors import traverse
import redis.asyncio as redis
from app.core.config import settings
from app.db.tenant_context import (
    TenantContextRequired,
    TenantIsolationError,
    get_current_tenant_id,
    is_unscoped,
)
from app.db.tenant_scope import TenantScoped

engine = create_async_engine(settings.DATABASE_URL, echo=False)


class TenantAwareSyncSession(Session):
    pass


class TenantAwareSession(AsyncSession):
    sync_session_class = TenantAwareSyncSession


AsyncSessionLocal = async_sessionmaker(engine, class_=TenantAwareSession, expire_on_commit=False)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def _is_scoped_class(cls) -> bool:
    return isinstance(cls, type) and issubclass(cls, TenantScoped) and cls is not TenantScoped


def _scoped_table_names() -> set[str]:
    from app.db.base_class import Base

    names: set[str] = set()
    for mapper in Base.registry.mappers:
        if _is_scoped_class(mapper.class_):
            names.add(mapper.local_table.name)
    return names


def _statement_involves_tenant_scoped(statement) -> bool:
    scoped_tables = _scoped_table_names()
    found = False

    def visit_table(table):
        nonlocal found
        if getattr(table, "name", None) in scoped_tables:
            found = True

    try:
        traverse(statement, {}, {"table": visit_table})
    except Exception:
        pass
    if found:
        return True

    descriptions = getattr(statement, "column_descriptions", None) or []
    for desc in descriptions:
        entity = desc.get("entity")
        cls = entity if isinstance(entity, type) else getattr(entity, "class_", None)
        if cls is None:
            insp = sa_inspect(entity, raiseerr=False) if entity is not None else None
            cls = getattr(insp, "class_", None) if insp is not None else None
        if _is_scoped_class(cls):
            return True
    return False


@event.listens_for(TenantAwareSyncSession, "do_orm_execute")
def _apply_tenant_criteria(execute_state):
    if execute_state.is_column_load:
        return
    if is_unscoped() or execute_state.execution_options.get("tenant_unscoped"):
        return

    tenant_id = get_current_tenant_id()
    involves = _statement_involves_tenant_scoped(execute_state.statement)

    if involves and tenant_id is None:
        raise TenantContextRequired(
            "Tenant-scoped query executed without a bound tenant. "
            "Bind via get_current_tenant, or wrap platform-plane work in unscoped()."
        )

    if tenant_id is None:
        return

    from app.db.base_class import Base

    options = [
        with_loader_criteria(
            mapper.class_,
            mapper.class_.tenant_id == tenant_id,
            include_aliases=True,
        )
        for mapper in Base.registry.mappers
        if _is_scoped_class(mapper.class_)
    ]
    if options:
        execute_state.statement = execute_state.statement.options(*options)


@event.listens_for(TenantAwareSyncSession, "before_flush")
def _stamp_and_guard_writes(session, flush_context, instances):
    tenant_id = get_current_tenant_id()
    allow_cross = is_unscoped()

    for obj in session.new:
        if not isinstance(obj, TenantScoped):
            continue
        obj_tid = getattr(obj, "tenant_id", None)
        if allow_cross:
            if obj_tid is None:
                raise TenantContextRequired(
                    f"{obj.__class__.__name__} insert on the platform plane requires an explicit tenant_id"
                )
            continue
        if tenant_id is None:
            raise TenantContextRequired(
                f"{obj.__class__.__name__} insert requires a bound tenant or unscoped()"
            )
        if obj_tid is None:
            obj.tenant_id = tenant_id
        elif int(obj_tid) != int(tenant_id):
            raise TenantIsolationError(
                f"Refusing to insert {obj.__class__.__name__} for tenant {obj_tid} while bound to {tenant_id}"
            )

    for obj in session.dirty:
        if not isinstance(obj, TenantScoped):
            continue
        hist = sa_inspect(obj).attrs.tenant_id.history
        if hist.has_changes() and not allow_cross:
            raise TenantIsolationError(f"Refusing to reassign tenant_id on {obj.__class__.__name__}")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


get_tenant_db = get_db


async def get_redis():
    yield redis_client
