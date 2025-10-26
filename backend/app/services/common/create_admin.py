import mysql.connector
from uuid import uuid4
import bcrypt

# ==========================
# ⚙️ Thông tin kết nối MySQL
# ==========================
DB_HOST = "localhost"
DB_PORT = 3309  # nếu bạn đang chạy MySQL trên port 3309
DB_USER = "root"
DB_PASS = "111004@"   # mật khẩu MySQL của bạn
DB_NAME = "e_learning"

# ==========================
# 🧩 Hàm tạo tài khoản admin
# ==========================
def create_admin_account():
    cursor = None
    db = None
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = db.cursor()

        password = "admin@123"
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        result = cursor.fetchone()

        if result[0] == 0:
            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, full_name, role, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (str(uuid4()), 'admin', 'admin@school.edu.vn', hashed_password, 'Quản trị hệ thống', 'admin', 'active'))
            db.commit()
            print("✅ Tài khoản admin đã được tạo thành công!")
        else:
            print("⚠️ Đã có tài khoản admin, không thể tạo thêm.")
        
    except mysql.connector.Error as err:
        print(f"❌ Lỗi: {err}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()
        print("🔒 Kết nối đến cơ sở dữ liệu đã được đóng.")


# ==========================
# 🔐 Hàm xác thực đăng nhập
# ==========================
def authenticate_user(username, entered_password):
    db = None
    cursor = None
    try:
        db = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = db.cursor()

        cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()

        if result:
            stored_hash = result[0]
            if bcrypt.checkpw(entered_password.encode('utf-8'), stored_hash.encode('utf-8')):
                print("✅ Đăng nhập thành công!")
                return True
            else:
                print("❌ Mật khẩu sai!")
                return False
        else:
            print("❌ Không tìm thấy tài khoản.")
            return False

    except mysql.connector.Error as err:
        print(f"❌ Lỗi: {err}")
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================
# 🚀 Chạy trực tiếp
# ==========================
if __name__ == "__main__":
    create_admin_account()
    authenticate_user("admin", "admin@123")
