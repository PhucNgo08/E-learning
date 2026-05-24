import { test } from "@playwright/test";
import { hasCredentials, loginAsRole } from "./helpers/auth";
import {
  ADMIN_ROUTES,
  PUBLIC_ROUTES,
  STUDENT_ROUTES,
  TEACHER_ROUTES,
} from "./helpers/routes";
import { smokeVisit } from "./helpers/smoke";

test.describe.configure({ mode: "serial" });

test.describe("Route smoke — Public", () => {
  for (const route of PUBLIC_ROUTES) {
    test(`GET ${route.path}`, async ({ page }) => {
      await smokeVisit(page, route, { requireAuth: false });
    });
  }
});

test.describe("Route smoke — Admin", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!hasCredentials("admin"), "Thiếu ADMIN_IDENTIFIER / ADMIN_PASSWORD trong .env");
    await loginAsRole(page, "admin");
  });

  for (const route of ADMIN_ROUTES) {
    test(`GET ${route.path}`, async ({ page }) => {
      await smokeVisit(page, route);
    });
  }
});

test.describe("Route smoke — Teacher", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(
      !hasCredentials("teacher"),
      "Thiếu TEACHER_IDENTIFIER / TEACHER_PASSWORD trong .env",
    );
    await loginAsRole(page, "teacher");
  });

  for (const route of TEACHER_ROUTES) {
    test(`GET ${route.path}`, async ({ page }) => {
      await smokeVisit(page, route);
    });
  }
});

test.describe("Route smoke — Student", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(
      !hasCredentials("student"),
      "Thiếu STUDENT_IDENTIFIER / STUDENT_PASSWORD trong .env",
    );
    await loginAsRole(page, "student");
  });

  for (const route of STUDENT_ROUTES) {
    test(`GET ${route.path}`, async ({ page }) => {
      await smokeVisit(page, route);
    });
  }
});
