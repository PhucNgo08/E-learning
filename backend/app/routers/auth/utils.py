# app/routers/auth/utils.py
import os
import jwt
import asyncio
from datetime import datetime, timedelta
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import load_dotenv

# ============================================================
# ⚙️ 1️⃣ Load biến môi trường từ .env
# ============================================================
load_dotenv()

MAIL_USERNAME = os.getenv("MAIL_USERNAME", "your_email@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "your_app_password")
MAIL_FROM = os.getenv("MAIL_FROM", MAIL_USERNAME)
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# ============================================================
# 📧 2️⃣ Cấu hình FastAPI Mail
# ============================================================
conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=True,   # ✅ STARTTLS cho Gmail
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

# ============================================================
# 🔐 3️⃣ Tạo token đặt lại mật khẩu
# ============================================================
def generate_reset_token(email: str, expires_hours: int = 1) -> str:
    """Sinh JWT token đặt lại mật khẩu hợp lệ trong 1 giờ."""
    expire = datetime.utcnow() + timedelta(hours=expires_hours)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ============================================================
# 🧩 4️⃣ Giải mã & kiểm tra token
# ============================================================
def verify_reset_token(token: str) -> str | None:
    """Xác minh token, trả về email nếu hợp lệ."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        print("❌ Token đã hết hạn.")
        return None
    except jwt.InvalidTokenError:
        print("❌ Token không hợp lệ.")
        return None

# ============================================================
# 📬 5️⃣ Gửi email đặt lại mật khẩu
# ============================================================
async def send_reset_email(email: str, link: str):
    """Gửi email chứa liên kết khôi phục mật khẩu."""
    subject = "🔒 Đặt lại mật khẩu - E-Learning Portal"
    body = f"""
    Xin chào,

    Bạn vừa yêu cầu đặt lại mật khẩu. Hãy truy cập liên kết sau để đổi mật khẩu:
    {link}

    ⏳ Liên kết này sẽ hết hạn sau 1 giờ.
    Nếu bạn không yêu cầu, vui lòng bỏ qua email này.

    Trân trọng,
    Đội ngũ hỗ trợ E-Learning
    """

    try:
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=body,
            subtype="plain"
        )
        fm = FastMail(conf)
        await fm.send_message(message)
        print(f"📧 Email đặt lại mật khẩu đã gửi đến {email}")
    except Exception as e:
        print(f"⚠️ Lỗi gửi email: {e}\n➡️ In ra nội dung thay thế:")
        print("────────────────────────────────────────")
        print(body)
        print("────────────────────────────────────────")
