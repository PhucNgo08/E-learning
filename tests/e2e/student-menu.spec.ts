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

  test('nút menu Student chính hoạt động', async ({ page }) => {
    const routes = [
      '/student/dashboard',
      '/student/course/',
      '/student/course/enrolled',
      '/student/lesson/',
      '/student/assignment/list',
      '/student/todo',
      '/student/quiz/',
      '/student/material/',
      '/student/discussion/',
      '/student/schedule/list',
      '/student/profile/',
      '/student/notifications/',
      '/student/message/',
      '/student/cart/',
      '/student/wallet/page',
      '/student/chat-ai/',
    ];

    for (const route of routes) {
      await page.goto(route, { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL(new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
      await assertNoAppError(page);
    }
  });

  test('trang danh sách khóa học: nút Khóa học của tôi hoạt động', async ({ page }) => {
    await page.goto('/student/course/', { waitUntil: 'domcontentloaded' });
    await assertNoAppError(page);

    await page.getByRole('link', { name: /Khóa học của tôi/i }).click();
    await expect(page).toHaveURL(/\/student\/course\/enrolled/);
    await assertNoAppError(page);
  });

  test('trang Khóa học của tôi: nút Xem chi tiết hoạt động', async ({ page }) => {
    await page.goto('/student/course/enrolled', { waitUntil: 'domcontentloaded' });
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const rowCount = await rows.count();

    test.skip(rowCount === 0, 'Chưa có khóa học đã ghi danh/mua để test nút Xem chi tiết.');

    await rows.first().getByRole('link', { name: /Xem chi tiết/i }).click();

    await expect(page).toHaveURL(/\/student\/course\/detail\//);
    await assertNoAppError(page);
  });

  test('trang Khóa học của tôi: nút Học tiếp hoặc Xem lại hoạt động', async ({ page }) => {
    await page.goto('/student/course/enrolled', { waitUntil: 'domcontentloaded' });
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const rowCount = await rows.count();

    test.skip(rowCount === 0, 'Chưa có khóa học đã ghi danh/mua để test nút Học tiếp/Xem lại.');

    await rows.first().getByRole('link', { name: /Học tiếp|Xem lại/i }).click();

    await expect(page).toHaveURL(/\/student\/course\/progress\//);
    await assertNoAppError(page);
  });

  test('trang Khóa học của tôi: nút Lộ trình hoạt động', async ({ page }) => {
    await page.goto('/student/course/enrolled', { waitUntil: 'domcontentloaded' });
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const rowCount = await rows.count();

    test.skip(rowCount === 0, 'Chưa có khóa học đã ghi danh/mua để test nút Lộ trình.');

    await rows.first().getByRole('link', { name: /Lộ trình/i }).click();

    await expect(page).toHaveURL(/\/student\/learning-path\//);
    await assertNoAppError(page);
  });

  test('trang chi tiết khóa học đã học: các nút chính hoạt động', async ({ page }) => {
    await page.goto('/student/course/enrolled', { waitUntil: 'domcontentloaded' });
    await assertNoAppError(page);

    const rows = page.locator('tbody tr.course-row');
    const rowCount = await rows.count();

    test.skip(rowCount === 0, 'Chưa có khóa học đã ghi danh/mua để test trang chi tiết.');

    await rows.first().getByRole('link', { name: /Xem chi tiết/i }).click();

    await expect(page).toHaveURL(/\/student\/course\/detail\//);
    await assertNoAppError(page);

    await expect(page.getByRole('link', { name: /Tiếp tục học/i }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Gợi ý lộ trình học/i }).first()).toBeVisible();

    await page.getByRole('link', { name: /Tiếp tục học/i }).first().click();
    await expect(page).toHaveURL(/\/student\/course\/progress\//);
    await assertNoAppError(page);
  });
});