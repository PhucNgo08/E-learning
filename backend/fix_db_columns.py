from app.database.connection import engine
from sqlalchemy import text

def add_missing_columns():
    print("🔄 Đang kiểm tra và thêm cột thiếu vào bảng 'users'...")
    
    # Danh sách các cột cần thêm (dựa trên log lỗi của bạn)
    columns_to_add = [
        ("total_assignments_submitted", "INT DEFAULT 0"),
        ("total_assignments_graded", "INT DEFAULT 0"),
        ("total_assignments_created", "INT DEFAULT 0"),
        ("total_learning_time", "INT DEFAULT 0")
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            try:
                # Câu lệnh SQL để thêm cột
                sql = text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")
                conn.execute(sql)
                conn.commit()
                print(f"✅ Đã thêm cột: {col_name}")
            except Exception as e:
                # Mã lỗi 1060 là "Duplicate column name" (Cột đã tồn tại)
                if "1060" in str(e):
                    print(f"⚠️ Cột '{col_name}' đã tồn tại -> Bỏ qua.")
                else:
                    # In lỗi khác nếu có (nhưng thường là do cột đã có rồi)
                    print(f"ℹ️ Thông báo về cột '{col_name}': {e}")

    print("\n🏁 Hoàn tất sửa lỗi Database!")

if __name__ == "__main__":
    add_missing_columns()