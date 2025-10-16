from pydantic_settings import BaseSettings  # ✅ ĐÚNG
# pip install pydantic-settings
from urllib.parse import quote_plus

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    @property
    def DATABASE_URL(self) -> str:
        # Encode password để tránh lỗi khi chứa ký tự đặc biệt (@, %, ...)
        safe_password = quote_plus(self.DB_PASS)
        return (
            f"mysql+pymysql://{self.DB_USER}:{safe_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"  # tự động đọc file .env ở root project
