from pydantic_settings import BaseSettings
from urllib.parse import quote_plus

class Settings(BaseSettings):
    # 🗄️ Cấu hình Database
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    # 🤖 Thêm API Key cho Chat AI (Google Gemini)
    GOOGLE_API_KEY: str | None = None   # 👈 thêm dòng này

    @property
    def DATABASE_URL(self) -> str:
        # Encode password để tránh lỗi khi chứa ký tự đặc biệt (@, %, ...)
        safe_password = quote_plus(self.DB_PASS)
        return (
            f"mysql+pymysql://{self.DB_USER}:{safe_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"     # Tự động đọc file .env
        extra = "ignore"      # 👈 Bỏ qua biến .env thừa, tránh lỗi pydantic
