import { test, expect } from "@playwright/test";
import { hasCredentials, loginAsRole } from "./helpers/auth";
import { adminMenu } from "./helpers/selectors";

test.describe("Menu Admin", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!hasCredentials("admin"), "Thiếu ADMIN_IDENTIFIER / ADMIN_PASSWORD trong .env");
    await loginAsRole(page, "admin");
  });

  test("dashboard admin load và hiển thị sidebar", async ({ page }) => {
    await expect(page).toHaveURL(/\/admin\/dashboard/);
    await expect(page.locator(adminMenu.sidebar)).toBeVisible();
  });

  test("sidebar có các mục menu chính", async ({ page }) => {
    const expectedLabels = [
      "Trang chủ",
      "Tiến độ học tập",
      "Người dùng",
      "Khóa học",
      "Ngành học",
      "Năm học",
      "Quản lý ví",
      "Cấu hình",
    ];

    for (const label of expectedLabels) {
      await expect(page.locator(adminMenu.items).filter({ hasText: label })).toBeVisible();
    }
  });

  test("điều hướng tới Quản lý người dùng", async ({ page }) => {
    await page.locator(adminMenu.users).click();
    await expect(page).toHaveURL(/\/admin\/Account\/manage-users/);
  });

  test("điều hướng tới Quản lý khóa học", async ({ page }) => {
    await page.locator(adminMenu.courses).click();
    await expect(page).toHaveURL(/\/admin\/Course\/manage/);
  });

  test("điều hướng tới Cấu hình hệ thống", async ({ page }) => {
    await page.locator(adminMenu.settings).click();
    await expect(page).toHaveURL(/\/admin\/settings\/manage/);
  });

  test("nút đăng xuất hiển thị trong sidebar", async ({ page }) => {
    await expect(page.locator(adminMenu.logout)).toBeVisible();
    await expect(page.locator(adminMenu.logout)).toContainText(/Đăng xuất/i);
  });
});
