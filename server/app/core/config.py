from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "super_secret_random_string_change_me_in_prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "rootpassword"
    DB_NAME: str = "multivendor_dev"
    DATABASE_URL: str = "mysql+aiomysql://root:rootpassword@127.0.0.1:3306/multivendor_dev"
    
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    
    STORAGE_TYPE: str = "local"
    UPLOAD_DIR: str = "./uploads"

    # "console" (default) logs the email instead of sending it -- zero
    # external calls until configured, same pattern as PAYMENT_PROVIDER.
    # "smtp" sends for real via aiosmtplib using the SMTP_* settings below.
    EMAIL_PROVIDER: str = "console"
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: str | None = None

    # Base URL of the Next.js frontend, used to build links (e.g. password
    # reset) that get emailed to users -- must not have a trailing slash.
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Left unset by default: the AI layout/product assistant runs in a
    # deterministic mock mode with no external calls until a real key is set.
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    # When true, product/logo/page image URLs are fetched before save and
    # rejected unless they actually return an image. Tests turn this off so
    # placeholder https://images.example.com/... URLs don't hit the network.
    VERIFY_REMOTE_IMAGE_URLS: bool = True

    # "mock" (default) keeps the existing dev-only instant-pay behavior with
    # zero external calls. "stripe" routes /pay through a real PaymentIntent
    # and only marks an order paid once the Stripe webhook confirms it -- see
    # app/services/payments/. Secret keys stay server-side only;
    # STRIPE_PUBLISHABLE_KEY is the one Stripe key that's meant to be public
    # (the frontend needs it to mount Stripe Elements).
    PAYMENT_PROVIDER: str = "mock"
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_CURRENCY: str = "ils"

    # Symmetric key (Fernet, url-safe base64, 32 bytes) encrypting per-tenant
    # courier credentials (TenantShippingConfig.credentials_encrypted) at
    # rest -- see app/core/crypto.py. Left unset by default: any attempt to
    # actually encrypt/decrypt without it raises rather than silently storing
    # plaintext. Generate one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    SHIPPING_CREDENTIALS_ENCRYPTION_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
