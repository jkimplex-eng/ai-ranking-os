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
  test.setTimeout(120_000);
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
  await page.getByText("Для экспертов", { exact: true }).click();
  await page.getByText("Рабочее пространство", { exact: true }).click();
  const routes = [
    ["Как начать", "/getting-started", "Начните с первого результата"],
    ["Все исследования", "/research", "Исследования"],
    ["Результаты", "/reports", "Отчёты"],
    ["План действий", "/recommendations", "Рекомендации"],
    ["Связи и источники", "/knowledge-graph", "Граф знаний"],
    ["Конкуренты", "/competitors", "Конкуренты"],
    ["История изменений", "/history", "История"],
    ["Подключения ИИ", "/providers", "Провайдеры ИИ"],
    ["Аналитика продукта", "/product-analytics", "Product Analytics"],
    ["Уведомления", "/notifications", "Уведомления"],
    ["Организация", "/organizations", "Организация"],
    ["Обратная связь", "/feedback", "Обратная связь"],
    ["Профиль", "/profile", "Профиль"],
    ["Настройки", "/settings", "Настройки"],
    ["Администрирование", "/admin", "Admin Console"],
  ] as const;
  for (const [link, path, heading] of routes) {
    await page.getByRole("navigation").getByRole("button").filter({ hasText: link }).click();
    await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}$`));
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Coming Soon|Скоро/i)).toHaveCount(0);
    await page.reload();
    await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}$`));
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible({ timeout: 15_000 });
    await page.goBack();
    await page.goForward();
    await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}$`));
  }
  expect(failedRequests, `Failed API requests: ${failedRequests.join(", ")}`).toEqual([]);
  expect(browserErrors, `Browser errors: ${browserErrors.join(" | ")}`).toEqual([]);
});

test("authenticated Skinjestique research completes through Web UI", async ({ page }) => {
  test.setTimeout(240_000);
  await login(page);
  await page.getByRole("button", { name: "Новое исследование" }).click();
  await page.getByLabel("Название бренда").fill("Skinjestique");
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button").filter({ hasText: "Private" }).click();
  await page.getByRole("button", { name: "Проверить" }).click();
  await expect(page.getByText(/Analyze.*Skinjestique/)).toBeVisible();
  await page.getByRole("button", { name: "Запустить исследование" }).click();
  await expect(page.getByText(/EXECUTIVE REPORT/)).toBeVisible({ timeout: 180_000 });
  await expect(page.getByText("Visibility", { exact: true })).toBeVisible();
  await page.getByRole("navigation").getByRole("button").filter({ hasText: "Recommendations" }).click();
  await expect(page.getByRole("heading", { name: "Рекомендации" })).toBeVisible();
  await page.getByRole("navigation").getByRole("button").filter({ hasText: "Knowledge Graph" }).click();
  await expect(page.getByRole("heading", { name: "Knowledge Graph" })).toBeVisible();
  await page.getByRole("navigation").getByRole("button").filter({ hasText: "Product Analytics" }).click();
  await expect(page.getByRole("heading", { name: "Product Analytics" })).toBeVisible();
  await page.getByRole("navigation").getByRole("button").filter({ hasText: "Notifications" }).click();
  await expect(page.getByRole("heading", { name: "Уведомления" })).toBeVisible();
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page.getByRole("heading", { name: "Понимайте, как AI видит ваш бренд" })).toBeVisible();
});
