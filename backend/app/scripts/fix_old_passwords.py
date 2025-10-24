import mysql.connector
import bcrypt

# ==========================
# ⚙️ Cấu hình kết nối MySQL
# ==========================
DB_HOST = "localhost"
DB_PORT = 3309           # Đổi nếu bạn dùng port khác
DB_USER = "root"
DB_PASS = "111004@"      # Mật khẩu MySQL của bạn
DB_NAME = "e_learning"

# ==========================
# 🔧 Đặt lại mật khẩu teacher & student
# ==========================
def reset_teacher_student_passwords():
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

        # 🔎 Lọc tất cả teacher & student
        cursor.execute("""
            SELECT id, username, role, password_hash 
            FROM users 
            WHERE role IN ('teacher', 'student')
        """)
        users = cursor.fetchall()

        count = 0
        for user_id, username, role, password_hash in users:
            # Nếu hash chưa phải bcrypt
            if not password_hash or not (password_hash.startswith("$2a$") or password_hash.startswith("$2b$")):
                new_hash = bcrypt.hashpw("123456".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = %s 
                    WHERE id = %s
                """, (new_hash, user_id))
                count += 1
                print(f"🔁 {role.upper()} {username}: reset mật khẩu → 123456 (bcrypt)")

        db.commit()
        print(f"✅ Đã cập nhật {count} tài khoản teacher/student sang bcrypt (mặc định 123456).")

    except mysql.connector.Error as err:
        print(f"❌ Lỗi MySQL: {err}")
    finally:
        if cursor: cursor.close()
        if db: db.close()
        print("🔒 Kết nối tới MySQL đã đóng.")

# ==========================
# 🚀 Chạy trực tiếp
# ==========================
if __name__ == "__main__":
    reset_teacher_student_passwords()
