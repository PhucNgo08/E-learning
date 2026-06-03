import { test, expect, Page } from "@playwright/test";
import { hasCredentials, loginAsRole } from "./helpers/auth";

const teacherMenu = {
  sidebar: "#sidebar.teacher-sidebar",
  dashboard: '#sidebar.teacher-sidebar a[href="/teacher/dashboard"]',
  analytics: '#sidebar.teacher-sidebar a[href="/teacher/analytics"]',
  courses: '#sidebar.teacher-sidebar a[href="/teacher/courses/list"]',
  classes: '#sidebar.teacher-sidebar a[href="/teacher/classes/list"]',
  modules: '#sidebar.teacher-sidebar a[href="/teacher/modules/list-all"]',
  lessons: '#sidebar.teacher-sidebar a[href="/teacher/lessons/list-all"]',
  assignments: '#sidebar.teacher-sidebar a[href="/teacher/assignments/list"]',
  quizzes: '#sidebar.teacher-sidebar a[href="/teacher/quizzes/list"]',
  quizTemplates: '#sidebar.teacher-sidebar a[href="/teacher/quizzes/templates"]',
  materials: '#sidebar.teacher-sidebar a[href="/teacher/materials/list"]',
  reviews: '#sidebar.teacher-sidebar a[href="/teacher/reviews/manage"]',
  messages: '#sidebar.teacher-sidebar a[href="/teacher/message/inbox"]',
  notifications: '#sidebar.teacher-sidebar a[href="/teacher/notifications/"]',
  schedule: '#sidebar.teacher-sidebar a[href="/teacher/schedule/list"]',
  statistics: '#sidebar.teacher-sidebar a[href="/teacher/statistics/index"]',
  progress: '#sidebar.teacher-sidebar a[href="/teacher/statistics/progress"]',
  profile: '#sidebar.teacher-sidebar a[href="/teacher/profile"]',
  logout: '#sidebar.teacher-sidebar a[href="/auth/logout"]',
};

async function assertNoAppError(page: Page) {
  await expect(page.locator("body")).not.toContainText(
    /Không tìm thấy nội dung|Có lỗi hệ thống|Thiếu giao diện|404 Not Found|500 Internal Server Error/i
  );
}

test.describe("Menu Teacher", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(
      !hasCredentials("teacher"),
      "Thiếu TEACHER_IDENTIFIER / TEACHER_PASSWORD trong .env"
    );

    await loginAsRole(page, "teacher");
    await assertNoAppError(page);
  });

  test("dashboard teacher load và hiển thị sidebar", async ({ page }) => {
    await expect(page).toHaveURL(/\/teacher\/dashboard/);
    await expect(page.locator(teacherMenu.sidebar)).toBeVisible();
  });

  test("sidebar có các mục menu chính", async ({ page }) => {
    const expectedLinks = [
      teacherMenu.dashboard,
      teacherMenu.analytics,
      teacherMenu.courses,
      teacherMenu.classes,
      teacherMenu.modules,
      teacherMenu.lessons,
      teacherMenu.assignments,
      teacherMenu.quizzes,
      teacherMenu.quizTemplates,
      teacherMenu.materials,
      teacherMenu.reviews,
      teacherMenu.messages,
      teacherMenu.notifications,
      teacherMenu.schedule,
      teacherMenu.statistics,
      teacherMenu.progress,
      teacherMenu.profile,
      teacherMenu.logout,
    ];

    for (const selector of expectedLinks) {
      await expect(page.locator(selector)).toBeVisible();
    }
  });

  test("điều hướng tới phân tích học tập", async ({ page }) => {
    await page.locator(teacherMenu.analytics).click();
    await expect(page).toHaveURL(/\/teacher\/analytics/);
    await assertNoAppError(page);
  });

  test("điều hướng tới danh sách khóa học", async ({ page }) => {
    await page.locator(teacherMenu.courses).click();
    await expect(page).toHaveURL(/\/teacher\/courses\/list/);
    await assertNoAppError(page);
  });

  test("điều hướng tới bài tập", async ({ page }) => {
    await page.locator(teacherMenu.assignments).click();
    await expect(page).toHaveURL(/\/teacher\/assignments\/list/);
    await assertNoAppError(page);
  });

  test("điều hướng tới hồ sơ cá nhân", async ({ page }) => {
    await page.locator(teacherMenu.profile).click();
    await expect(page).toHaveURL(/\/teacher\/profile/);
    await assertNoAppError(page);
  });

  test("nút đăng xuất hiển thị", async ({ page }) => {
    await expect(page.locator(teacherMenu.logout)).toBeVisible();
    await expect(page.locator(teacherMenu.logout)).toContainText(/Đăng xuất/i);
  });
});