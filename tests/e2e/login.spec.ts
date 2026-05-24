import { test, expect } from "@playwright/test";
import { getCredentials, hasCredentials, loginAs } from "./helpers/auth";
import { loginSelectors } from "./helpers/selectors";

test.describe("Form đăng nhập", () => {
  test("submit rỗng hiển thị cảnh báo trình duyệt", async ({ page }) => {
    await page.goto("/auth/login");

    page.once("dialog", async (dialog) => {
      expect(dialog.message()).toMatch(/nhập đầy đủ|email|username|mật khẩu/i);
      await dialog.accept();
    });

    await page.click(loginSelectors.submit);
    await expect(page).toHaveURL(/\/auth\/login/);
  });

  test("sai mật khẩu hiển thị thông báo lỗi", async ({ page }) => {
    const admin = getCredentials("admin");
    test.skip(!admin, "Cần ADMIN_IDENTIFIER trong .env để test sai mật khẩu");

    await page.goto("/auth/login");
    await page.fill(loginSelectors.identifier, admin!.identifier);
    await page.fill(loginSelectors.password, "__wrong_password__");
    await page.click(loginSelectors.submit);

    await expect(page).toHaveURL(/\/auth\/login/);
    await expect(page.locator(loginSelectors.errorBox)).toBeVisible();
  });

  test("đăng nhập admin thành công → /admin/dashboard", async ({ page }) => {
    test.skip(!hasCredentials("admin"), "Thiếu ADMIN_IDENTIFIER / ADMIN_PASSWORD trong .env");

    await loginAs(page, getCredentials("admin")!);
    await expect(page).toHaveURL(/\/admin\/dashboard/);
  });

  test("đăng nhập teacher thành công → /teacher/dashboard", async ({ page }) => {
    test.skip(!hasCredentials("teacher"), "Thiếu TEACHER_IDENTIFIER / TEACHER_PASSWORD trong .env");

    await loginAs(page, getCredentials("teacher")!);
    await expect(page).toHaveURL(/\/teacher\/dashboard/);
  });

  test("đăng nhập student thành công → /student/dashboard", async ({ page }) => {
    test.skip(!hasCredentials("student"), "Thiếu STUDENT_IDENTIFIER / STUDENT_PASSWORD trong .env");

    await loginAs(page, getCredentials("student")!);
    await expect(page).toHaveURL(/\/student\/dashboard/);
  });
});
