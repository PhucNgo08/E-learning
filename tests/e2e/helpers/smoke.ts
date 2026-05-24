import { expect, type Page } from "@playwright/test";
import type { SmokeRoute } from "./routes";

const ERROR_PAGE_PATTERNS = [
  /Mã lỗi:\s*404/i,
  /Mã lỗi:\s*500/i,
  /Không tìm thấy nội dung/i,
  /Có lỗi hệ thống/i,
  /Không kết nối được cơ sở dữ liệu/i,
  /Cấu trúc dữ liệu chưa đồng bộ/i,
  /Thiếu giao diện hiển thị/i,
];

export interface SmokeOptions {
  /** When true, fail if redirected to /auth/login (protected routes). Default: true */
  requireAuth?: boolean;
}

/**
 * Visit a route with GET only — no form submit, no destructive actions.
 * Asserts HTTP status, visible body, and absence of server error pages.
 */
export async function smokeVisit(
  page: Page,
  route: SmokeRoute,
  options: SmokeOptions = {},
): Promise<void> {
  const { requireAuth = true } = options;
  const label = route.path;

  const response = await page.goto(route.path, {
    waitUntil: "domcontentloaded",
    timeout: 30_000,
  });

  const status = response?.status() ?? 0;

  expect(status, `${label} — HTTP status`).not.toBe(404);
  expect(status, `${label} — HTTP status`).not.toBe(500);
  expect(status, `${label} — HTTP status`).toBeGreaterThanOrEqual(200);
  expect(status, `${label} — HTTP status`).toBeLessThan(500);

  await expect(page.locator("body")).toBeVisible({ timeout: 10_000 });

  const bodyText = (await page.locator("body").innerText()).trim();
  expect(bodyText.length, `${label} — body content`).toBeGreaterThan(0);

  for (const pattern of ERROR_PAGE_PATTERNS) {
    expect(bodyText, `${label} — error page content`).not.toMatch(pattern);
  }

  const currentUrl = page.url();

  if (requireAuth) {
    expect(currentUrl, `${label} — should not redirect to login`).not.toMatch(
      /\/auth\/login/,
    );
  }

  if (route.urlPattern) {
    expect(currentUrl, `${label} — final URL`).toMatch(route.urlPattern);
  }
}
