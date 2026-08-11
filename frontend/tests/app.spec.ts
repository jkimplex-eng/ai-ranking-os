import { expect, test } from "@playwright/test";

test("login page exposes product entry point", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Понимайте, как AI видит ваш бренд" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
});

test("wizard transparently refreshes an expired access token", async ({ page }) => {
  let reviewAttempts = 0;
  let refreshed = false;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let status = 200;
    let json: unknown = {};
    if (path.endsWith("/auth/login")) {
      json = { access_token: "expired-access", refresh_token: "valid-refresh-token" };
    } else if (path.endsWith("/auth/refresh")) {
      refreshed = true;
      json = { access_token: "renewed-access", refresh_token: "rotated-refresh-token" };
    } else if (path.endsWith("/auth/me")) {
      json = { id: 1, display_name: "Analyst", email: "analyst@example.com", roles: ["analyst"] };
    } else if (path.endsWith("/research/wizard/review")) {
      reviewAttempts += 1;
      if (reviewAttempts === 1) {
        status = 401;
        json = { detail: "Authentication required" };
      } else {
        expect(request.headers()["authorization"]).toBe("Bearer renewed-access");
        json = {
          valid: true, title: "AI Visibility", prompt: "Analyze Acme",
          provider_models: ["ollama/qwen2.5:3b"], selected_models: ["ollama/qwen2.5:3b"],
          languages: ["ru"], regions: ["GLOBAL"], pipeline: [],
          estimated_cost_usd: 0, estimated_time_ms: 20000,
        };
      }
    } else if (path.endsWith("/research") || path.endsWith("/providers")) {
      json = [];
    } else if (path.endsWith("/system/health")) {
      json = { status: "healthy" };
    }
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(json) });
  });

  await page.goto("/");
  await page.getByLabel("Email").fill("analyst@example.com");
  await page.getByLabel("Пароль").fill("strong-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await page.getByRole("button", { name: "Проверить бренд" }).click();
  await page.getByLabel("Название бренда").fill("Acme");
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: "Проверить" }).click();

  await expect(page.getByText("Analyze Acme")).toBeVisible();
  expect(refreshed).toBe(true);
  expect(reviewAttempts).toBe(2);
});

test("authenticated routes survive refresh and browser history", async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = path.endsWith("/auth/login") || path.endsWith("/auth/refresh")
      ? { access_token: "access", refresh_token: "refresh-token-with-valid-length" }
      : path.endsWith("/auth/me")
        ? { id: 1, display_name: "Admin", email: "admin@example.com", roles: ["superadmin"] }
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
    await page.getByRole("navigation").getByRole("button").filter({ hasText: link }).click();
    await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}$`));
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
  }
});
