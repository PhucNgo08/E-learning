import { expect, type Page } from "@playwright/test";
import { loginSelectors } from "./selectors";

export type Role = "admin" | "teacher" | "student";

export interface Credentials {
  identifier: string;
  password: string;
}

const ENV_KEYS: Record<Role, { id: string; pass: string }> = {
  admin: { id: "ADMIN_IDENTIFIER", pass: "ADMIN_PASSWORD" },
  teacher: { id: "TEACHER_IDENTIFIER", pass: "TEACHER_PASSWORD" },
  student: { id: "STUDENT_IDENTIFIER", pass: "STUDENT_PASSWORD" },
};

export function getCredentials(role: Role): Credentials | null {
  const keys = ENV_KEYS[role];
  const identifier = process.env[keys.id]?.trim();
  const password = process.env[keys.pass]?.trim();

  if (!identifier || !password) return null;

  return { identifier, password };
}

export function hasCredentials(role: Role): boolean {
  return getCredentials(role) !== null;
}

/**
 * Fill and submit login form.
 * Fix: không dùng Promise.all cứng với waitForURL + click vì đôi khi
 * Playwright bị kẹt ở bước "waiting for scheduled navigations to finish".
 */
export async function loginAs(page: Page, creds: Credentials): Promise<void> {
  await page.goto("/auth/login", {
    waitUntil: "domcontentloaded",
    timeout: 30_000,
  });

  const form = page.locator(loginSelectors.form);
  const identifierInput = page.locator(loginSelectors.identifier);
  const passwordInput = page.locator(loginSelectors.password);
  const submitBtn = page.locator(loginSelectors.submit);

  await expect(form).toBeVisible({
    timeout: 15_000,
  });

  await identifierInput.fill(creds.identifier);
  await passwordInput.fill(creds.password);

  await expect(submitBtn).toBeVisible({
    timeout: 15_000,
  });

  await expect(submitBtn).toBeEnabled({
    timeout: 15_000,
  });

  await submitBtn.scrollIntoViewIfNeeded();

  await submitBtn.click({
    force: true,
    timeout: 15_000,
    noWaitAfter: true,
  });

  try {
    await page.waitForURL((url) => !url.pathname.startsWith("/auth/login"), {
      timeout: 30_000,
      waitUntil: "domcontentloaded",
    });
  } catch {
    await page.waitForTimeout(1500);
  }

  await page.waitForLoadState("domcontentloaded").catch(() => undefined);

  const currentPath = new URL(page.url()).pathname;

  if (currentPath.startsWith("/auth/login")) {
    const errorText = await page
      .locator(".alert-danger, .text-danger, .invalid-feedback, .error-message")
      .first()
      .textContent()
      .catch(() => "");

    throw new Error(
      `Login failed or did not redirect from /auth/login. ${
        errorText ? `Message: ${errorText.trim()}` : "Check credentials in tests/e2e/.env"
      }`,
    );
  }
}

export async function loginAsRole(page: Page, role: Role): Promise<void> {
  const creds = getCredentials(role);

  if (!creds) {
    throw new Error(
      `Missing credentials for role "${role}". Set ${ENV_KEYS[role].id} and ${ENV_KEYS[role].pass} in tests/e2e/.env`,
    );
  }

  await loginAs(page, creds);
}

export async function logout(page: Page): Promise<void> {
  await page.goto("/auth/logout", {
    waitUntil: "domcontentloaded",
    timeout: 30_000,
  });
}