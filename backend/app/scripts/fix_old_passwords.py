import bcrypt
import pymysql
from pymysql.cursors import DictCursor

from app.core.config import Settings


settings = Settings()
DEFAULT_PASSWORD = "123456"
TARGET_ROLES = ("teacher", "student")


def get_db_connection():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASS,
        database=settings.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def make_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_bcrypt_hash(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith(("$2a$", "$2b$", "$2y$"))


def reset_teacher_student_passwords():
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()

        placeholders = ", ".join(["%s"] * len(TARGET_ROLES))
        cursor.execute(
            f"""
            SELECT DISTINCT u.id, u.username, u.password_hash, r.role_code
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles r ON r.id = ur.role_id
            WHERE r.role_code IN ({placeholders})
            """,
            TARGET_ROLES,
        )
        users = cursor.fetchall()

        count = 0
        for user in users:
            if not is_bcrypt_hash(user.get("password_hash")):
                new_hash = make_password_hash(DEFAULT_PASSWORD)
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (new_hash, user["id"]),
                )
                count += 1
                print(
                    f"🔁 {user['role_code'].upper()} {user['username']}: "
                    f"reset mật khẩu mặc định → {DEFAULT_PASSWORD}"
                )

        db.commit()
        print(f"✅ Đã cập nhật {count} tài khoản teacher/student sang bcrypt.")

    except pymysql.MySQLError as err:
        if db:
            db.rollback()
        print(f"❌ Lỗi MySQL: {err}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
        print("🔒 Kết nối tới MySQL đã đóng.")


if __name__ == "__main__":
    reset_teacher_student_passwords()
