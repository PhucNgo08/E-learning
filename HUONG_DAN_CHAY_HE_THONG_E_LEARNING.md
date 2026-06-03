# HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY HỆ THỐNG E-LEARNING

## 1. Yêu cầu môi trường

Máy cần cài sẵn:

- Python 3.12
- MySQL Server
- Visual Studio Code hoặc Cursor
- Git
- Trình duyệt Chrome/Edge

---

## 2. Mở thư mục dự án

Mở terminal tại thư mục backend của dự án:

```bash
cd D:\KhoaHoctructuyen\KHoaHocOnline\backend
```

Hoặc mở trực tiếp thư mục `backend` bằng VS Code/Cursor.

---

## 3. Tạo môi trường ảo Python

### Windows PowerShell

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

Khi kích hoạt thành công, terminal sẽ hiện dạng:

```bash
(.venv) PS D:\KhoaHoctructuyen\KHoaHocOnline\backend>
```

---

## 4. Cài đặt thư viện

Cài thư viện từ file `requirements.txt`:

```bash
pip install -r requirements.txt
```

Nếu dùng kiểm thử tự động bằng Playwright, chạy thêm:

```bash
playwright install
```

---

## 5. Cấu hình cơ sở dữ liệu MySQL

Tạo database trong MySQL:

```sql
CREATE DATABASE e_learning CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Sau đó import file SQL của hệ thống vào database `e_learning`.

Ví dụ nếu có file `e_learning.sql`:

```bash
mysql -u root -p e_learning < e_learning.sql
```

---

## 6. Cấu hình file .env

Tạo hoặc kiểm tra file `.env` trong thư mục `backend`.

Ví dụ cấu hình:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=e_learning

SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Lưu ý: thay `your_password` bằng mật khẩu MySQL trên máy.

---
## . Chạy tài khoản admin
```bash
PS D:\KhoaHoctructuyen\KHoaHocOnline\backend> py -m app.services.common.create_admin   
```
## 7. Chạy hệ thống

Trong thư mục `backend`, chạy:

```bash
uvicorn app.main:app --reload
```

Nếu chạy thành công, terminal sẽ hiện:

```bash
Uvicorn running on http://127.0.0.1:8000
```

Mở trình duyệt và truy cập:

```text
http://127.0.0.1:8000
```

---

## 8. Một số đường dẫn thường dùng

```text
Trang chủ:
http://127.0.0.1:8000

Trang đăng nhập:
http://127.0.0.1:8000/login

Trang quản trị viên:
http://127.0.0.1:8000/admin/dashboard

Trang giảng viên:
http://127.0.0.1:8000/teacher/dashboard

Trang sinh viên:
http://127.0.0.1:8000/student/dashboard
```

---

## 9. Tài khoản kiểm thử

Điền theo dữ liệu demo của nhóm:

```text
Admin:
Email/Tài khoản: admin@example.com
Mật khẩu: 123456

Giảng viên:
Email/Tài khoản: teacher@example.com
Mật khẩu: 123456

Sinh viên:
Email/Tài khoản: student@example.com
Mật khẩu: 123456
```

Nếu tài khoản trong database khác, cần thay lại đúng theo dữ liệu demo.

---

## 10. Chạy kiểm thử tự động

Nếu project có thư mục test, chạy:

```bash
pytest
```

Nếu có test Playwright riêng, chạy theo file test của nhóm, ví dụ:

```bash
pytest tests/
```

---

## 11. Lỗi thường gặp và cách xử lý

### Lỗi thiếu thư viện

Nếu gặp lỗi:

```text
ModuleNotFoundError: No module named 'tên_thư_viện'
```

Cài thư viện bị thiếu:

```bash
pip install tên_thư_viện
```

---

### Lỗi không kết nối được MySQL

Kiểm tra:

- MySQL Server đã bật chưa
- Tên database đúng chưa
- User/password trong `.env` đúng chưa
- Database đã import dữ liệu chưa

---

### Lỗi Jinja2 TemplateNotFound

Kiểm tra:

- File HTML có tồn tại đúng thư mục không
- Đường dẫn template trong code có đúng không
- Tên file có bị sai chữ hoa/thường không

---

### Lỗi port 8000 đã được sử dụng

Chạy bằng port khác:

```bash
uvicorn app.main:app --reload --port 8001
```

Sau đó truy cập:

```text
http://127.0.0.1:8001
```

---

## 12. Ghi chú khi nộp đồ án

Nên nộp kèm:

- Source code
- File database SQL
- File `.env.example`
- File `requirements.txt`
- File hướng dẫn chạy này
- Báo cáo PDF
- Poster PDF
- Slide thuyết trình

Không nên nộp thư mục `.venv`, `__pycache__`, `.pytest_cache`, file log hoặc dữ liệu tạm.


Thông tin thẻ test
#	Thông tin thẻ	Ghi chú
1	
Ngân hàng: NCB
Số thẻ: 9704198526191432198
Tên chủ thẻ:NGUYEN VAN A
Ngày phát hành:07/15
Mật khẩu OTP:123456
Thành công
2	
Ngân hàng: NCB
Số thẻ: 9704195798459170488
Tên chủ thẻ:NGUYEN VAN A
Ngày phát hành:07/15
Thẻ không đủ số dư
3	
Ngân hàng: NCB
Số thẻ: 9704192181368742
Tên chủ thẻ:NGUYEN VAN A
Ngày phát hành:07/15
Thẻ chưa kích hoạt
4	
Ngân hàng: NCB
Số thẻ: 9704193370791314
Tên chủ thẻ:NGUYEN VAN A
Ngày phát hành:07/15
Thẻ bị khóa
5	
Ngân hàng: NCB
Số thẻ: 9704194841945513
Tên chủ thẻ:NGUYEN VAN A
Ngày phát hành:07/15
Thẻ bị hết hạn
6	
Loại thẻ quốc tếVISA (No 3DS)
Số thẻ: 4456530000001005
CVC/CVV: 123
Tên chủ thẻ:NGUYEN VAN A
Ngày hết hạn:12/26
Email:test@gmail.com
Địa chỉ:22 Lang Ha
Thành phố:Ha Noi
Thành công
7	
Loại thẻ quốc tếVISA (3DS)
Số thẻ: 4456530000001096
CVC/CVV: 123
Tên chủ thẻ:NGUYEN VAN A
Ngày hết hạn:12/26
Email:test@gmail.com
Địa chỉ:22 Lang Ha
Thành phố:Ha Noi
Thành công
8	
Loại thẻ quốc tếMasterCard (No 3DS)
Số thẻ: 5200000000001005
CVC/CVV: 123
Tên chủ thẻ:NGUYEN VAN A
Ngày hết hạn:12/26
Email:test@gmail.com
Địa chỉ:22 Lang Ha
Thành phố:Ha Noi
Thành công
9	
Loại thẻ quốc tếMasterCard (3DS)
Số thẻ: 5200000000001096
CVC/CVV: 123
Tên chủ thẻ:NGUYEN VAN A
Ngày hết hạn:12/26
Email:test@gmail.com
Địa chỉ:22 Lang Ha
Thành phố:Ha Noi
Thành công
10	
Loại thẻ quốc tếJCB (No 3DS)
Số thẻ: 3337000000000008
CVC/CVV: 123
Tên chủ thẻ:NGUYEN VAN A
Ngày hết hạn:12/26
Email:test@gmail.com
Địa chỉ:22 Lang Ha
Thành phố:Ha Noi
Thành công
11	
Loại thẻ quốc tếJCB (3DS)
Số thẻ: 3337000000200004
CVC/CVV: 123
Tên chủ thẻ:NGUYEN VAN A
Ngày hết hạn:12/24
Email:test@gmail.com
Địa chỉ:22 Lang Ha
Thành phố:Ha Noi
Thành công
12	
Loại thẻ ATM nội địaNhóm Bank qua NAPAS
Số thẻ: 9704000000000018
Số thẻ: 9704020000000016
Tên chủ thẻ:NGUYEN VAN A
Ngày phát hành:03/07
OTP:otp
Thành công
12	
Loại thẻ ATM nội địaEXIMBANK
Số thẻ: 9704310005819191
Tên chủ thẻ:NGUYEN VAN A
Ngày hết hạn:10/26