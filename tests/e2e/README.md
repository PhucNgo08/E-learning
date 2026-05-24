# Playwright E2E — KHoaHocOnline

Kiểm tra giao diện các trang chính, form đăng nhập, menu admin / teacher / student và smoke test các route chính.

**Không sửa backend, không sửa frontend, không sửa database** — test chạy trên server FastAPI đang chạy sẵn.

---

## Yêu cầu

- Node.js 18+
- Server FastAPI đang chạy tại `http://127.0.0.1:8000`
- Tài khoản admin / teacher / student đã có trong MySQL
- File `.env` trong `tests/e2e` đã điền đúng tài khoản test

---

## Cài đặt lần đầu

```powershell
cd "D:\KhoaHoctructuyen\KHoaHocOnline\tests\e2e"
npm install
npx playwright install chromium
```

Nếu chưa có file `.env` thì tạo từ file mẫu:

```powershell
copy .env.example .env
```

Sau đó mở file `.env`:

```powershell
notepad .env
```

Nội dung `.env` nên có dạng:

```env
BASE_URL=http://127.0.0.1:8000

ADMIN_IDENTIFIER=admin
ADMIN_PASSWORD=admin@123

TEACHER_IDENTIFIER=gv_linh
TEACHER_PASSWORD=Teacher@123

STUDENT_IDENTIFIER=sv002
STUDENT_PASSWORD=123456@Az
```

> Lưu ý: Không push file `.env` lên GitHub vì có mật khẩu thật.

---

## Chạy backend

**Terminal 1 — Backend:**

```powershell
cd "D:\KhoaHoctructuyen\KHoaHocOnline\backend"
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Nếu báo port `8000` đang được dùng, hãy mở thử trình duyệt:

```text
http://127.0.0.1:8000
```

Nếu web lên được thì backend đã chạy rồi, không cần chạy lại.

---

## Chạy Playwright test

**Terminal 2 — Playwright:**

```powershell
cd "D:\KhoaHoctructuyen\KHoaHocOnline\tests\e2e"
npm test
```

Hoặc chạy có mở trình duyệt:

```powershell
npm run test:headed
```

---

## Lệnh hữu ích

| Lệnh | Mô tả |
|------|------|
| `npm test` | Chạy toàn bộ test dạng headless |
| `npm run test:headed` | Chạy toàn bộ test và mở browser |
| `npm run test:ui` | Mở Playwright UI mode |
| `npm run report` | Xem HTML report sau khi chạy |
| `npx playwright test login.spec.ts --headed --workers=1` | Chỉ test đăng nhập |
| `npx playwright test route-smoke.spec.ts --headed --workers=1` | Chỉ chạy route smoke test |

---

## Cấu trúc file

```text
tests/e2e/
├── playwright.config.ts   # Cấu hình Playwright, baseURL, workers
├── helpers/
│   ├── auth.ts            # loginAs, loginAsRole, đọc .env
│   ├── selectors.ts       # Selector theo template Jinja
│   ├── routes.ts          # Danh sách route smoke GET an toàn
│   └── smoke.ts           # smokeVisit kiểm tra status/body/URL
├── public.spec.ts         # Trang chủ, link đăng nhập
├── login.spec.ts          # Form login, redirect theo role
├── admin-menu.spec.ts     # Sidebar và điều hướng admin
├── teacher-menu.spec.ts   # Sidebar và điều hướng teacher
├── student-menu.spec.ts   # Sidebar và điều hướng student
└── route-smoke.spec.ts    # Smoke test toàn bộ route chính GET-only
```

---

## Chạy từng nhóm test

```powershell
npx playwright test public.spec.ts --headed --workers=1
npx playwright test login.spec.ts --headed --workers=1
npx playwright test admin-menu.spec.ts --headed --workers=1
npx playwright test teacher-menu.spec.ts --headed --workers=1
npx playwright test student-menu.spec.ts --headed --workers=1
npx playwright test route-smoke.spec.ts --headed --workers=1
```

---

## Route smoke test

`route-smoke.spec.ts` truy cập GET-only các trang list/manage chính.

| Nhóm | Số route | Ghi chú |
|------|----------|---------|
| Public | 2 | `/`, `/auth/login` |
| Admin | 29 | Dashboard, users, courses, quiz, settings... |
| Teacher | 18 | Dashboard, courses, assignments, statistics... |
| Student | 21 | Dashboard, course, wallet, chat-ai... |

Mỗi route kiểm tra:

- HTTP status không phải 404
- HTTP status không phải 500
- Body có nội dung
- Không hiện trang lỗi hệ thống
- Route yêu cầu đăng nhập không bị đá về `/auth/login`

Smoke test không truy cập route create/edit/delete theo ID, không submit form, không seed dữ liệu, không thay đổi database.

---

## Chạy smoke test theo từng role

```powershell
npx playwright test route-smoke.spec.ts -g "Public" --headed --workers=1
npx playwright test route-smoke.spec.ts -g "Admin" --headed --workers=1
npx playwright test route-smoke.spec.ts -g "Teacher" --headed --workers=1
npx playwright test route-smoke.spec.ts -g "Student" --headed --workers=1
```

---

## Test bị skip?

Nếu thiếu biến trong `.env`, nhóm test cần đăng nhập sẽ skip, không fail.

Các biến bắt buộc:

```env
ADMIN_IDENTIFIER=
ADMIN_PASSWORD=

TEACHER_IDENTIFIER=
TEACHER_PASSWORD=

STUDENT_IDENTIFIER=
STUDENT_PASSWORD=
```

Ví dụ:

- Thiếu `TEACHER_IDENTIFIER` hoặc `TEACHER_PASSWORD` → test teacher bị skip
- Thiếu `STUDENT_IDENTIFIER` hoặc `STUDENT_PASSWORD` → test student bị skip
- Thiếu `ADMIN_IDENTIFIER` hoặc `ADMIN_PASSWORD` → test admin bị skip

---

## Ghi chú quan trọng

- `playwright.config.ts` đang để `workers: 1` để tránh backend local bị timeout.
- Không chạy song song nhiều worker với FastAPI + MySQL local.
- Không push `.env`.
- Không seed hoặc thay đổi dữ liệu DB trong quá trình test.
- Không bấm xác nhận xóa, duyệt, thanh toán, backup/restore trong test tự động.

---

## Xem báo cáo test

Sau khi chạy test:

```powershell
npx playwright show-report
```

Hoặc:

```powershell
npm run report
```

---

## Kết quả hiện tại

Bộ test cơ bản đã chạy thành công:

```text
26 passed
0 failed
0 skipped
```

Bao gồm:

- Trang công khai
- Form đăng nhập
- Login admin / teacher / student
- Menu admin
- Menu teacher
- Menu student