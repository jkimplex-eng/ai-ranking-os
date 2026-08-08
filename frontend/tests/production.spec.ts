import { expect, test } from "@playwright/test";

test("authenticated Skinjestique research completes through Web UI", async ({ page }) => {
  const email = process.env.E2E_EMAIL;
  const password = process.env.E2E_PASSWORD;
  test.skip(!email || !password, "Production credentials are required for this scenario");

  await page.goto("/");
  await page.getByLabel("Email").fill(email!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Где ваш бренд в ответах AI?" })).toBeVisible();
  await expect(page.getByLabel("Бренд")).toHaveValue("Skinjestique");
  await page.getByRole("button", { name: "Проверить" }).click();
  await expect(page.getByText(/Analyze.*Skinjestique/)).toBeVisible();
  await page.getByRole("button", { name: "Запустить исследование" }).click();
  await expect(page.getByText("AI VISIBILITY REPORT")).toBeVisible({ timeout: 180_000 });
  await expect(page.getByText("COMPLETED")).toBeVisible();
  await expect(page.getByText("Visibility", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page.getByRole("heading", { name: "Войдите в рабочее пространство" })).toBeVisible();
});
