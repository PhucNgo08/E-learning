import { test, expect } from "@playwright/test";
import { hasCredentials, loginAsRole } from "./helpers/auth";
import { studentMenu } from "./helpers/selectors";

test.describe("Menu Student", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!hasCredentials("student"), "Thiếu STUDENT_IDENTIFIER / STUDENT_PASSWORD trong .env");
    await loginAsRole(page, "student");
  });

  test("dashboard student load và hiển thị sidebar", async ({ page }) => {
    await expect(page).toHaveURL(/\/student\/dashboard/);
    await expect(page.locator(studentMenu.sidebar)).toBeVisible();
  });

  test("sidebar có các mục menu chính", async ({ page }) => {
    const expectedLabels = [
      "Bảng điều khiển",
      "Khóa học của tôi",
      "Bài học",
      "Bài tập",
      "Việc cần làm",
      "Trắc nghiệm",
      "Tài liệu",
      "Thảo luận",
      "Lịch học",
      "Hồ sơ cá nhân",
    ];

    const sidebar = page.locator(studentMenu.sidebar);
    for (const label of expectedLabels) {
      await expect(sidebar.getByRole("link", { name: label })).toBeVisible();
    }
  });

  test("điều hướng tới khóa học của tôi", async ({ page }) => {
    await page.locator(studentMenu.courses).click();
    await expect(page).toHaveURL(/\/student\/course/);
  });

  test("điều hướng tới bài tập", async ({ page }) => {
    await page.locator(studentMenu.assignments).click();
    await expect(page).toHaveURL(/\/student\/assignment/);
  });

  test("điều hướng tới hồ sơ cá nhân", async ({ page }) => {
    await page.locator(studentMenu.profile).click();
    await expect(page).toHaveURL(/\/student\/profile/);
  });

  test("nút đăng xuất hiển thị", async ({ page }) => {
    await expect(page.locator(studentMenu.logout)).toBeVisible();
    await expect(page.locator(studentMenu.logout)).toContainText(/Đăng xuất/i);
  });
});
