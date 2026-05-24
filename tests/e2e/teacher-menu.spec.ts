import { test, expect } from "@playwright/test";
import { hasCredentials, loginAsRole } from "./helpers/auth";
import { teacherMenu } from "./helpers/selectors";

test.describe("Menu Teacher", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!hasCredentials("teacher"), "Thiếu TEACHER_IDENTIFIER / TEACHER_PASSWORD trong .env");
    await loginAsRole(page, "teacher");
  });

  test("dashboard teacher load và hiển thị sidebar", async ({ page }) => {
    await expect(page).toHaveURL(/\/teacher\/dashboard/);
    await expect(page.locator(teacherMenu.sidebar)).toBeVisible();
  });

  test("sidebar có các mục menu chính", async ({ page }) => {
    const expectedLabels = [
      "Bảng điều khiển",
      "Khóa học",
      "Lớp học",
      "Chương học",
      "Bài tập",
      "Trắc nghiệm",
      "Tài liệu",
      "Đánh giá",
      "Tin nhắn",
      "Lịch giảng dạy",
      "Thống kê",
      "Hồ sơ cá nhân",
    ];

    const sidebar = page.locator(teacherMenu.sidebar);
    for (const label of expectedLabels) {
      await expect(sidebar.getByRole("link", { name: label })).toBeVisible();
    }
  });

  test("điều hướng tới danh sách khóa học", async ({ page }) => {
    await page.locator(teacherMenu.courses).click();
    await expect(page).toHaveURL(/\/teacher\/courses/);
  });

  test("điều hướng tới bài tập", async ({ page }) => {
    await page.locator(teacherMenu.assignments).click();
    await expect(page).toHaveURL(/\/teacher\/assignments/);
  });

  test("điều hướng tới hồ sơ cá nhân", async ({ page }) => {
    await page.locator(teacherMenu.profile).click();
    await expect(page).toHaveURL(/\/teacher\/profile/);
  });

  test("nút đăng xuất hiển thị", async ({ page }) => {
    await expect(page.locator(teacherMenu.logout)).toBeVisible();
    await expect(page.locator(teacherMenu.logout)).toContainText(/Đăng xuất/i);
  });
});
