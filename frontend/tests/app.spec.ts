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
        : path.endsWith("/product-analytics/dashboard")
          ? { period: "DAILY", overview: {}, users: {}, organizations: {}, sessions: {}, research: {}, reports: {}, providers: {}, feedback: {}, errors: {}, trends: [], cached: false }
        : path.endsWith("/notifications/summary")
          ? { unread: 0, total: 0, archived: 0 }
        : path.endsWith("/audit/events")
          ? { items: [], total: 0 }
        : path.endsWith("/reports")
          ? { items: [], total: 0 }
        : path.endsWith("/graph")
          ? { id: 1, structure_version: "1.0", node_count: 0, edge_count: 0, nodes: [], edges: [], created_at: new Date().toISOString() }
        : path.endsWith("/workspace")
          ? { id: 1, name: "Workspace", settings: {} }
          : path.endsWith("/router/status")
            ? { status: "ok", costs: {} }
          : path.endsWith("/system/health")
            ? { status: "healthy" }
          : path.endsWith("/providers") || path.endsWith("/api-keys") || path.endsWith("/research") || path.endsWith("/workspace/projects") || path.endsWith("/feedback") || path.endsWith("/notifications") || path.endsWith("/organizations") || path.endsWith("/execution/history") || path.endsWith("/admin/feedback") || path.endsWith("/admin/beta/users")
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
});
