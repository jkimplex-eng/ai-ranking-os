import { expect, test } from "@playwright/test";

test("authenticated Skinjestique research completes through Web UI", async ({ page }) => {
  const email = process.env.E2E_EMAIL;
  const password = process.env.E2E_PASSWORD;
  test.skip(!email || !password, "Production credentials are required for this scenario");

  await page.goto("/");
  await page.getByLabel("Email").fill(email!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByText("СОСТОЯНИЕ БРЕНДА", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Новое исследование" }).click();
  await expect(page.getByLabel("Название бренда")).toHaveValue("Skinjestique");
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: "Проверить" }).click();
  await expect(page.getByText(/Analyze.*Skinjestique/)).toBeVisible();
  await page.getByRole("button", { name: "Запустить исследование" }).click();
  await expect(page.getByText(/EXECUTIVE REPORT/)).toBeVisible({ timeout: 180_000 });
  await expect(page.getByText("Visibility", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page.getByRole("heading", { name: "Понимайте, как AI видит ваш бренд" })).toBeVisible();
});
