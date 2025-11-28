import mysql.connector # type: ignore
from uuid import uuid4
import bcrypt
from datetime import datetime

# =====================================================
# ⚙️ Thông tin kết nối MySQL
# =====================================================
DB_HOST = "localhost"
DB_PORT = 3306  # đổi nếu bạn dùng port khác (mặc định 3306)
DB_USER = "root"
DB_PASS = "p882004N@@Gg"   # mật khẩu MySQL
DB_NAME = "e_learning"

# =====================================================
# 🧩 Hàm kết nối tới cơ sở dữ liệu
# =====================================================
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )


# =====================================================
# 👑 Tạo hoặc khôi phục tài khoản admin
# =====================================================
def ensure_admin_account():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1️⃣ Kiểm tra xem admin có tồn tại không
        cursor.execute("SELECT * FROM users WHERE username = 'admin' LIMIT 1;")
        admin = cursor.fetchone()

        # 2️⃣ Nếu chưa có -> tạo mới
        if not admin:
            print("⚙️ Không tìm thấy admin, tạo mới...")
            password = "admin@123"
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, full_name, role, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                str(uuid4()), "admin", "admin@school.edu.vn", hashed_password,
                "Quản trị hệ thống", "admin", "active"
            ))
            conn.commit()
            print("✅ Đã tạo tài khoản admin mới (mật khẩu: admin@123)")
            return

        # 3️⃣ Nếu tồn tại nhưng bị vô hiệu hóa → kích hoạt lại
        if admin["status"] != "active":
            cursor.execute("""
                UPDATE users SET status = 'active', updated_at = NOW()
                WHERE username = 'admin'
            """)
            conn.commit()
            print("🔓 Đã kích hoạt lại tài khoản admin.")

        # 4️⃣ Kiểm tra bảng bảo mật (security_settings)
        cursor.execute("""
            SELECT * FROM security_settings WHERE user_id = %s
        """, (admin["id"],))
        security = cursor.fetchone()

        if not security:
            cursor.execute("""
                INSERT INTO security_settings (id, user_id, two_factor_enabled, failed_login_attempts, account_locked_until)
                VALUES (%s, %s, 0, 0, NULL)
            """, (str(uuid4()), admin["id"]))
            print("✅ Đã tạo bản ghi bảo mật cho admin.")
        else:
            # reset lại nếu bị khóa tạm thời
            cursor.execute("""
                UPDATE security_settings
                SET failed_login_attempts = 0,
                    account_locked_until = NULL
                WHERE user_id = %s
            """, (admin["id"],))
            print("🔁 Đã xóa trạng thái khóa tạm thời của admin.")

        conn.commit()
        print("🎯 Admin hiện đang hoạt động bình thường!")

    except mysql.connector.Error as err:
        print(f"❌ Lỗi MySQL: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("🔒 Kết nối MySQL đã đóng.")


# =====================================================
# 🔐 Hàm xác thực đăng nhập kiểm tra nhanh
# =====================================================
def quick_login_check():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        user = cursor.fetchone()

        if not user:
            print("❌ Không tìm thấy tài khoản admin để kiểm tra.")
            return

        entered_password = "admin@123"
        if bcrypt.checkpw(entered_password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            print("✅ Đăng nhập thử admin thành công (mật khẩu đúng).")
        else:
            print("⚠️ Sai mật khẩu admin hoặc đã đổi mật khẩu khác.")

    except mysql.connector.Error as err:
        print(f"❌ Lỗi MySQL: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =====================================================
# 🚀 CHẠY TRỰC TIẾP
# =====================================================
if __name__ == "__main__":
    print("=== 🧩 KIỂM TRA / KHỞI TẠO ADMIN ACCOUNT ===")
    ensure_admin_account()
    quick_login_check()
