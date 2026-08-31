import logging

from app.core.config import settings


def configure_observability() -> None:
    """Called once at app startup (see main.py). Two independent pieces:

    1. Logging: without this, Python's root logger has no handler attached,
       so every `logger.info(...)`/`logger.warning(...)` call in the app
       (e.g. email_service's console-log fallback) is silently dropped --
       only logger.exception/critical calls happen to clear the WARNING
       threshold of the "handler of last resort" and print anything at all.
    2. Sentry: a no-op unless SENTRY_DSN is set, same "zero external calls
       until configured" pattern as PAYMENT_PROVIDER/EMAIL_PROVIDER.
    """
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not settings.SENTRY_DSN:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        # Sampling, not "log every request" -- fine for a course-scale
        # deployment; tune down for real production traffic volume.
        traces_sample_rate=0.1,
    )
