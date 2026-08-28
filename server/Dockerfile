FROM python:3.12-slim AS base

# mysqlclient/cryptography/pillow need build headers to compile from sdist on
# some platforms even though this project mostly uses prebuilt wheels --
# cheap to keep, expensive to debug the one time a wheel is missing.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# The vendored israel-shipping-sdk package (installed editable via
# requirements.txt as `-e ../packages/israel-shipping-sdk`) must exist at
# that relative path before pip install runs.
COPY packages/israel-shipping-sdk /packages/israel-shipping-sdk
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ .

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/uploads \
    && chown -R appuser:appuser /app /packages
USER appuser

EXPOSE 8000

# --proxy-headers: the app sits behind Caddy (see docker-compose.prod.yml),
# so it needs to trust X-Forwarded-* for request.client / scheme to be
# correct (e.g. the rate limiter's get_remote_address, HTTPS-aware redirects).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
