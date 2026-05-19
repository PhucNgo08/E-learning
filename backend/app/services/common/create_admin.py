from uuid import uuid4

import bcrypt
import pymysql
from pymysql.cursors import DictCursor

from app.core.config import Settings

# =====================================================
# CẤU HÌNH DB - đọc từ .env, không hard-code mật khẩu trong code
# =====================================================
settings = Settings()

# =====================================================
# CẤU HÌNH ADMIN MẶC ĐỊNH
# =====================================================
ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@school.edu.vn"
ADMIN_FULL_NAME = "Quản trị hệ thống"
ADMIN_PASSWORD = "admin@123"

ADMIN_ROLE_CODE = "admin"
ADMIN_ROLE_NAME = "Quản trị viên"


# =====================================================
# KẾT NỐI DB
# =====================================================
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


# =====================================================
# BCRYPT
# =====================================================
def make_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_valid_bcrypt_hash(value: str | None) -> bool:
    if not value:
        return False

    try:
        bcrypt.checkpw(b"__probe__", value.encode("utf-8"))
        return True
    except ValueError:
        return False
    except Exception:
        return False


# =====================================================
# ROLE ADMIN
# =====================================================
def ensure_admin_role(cursor) -> str:
    cursor.execute(
        "SELECT id FROM roles WHERE role_code = %s LIMIT 1",
        (ADMIN_ROLE_CODE,),
    )
    role = cursor.fetchone()

    if role:
        return role["id"]

    role_id = str(uuid4())
    cursor.execute(
        """
        INSERT INTO roles (id, role_code, role_name, description, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        """,
        (
            role_id,
            ADMIN_ROLE_CODE,
            ADMIN_ROLE_NAME,
            "Toàn quyền hệ thống",
        ),
    )
    print("✅ Đã tạo role admin.")
    return role_id


# =====================================================
# USER PROFILE ADMIN
# =====================================================
def ensure_admin_profile(cursor, user_id: str):
    cursor.execute(
        "SELECT user_id FROM user_profiles WHERE user_id = %s LIMIT 1",
        (user_id,),
    )
    profile = cursor.fetchone()

    if profile:
        cursor.execute(
            """
            UPDATE user_profiles
            SET full_name = %s,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (ADMIN_FULL_NAME, user_id),
        )
        return

    cursor.execute(
        """
        INSERT INTO user_profiles (
            user_id, full_name, phone, avatar_url, date_of_birth, gender, created_at, updated_at
        )
        VALUES (%s, %s, NULL, NULL, NULL, NULL, NOW(), NOW())
        """,
        (user_id, ADMIN_FULL_NAME),
    )
    print("✅ Đã tạo hồ sơ admin.")


# =====================================================
# SECURITY SETTINGS ADMIN
# =====================================================
def ensure_admin_security(cursor, user_id: str):
    cursor.execute(
        "SELECT id FROM security_settings WHERE user_id = %s LIMIT 1",
        (user_id,),
    )
    sec = cursor.fetchone()

    if not sec:
        cursor.execute(
            """
            INSERT INTO security_settings (
                id, user_id, two_factor_enabled, last_password_change,
                failed_login_attempts, account_locked_until, created_at, updated_at
            )
            VALUES (%s, %s, 0, NOW(), 0, NULL, NOW(), NOW())
            """,
            (str(uuid4()), user_id),
        )
        print("✅ Đã tạo security_settings cho admin.")
        return

    cursor.execute(
        """
        UPDATE security_settings
        SET failed_login_attempts = 0,
            account_locked_until = NULL,
            updated_at = NOW()
        WHERE user_id = %s
        """,
        (user_id,),
    )
    print("🔁 Đã mở khóa admin nếu trước đó bị khóa.")


# =====================================================
# GÁN ROLE ADMIN
# =====================================================
def ensure_admin_user_role(cursor, user_id: str, role_id: str):
    cursor.execute(
        """
        SELECT 1
        FROM user_roles
        WHERE user_id = %s AND role_id = %s
        LIMIT 1
        """,
        (user_id, role_id),
    )
    row = cursor.fetchone()

    if row:
        return

    cursor.execute(
        """
        INSERT INTO user_roles (user_id, role_id, assigned_at)
        VALUES (%s, %s, NOW())
        """,
        (user_id, role_id),
    )
    print("✅ Đã gán role admin cho tài khoản admin.")


# =====================================================
# TẠO / KHÔI PHỤC ADMIN
# =====================================================
def ensure_admin_account():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        role_id = ensure_admin_role(cursor)

        cursor.execute(
            """
            SELECT id, username, email, password_hash, status
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            (ADMIN_USERNAME,),
        )
        admin = cursor.fetchone()

        # 1. Chưa có admin -> tạo mới
        if not admin:
            print("⚙️ Không tìm thấy admin, đang tạo mới...")

            admin_id = str(uuid4())
            new_hash = make_password_hash(ADMIN_PASSWORD)

            cursor.execute(
                """
                INSERT INTO users (
                    id, username, email, password_hash, status,
                    last_login, login_count, created_at, updated_at, deleted_at
                )
                VALUES (%s, %s, %s, %s, 'active', NULL, 0, NOW(), NOW(), NULL)
                """,
                (
                    admin_id,
                    ADMIN_USERNAME,
                    ADMIN_EMAIL,
                    new_hash,
                ),
            )

            ensure_admin_profile(cursor, admin_id)
            ensure_admin_security(cursor, admin_id)
            ensure_admin_user_role(cursor, admin_id, role_id)

            conn.commit()
            print(f"✅ Đã tạo admin mới. Mật khẩu mặc định: {ADMIN_PASSWORD}")
            return

        # 2. Đã có admin -> khôi phục
        admin_id = admin["id"]

        if str(admin.get("status", "")).strip().lower() != "active":
            cursor.execute(
                """
                UPDATE users
                SET status = 'active',
                    deleted_at = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (admin_id,),
            )
            print("🔓 Đã kích hoạt lại tài khoản admin.")

        # 3. Nếu hash cũ lỗi / giả -> reset về mật khẩu mặc định
        if not is_valid_bcrypt_hash(admin.get("password_hash")):
            new_hash = make_password_hash(ADMIN_PASSWORD)
            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (new_hash, admin_id),
            )
            print(f"🔑 Đã reset mật khẩu admin về: {ADMIN_PASSWORD}")

        ensure_admin_profile(cursor, admin_id)
        ensure_admin_security(cursor, admin_id)
        ensure_admin_user_role(cursor, admin_id, role_id)

        conn.commit()
        print("🎯 Tài khoản admin đã sẵn sàng sử dụng.")

    except pymysql.MySQLError as err:
        print(f"❌ Lỗi MySQL: {err}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("🔒 Đã đóng kết nối MySQL.")


# =====================================================
# KIỂM TRA ĐĂNG NHẬP NHANH
# =====================================================
def quick_login_check():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT password_hash FROM users WHERE username = %s LIMIT 1",
            (ADMIN_USERNAME,),
        )
        user = cursor.fetchone()

        if not user:
            print("❌ Không tìm thấy admin để kiểm tra.")
            return

        hashed = user["password_hash"]

        if not is_valid_bcrypt_hash(hashed):
            print("❌ password_hash của admin chưa hợp lệ.")
            return

        ok = bcrypt.checkpw(ADMIN_PASSWORD.encode("utf-8"), hashed.encode("utf-8"))

        if ok:
            print("✅ Kiểm tra đăng nhập thành công.")
            print(f"👤 Username: {ADMIN_USERNAME}")
            print(f"🔑 Password: {ADMIN_PASSWORD}")
        else:
            print("⚠️ Admin tồn tại nhưng mật khẩu hiện tại không phải mật khẩu mặc định.")

    except pymysql.MySQLError as err:
        print(f"❌ Lỗi MySQL: {err}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =====================================================
# CHẠY FILE
# =====================================================
if __name__ == "__main__":
    print("=== KIỂM TRA / KHỞI TẠO ADMIN ===")
    ensure_admin_account()
    quick_login_check()