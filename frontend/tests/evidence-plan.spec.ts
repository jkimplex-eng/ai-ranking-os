import { expect, test } from "@playwright/test";

test("manager can trace a task to a source and see an audit failure without losing the plan", async ({ page }) => {
  const action = {
    id: "source-1", resource: "example.org", reason: "Ресурс указан в одном ответе.",
    deliverable: "Проверить правила редакции и предложить разбор выбора курса.",
    affected_metric: "citation_score", expected_effect_range: [], confidence: 0,
    effort: "HIGH", estimated_days: 30, verification: "Повторить те же вопросы через 30 дней.",
    causality_notice: "Связь не доказывает причинность.", owner: "PR-менеджер",
    prerequisites: "Проверить условия редакции.", channel: "EARNED_MEDIA",
    evidence: [{response_id: 7, query: "Где изучать дизайн?", provider: "yandex", model: "api",
      mentioned: false, competitors: ["Другая школа"], urls: ["https://example.org/courses"]}],
  };
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/auth/login") || path.endsWith("/auth/refresh")) json = {access_token: "access", refresh_token: "refresh-token-with-valid-length"};
    else if (path.endsWith("/auth/me")) json = {id: 1, display_name: "Manager", email: "manager@example.com", roles: ["superadmin"]};
    else if (path.endsWith("/research")) json = [{id: 1, title: "Skillbox", status: "COMPLETED", metadata: {brand: "Skillbox", website_url: "https://skillbox.ru"}}];
    else if (path.endsWith("/research/1/final-report")) json = {research: {id: 1, title: "Skillbox", status: "COMPLETED"}, geo_opportunities: [action], sources: []};
    else if (path.endsWith("/notifications/summary")) json = {unread: 0, total: 0, archived: 0};
    else if (path.endsWith("/system/health")) json = {status: "healthy"};
    else if (path.endsWith("/geo/site-audits") && route.request().method() === "POST") {
      return route.fulfill({status: 422, contentType: "application/json", body: JSON.stringify({detail: "Сайт временно недоступен"})});
    }
    await route.fulfill({status: 200, contentType: "application/json", body: JSON.stringify(json)});
  });
  await page.goto("/");
  await page.getByLabel("Email").fill("manager@example.com");
  await page.getByLabel("Пароль").fill("strong-password");
  await page.getByRole("button", {name: "Войти", exact: true}).click();
  await expect(page.getByLabel("Email")).not.toBeVisible();
  await page.goto("/recommendations");
  await expect(page.getByRole("heading", {name: "Три приоритетных действия"})).toBeVisible();
  await expect(page.getByText("PR-менеджер", {exact: true})).toBeVisible();
  await page.getByText("На чём основан совет · 1 ответов", {exact: true}).click();
  await expect(page.getByRole("link", {name: "https://example.org/courses", exact: true})).toHaveAttribute("href", "https://example.org/courses");
  await expect(page.getByText("Где изучать дизайн?", {exact: true})).toBeVisible();
  await page.getByRole("button", {name: "Проверить сайт и получить задачи"}).click();
  await expect(page.getByRole("alert")).toContainText("Сайт временно недоступен");
  await expect(page.getByRole("heading", {name: "Три приоритетных действия"})).toBeVisible();
  await expect(page.getByText("Оценочный диапазон:")).toHaveCount(0);
});
