import { expect, test } from "@playwright/test";

test("login page exposes product entry point", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Понимайте, как AI видит ваш бренд" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
});

test("authenticated routes survive refresh and browser history", async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = path.endsWith("/auth/login") || path.endsWith("/auth/refresh")
      ? { access_token: "access", refresh_token: "refresh-token-with-valid-length" }
      : path.endsWith("/auth/me")
        ? { display_name: "Admin", email: "admin@example.com" }
        : path.endsWith("/workspace")
          ? { id: 1, name: "Workspace", settings: {} }
          : path.endsWith("/providers") || path.endsWith("/api-keys")
            ? []
            : path.endsWith("/research")
              ? []
              : {};
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
  });
  await page.goto("/");
  await page.getByLabel("Email").fill("admin@example.com");
  await page.getByLabel("Пароль").fill("strong-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await page.getByRole("button", { name: "Settings" }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Настройки" })).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Настройки" })).toBeVisible();
  await page.getByRole("button", { name: "Dashboard" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/settings$/);
  await page.goForward();
  await expect(page).toHaveURL(/\/$/);
});
