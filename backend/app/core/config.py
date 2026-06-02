from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================
    # App
    # =========================
    APP_NAME: str = "E-Learning Platform"
    APP_VERSION: str = "1.2.3"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # =========================
    # Database
    # =========================
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    DB_ECHO: bool = False
    DB_POOL_PRE_PING: bool = True
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # =========================
    # Session / Security
    # =========================
    SESSION_SECRET_KEY: str = Field(
        default="dev-insecure-change-me",
        description="Secret key for SessionMiddleware",
    )
    SESSION_EXPIRE_MINUTES: int = 60
    SESSION_COOKIE_NAME: str = "kh_session"
    SESSION_SAME_SITE: str = "lax"
    SESSION_HTTPS_ONLY: bool | None = None

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # =========================
    # CORS
    # =========================
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # =========================
    # AI / OAuth
    # =========================
    GOOGLE_API_KEY: str | None = None
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    MICROSOFT_CLIENT_ID: str | None = None
    MICROSOFT_CLIENT_SECRET: str | None = None

    # =========================
    # File / Upload
    # =========================
    UPLOAD_DIR: str = "backend/uploads"

    # =========================
    # Wallet / VietQR
    # =========================
    VIETQR_BANK_ID: str = "sacombank"
    VIETQR_BANK_NAME: str = "Sacombank"
    VIETQR_ACCOUNT_NO: str = ""
    VIETQR_ACCOUNT_NAME: str = ""
    VIETQR_TEMPLATE: str = "compact2"

    MIN_TOPUP_AMOUNT: int = 10000
    MAX_TOPUP_AMOUNT: int = 50000000

    # =========================
    # VNPay Sandbox
    # =========================
    VNPAY_TMN_CODE: str = ""
    VNPAY_HASH_SECRET: str = ""
    VNPAY_PAYMENT_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    VNPAY_RETURN_URL: str = "http://127.0.0.1:8000/student/cart/vnpay-return"
    VNPAY_IPN_URL: str = "http://127.0.0.1:8000/student/cart/vnpay-ipn"
    VNPAY_VERSION: str = "2.1.0"
    VNPAY_COMMAND: str = "pay"
    VNPAY_CURRENCY: str = "VND"
    VNPAY_LOCALE: str = "vn"
    VNPAY_ORDER_TYPE: str = "other"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "APP_NAME",
        "APP_ENV",
        "DB_HOST",
        "DB_USER",
        "DB_PASS",
        "DB_NAME",
        "SESSION_SECRET_KEY",
        "ALGORITHM",
        "CORS_ALLOW_ORIGINS",
        "GOOGLE_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "MICROSOFT_CLIENT_ID",
        "MICROSOFT_CLIENT_SECRET",
        "UPLOAD_DIR",
        "VIETQR_BANK_ID",
        "VIETQR_BANK_NAME",
        "VIETQR_ACCOUNT_NO",
        "VIETQR_ACCOUNT_NAME",
        "VIETQR_TEMPLATE",
        "VNPAY_TMN_CODE",
        "VNPAY_HASH_SECRET",
        "VNPAY_PAYMENT_URL",
        "VNPAY_RETURN_URL",
        "VNPAY_IPN_URL",
        "VNPAY_VERSION",
        "VNPAY_COMMAND",
        "VNPAY_CURRENCY",
        "VNPAY_LOCALE",
        "VNPAY_ORDER_TYPE",
        mode="before",
    )
    @classmethod
    def strip_string_values(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            return value.strip()
        return value

    @property
    def DATABASE_URL(self) -> str:
        safe_password = quote_plus(self.DB_PASS)
        return (
            f"mysql+pymysql://{self.DB_USER}:{safe_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() in {"prod", "production"}

    @property
    def session_max_age_seconds(self) -> int:
        return self.SESSION_EXPIRE_MINUTES * 60

    @property
    def session_https_only(self) -> bool:
        if self.SESSION_HTTPS_ONLY is None:
            return self.is_production
        return self.SESSION_HTTPS_ONLY

    @property
    def cors_allow_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.CORS_ALLOW_ORIGINS.split(",")
            if item.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()