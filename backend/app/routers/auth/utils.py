import jwt
from datetime import datetime, timedelta
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# 👇 Cấu hình gửi email thật (dùng Gmail hoặc mail server riêng)
from fastapi_mail import ConnectionConfig

conf = ConnectionConfig(
    MAIL_USERNAME="your_email@gmail.com",
    MAIL_PASSWORD="your_app_password",
    MAIL_FROM="your_email@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,   # ✅ Thay MAIL_TLS → MAIL_STARTTLS
    MAIL_SSL_TLS=False,   # ✅ Thay MAIL_SSL → MAIL_SSL_TLS
    USE_CREDENTIALS=True
)


SECRET_KEY = "mysecretkey123"
ALGORITHM = "HS256"

# Tạo mã reset password
def generate_reset_token(email: str):
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Gửi email (bạn có thể test tạm bằng print nếu chưa có SMTP)
def send_reset_email(email: str, link: str):
    subject = "🔒 Đặt lại mật khẩu - E-Learning Portal"
    body = f"""
    Xin chào,

    Bạn vừa yêu cầu đặt lại mật khẩu. Hãy truy cập liên kết sau để đổi mật khẩu:
    {link}

    Liên kết này sẽ hết hạn sau 1 giờ.
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
        import asyncio
        asyncio.create_task(fm.send_message(message))
        print(f"📧 Email đặt lại mật khẩu đã gửi đến {email}")
    except Exception as e:
        print(f"❌ Lỗi gửi email: {e}")
