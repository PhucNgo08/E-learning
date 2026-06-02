import { test, expect, Page } from '@playwright/test';

const STUDENT_USERNAME = process.env.STUDENT_IDENTIFIER || 'sv002';
const STUDENT_PASSWORD = process.env.STUDENT_PASSWORD || '123456@Az';

async function assertNoAppError(page: Page) {
  await expect(page.locator('body')).not.toContainText(
    /Không tìm thấy nội dung|Có lỗi hệ thống|Thiếu giao diện|404 Not Found|500 Internal Server Error/i
  );
}

async function loginAsStudent(page: Page) {
  await page.goto('/auth/login', { waitUntil: 'domcontentloaded' });

  const identifier = page.locator(
    [
      'input[name="identifier"]',
      'input#identifier',
      'input[name="username"]',
      'input#username',
      'input[name="email"]',
      'input#email',
      'input[type="text"]'
    ].join(', ')
  ).first();

  const password = page.locator(
    [
      'input[name="password"]',
      'input#password',
      'input[type="password"]'
    ].join(', ')
  ).first();

  await expect(identifier).toBeVisible({ timeout: 10000 });
  await identifier.fill(STUDENT_USERNAME);

  await expect(password).toBeVisible({ timeout: 10000 });
  await password.fill(STUDENT_PASSWORD);

  const loginButton = page.getByRole('button', { name: /đăng nhập|login/i }).first();

  if (await loginButton.count()) {
    await loginButton.click();
  } else {
    await page.locator('button[type="submit"], input[type="submit"]').first().click();
  }

  await page.waitForURL(/\/student\/dashboard|\/student\//, { timeout: 15000 });
  await assertNoAppError(page);
}

test.describe('Student buttons', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsStudent(page);
  });

  test('mở trang Khóa học của tôi', async ({ page }) => {
    await page.goto('/student/course/enrolled');
    await expect(page).toHaveURL(/\/student\/course\/enrolled/);
    await assertNoAppError(page);
  });

  test('nút Xem chi tiết trong Khóa học của tôi hoạt động', async ({ page }) => {
    await page.goto('/student/course/enrolled');
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const count = await rows.count();

    test.skip(count === 0, 'Chưa có khóa học đã ghi danh/mua để test.');

    await rows.first().getByRole('link', { name: /Xem chi tiết/i }).click();

    await expect(page).toHaveURL(/\/student\/course\/detail\//);
    await assertNoAppError(page);
  });

  test('nút Học tiếp hoặc Xem lại hoạt động', async ({ page }) => {
    await page.goto('/student/course/enrolled');
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const count = await rows.count();

    test.skip(count === 0, 'Chưa có khóa học đã ghi danh/mua để test.');

    await rows.first().getByRole('link', { name: /Học tiếp|Xem lại/i }).click();

    await expect(page).toHaveURL(/\/student\/course\/progress\//);
    await assertNoAppError(page);
  });

  test('nút Lộ trình hoạt động', async ({ page }) => {
    await page.goto('/student/course/enrolled');
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const count = await rows.count();

    test.skip(count === 0, 'Chưa có khóa học đã ghi danh/mua để test.');

    await rows.first().getByRole('link', { name: /Lộ trình/i }).click();

    await expect(page).toHaveURL(/\/student\/learning-path\//);
    await assertNoAppError(page);
  });

  test('trang chi tiết khóa học có nút Tiếp tục học và Gợi ý lộ trình', async ({ page }) => {
    await page.goto('/student/course/enrolled');
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const count = await rows.count();

    test.skip(count === 0, 'Chưa có khóa học đã ghi danh/mua để test.');

    await rows.first().getByRole('link', { name: /Xem chi tiết/i }).click();

    await expect(page).toHaveURL(/\/student\/course\/detail\//);
    await assertNoAppError(page);

    await expect(page.getByRole('link', { name: /Tiếp tục học/i }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Gợi ý lộ trình học/i }).first()).toBeVisible();
  });
});