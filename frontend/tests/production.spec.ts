import { expect, test } from "@playwright/test";

async function login(page: import("@playwright/test").Page) {
  const email = process.env.E2E_EMAIL;
  const password = process.env.E2E_PASSWORD;
  test.skip(!email || !password, "Production credentials are required for this scenario");
  await page.goto("/");
  await page.getByLabel("Email").fill(email!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByText("СОСТОЯНИЕ БРЕНДА", { exact: true })).toBeVisible();
}

test("all production navigation routes use the real backend", async ({ page }) => {
  const browserErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      failedRequests.push(`${response.status()} ${new URL(response.url()).pathname}`);
    }
  });

  await login(page);
  const routes = [
    ["Getting Started", "/getting-started", "Начните с первого результата"],
    ["Research", "/research", "Исследования"],
    ["Reports", "/reports", "Отчёты"],
    ["Recommendations", "/recommendations", "Рекомендации"],
    ["Knowledge Graph", "/knowledge-graph", "Knowledge Graph"],
    ["Competitors", "/competitors", "Конкуренты"],
    ["History", "/history", "История"],
    ["AI Providers", "/providers", "AI Providers"],
    ["Product Analytics", "/product-analytics", "Product Analytics"],
    ["Notifications", "/notifications", "Уведомления"],
    ["Organizations", "/organizations", "Организация"],
    ["Feedback", "/feedback", "Feedback"],
    ["User Profile", "/profile", "Профиль"],
    ["Settings", "/settings", "Настройки"],
    ["Admin Console", "/admin", "Admin Console"],
  ] as const;
  for (const [link, path, heading] of routes) {
    await page.getByRole("button").filter({ hasText: link }).click();
    await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}$`));
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
  }
  expect(failedRequests, `Failed API requests: ${failedRequests.join(", ")}`).toEqual([]);
  expect(browserErrors, `Browser errors: ${browserErrors.join(" | ")}`).toEqual([]);
});

test("authenticated Skinjestique research completes through Web UI", async ({ page }) => {
  await login(page);
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
