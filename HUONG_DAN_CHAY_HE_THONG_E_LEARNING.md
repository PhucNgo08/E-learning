HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY HỆ THỐNG E-LEARNING

1. Yêu cầu môi trường

Máy tính cần cài đặt các phần mềm sau:

* Python 3.12
* MySQL Server
* Visual Studio Code hoặc Cursor
* Git
* Trình duyệt Chrome hoặc Microsoft Edge
* Node.js nếu chạy kiểm thử tự động bằng Playwright

2. Mở thư mục dự án

Mở terminal tại thư mục backend của dự án:

cd D:\KhoaHoctructuyen\KHoaHocOnline\backend

3. Tạo và kích hoạt môi trường ảo Python

python -m venv .venv
..venv\Scripts\activate

Khi kích hoạt thành công, terminal sẽ hiển thị tiền tố (.venv).

4. Cài đặt thư viện backend

pip install -r requirements.txt

5. Tạo và import cơ sở dữ liệu MySQL

Tạo database:

CREATE DATABASE e_learning CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

Sau đó import file e_learning.sql vào database e_learning bằng MySQL Workbench, DBeaver hoặc dòng lệnh:

mysql -u root -p e_learning < e_learning.sql

6. Cấu hình file .env

Tạo hoặc kiểm tra file .env trong thư mục backend:

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=your_mysql_password
DB_NAME=e_learning

APP_ENV=development
DEBUG=true
SESSION_SECRET_KEY=your_secret_key

Lưu ý: thay your_mysql_password bằng mật khẩu MySQL trên máy đang chạy.

7. Tạo tài khoản quản trị bắt buột

py -m app.services.common.create_admin

8. Chạy hệ thống

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

Sau khi chạy thành công, mở trình duyệt và truy cập:

http://127.0.0.1:8000

9. Một số đường dẫn thường dùng

Trang chủ:
http://127.0.0.1:8000

Trang đăng nhập:
http://127.0.0.1:8000/auth/login

Trang quản trị viên:
http://127.0.0.1:8000/admin/dashboard

Trang giảng viên:
http://127.0.0.1:8000/teacher/dashboard

Trang sinh viên:
http://127.0.0.1:8000/student/dashboard

10. Tài khoản kiểm thử

Admin:
Tài khoản: admin

Giảng viên:
Tài khoản: gv_an
Tài khoản: gv_binh

Sinh viên:
Tài khoản: sv001
Tài khoản: sv002
Tài khoản: sv003
Tài khoản: sv004
Tài khoản: sv005
Tài khoản: sv006

Lưu ý: mật khẩu kiểm thử được cung cấp riêng trong dữ liệu demo hoặc khi trình bày demo, không nên ghi mật khẩu thật trong bản nộp công khai.

11. Chạy kiểm thử tự động bằng Playwright

Trước khi chạy test, cần đảm bảo backend đang chạy tại http://127.0.0.1:8000.

cd D:\KhoaHoctructuyen\KHoaHocOnline\tests\e2e
npm install
npx playwright install chromium
npx playwright test --headed

12. Một số lỗi thường gặp

Lỗi thiếu thư viện:
Cài lại thư viện bằng lệnh pip install -r requirements.txt hoặc cài riêng thư viện bị thiếu.

Lỗi không kết nối được MySQL:
Kiểm tra MySQL Server đã bật chưa, tên database có đúng không, thông tin DB_HOST, DB_PORT, DB_USER, DB_PASS và DB_NAME trong file .env có đúng không.

Lỗi Jinja2 TemplateNotFound:
Kiểm tra file HTML có tồn tại đúng thư mục không, tên file có đúng chữ hoa/chữ thường không và đường dẫn template trong code có chính xác không.

Lỗi port 8000 đã được sử dụng:
Chạy bằng port khác:

python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

13. Ghi chú khi nộp đồ án

Nên nộp kèm:

* Mã nguồn hệ thống
* File cơ sở dữ liệu e_learning.sql
* File .env.example
* File requirements.txt
* File hướng dẫn cài đặt và chạy hệ thống
* Báo cáo PDF
* Poster PDF
* Slide thuyết trình
* Video demo nếu có

Không nên nộp các thư mục hoặc file tạm như .venv, **pycache**, .pytest_cache, file log, file cache hoặc dữ liệu cá nhân.
