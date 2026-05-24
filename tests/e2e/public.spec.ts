import { test, expect } from "@playwright/test";
import { publicSelectors, loginSelectors } from "./helpers/selectors";

test.describe("Trang công khai", () => {
  test("trang chủ load thành công", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBeLessThan(400);

    await expect(page).toHaveTitle(/E-Learning|Trang chủ/i);
    await expect(page.locator(publicSelectors.brand)).toBeVisible();
  });

  test("nút Đăng nhập dẫn tới /auth/login", async ({ page }) => {
    await page.goto("/");

    const loginLink = page.locator(publicSelectors.loginButton);
    await expect(loginLink).toBeVisible();
    await expect(loginLink).toHaveAttribute("href", "/auth/login");

    await loginLink.click();
    await expect(page).toHaveURL(/\/auth\/login$/);
    await expect(page.locator(loginSelectors.form)).toBeVisible();
  });

  test("trang đăng nhập hiển thị form đầy đủ", async ({ page }) => {
    await page.goto("/auth/login");

    await expect(page.locator(loginSelectors.title)).toContainText("Đăng nhập");
    await expect(page.locator(loginSelectors.identifier)).toBeVisible();
    await expect(page.locator(loginSelectors.password)).toBeVisible();
    await expect(page.locator(loginSelectors.submit)).toBeVisible();
    await expect(page.locator('a[href="/"]')).toBeVisible();
    await expect(page.locator('a[href="/auth/forgot-password"]')).toBeVisible();
  });
});
