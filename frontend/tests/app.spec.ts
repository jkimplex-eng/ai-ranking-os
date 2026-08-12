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
    } else if (path.endsWith("/router/models")) {
      json = { items: [{ id: "qwen-test", provider: "ollama", display_name: "Qwen", version: "2.5", status: "ACTIVE", tier: "FREE", capabilities: ["chat"], availability: 1, pricing: { input_per_million: 0, output_per_million: 0 } }], total: 1 };
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
  await page.getByRole("button", { name: /Qwen/ }).click();
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
  await page.getByRole("button", { name: "Настройки" }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Настройки" })).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Настройки" })).toBeVisible();
  await page.getByRole("button", { name: "Обзор" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/settings$/);
  await page.goForward();
  await expect(page).toHaveURL(/\/$/);

  const routes = [
    ["Начало работы", "/getting-started", "Начните с первого результата"],
    ["Исследования", "/research", "Исследования"],
    ["Отчёты", "/reports", "Отчёты"],
    ["Рекомендации", "/recommendations", "Рекомендации"],
    ["Граф знаний", "/knowledge-graph", "Граф знаний"],
    ["Конкуренты", "/competitors", "Конкуренты"],
    ["История", "/history", "История"],
    ["Провайдеры ИИ", "/providers", "AI Providers"],
    ["Аналитика продукта", "/product-analytics", "Product Analytics"],
    ["Уведомления", "/notifications", "Уведомления"],
    ["Организации", "/organizations", "Организация"],
    ["Обратная связь", "/feedback", "Обратная связь"],
    ["Профиль", "/profile", "Профиль"],
    ["Настройки", "/settings", "Настройки"],
    ["Администрирование", "/admin", "Admin Console"],
  ] as const;
  for (const [link, path, heading] of routes) {
    await page.getByRole("navigation").getByRole("button").filter({ hasText: link }).click();
    await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}$`));
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
  }
});

test("executive report explains metrics, zero citations and graph evidence", async ({ page }) => {
  const now = "2026-08-11T12:00:00Z";
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json: unknown = path.endsWith("/auth/login") ? { access_token: "access", refresh_token: "refresh-token-with-valid-length" }
      : path.endsWith("/auth/me") ? { id: 1, display_name: "Analyst", email: "analyst@example.com", roles: ["analyst"] }
      : path.endsWith("/research") ? [{ id: 31, title: "AI Visibility: skinjestique", status: "COMPLETED", total_tasks: 2, completed_tasks: 2, created_at: now, metadata: { brand: "Skinjestique" } }]
      : path.endsWith("/research/31/final-report") ? { research: { id: 31, title: "AI Visibility: skinjestique", status: "COMPLETED", total_tasks: 2, created_at: now, metadata: { brand: "Skinjestique" } }, score: { visibility_score: 84.7, mention_score: 100, recommendation_score: 90, citation_score: 0, coverage_score: 100, confidence_score: 92, version: "1.0", calculated_at: now }, responses: [{ id: 1, provider: "ollama", model: "qwen2.5:3b", content: "Skinjestique recommended", processing_status: "PROCESSED", created_at: now, finished_at: now, latency_ms: 15000, total_tokens: 315, cost: 0 }], detected_entities: [{ id: 1, name: "Skinjestique", entity_type: "BRAND", confidence: .99 }], sources: [], recommendations: [{ id: 4, recommendation_type: "CITATION_AUTHORITY", priority: "HIGH", metric: "citation_score", metric_value: 0, explanation: "Citation Score below 50", expected_effect: "Improve citation" }], trend: { metrics: [{ metric: "visibility", direction: "UP", points: [{ research_id: 30, observed_at: "2026-08-01T12:00:00Z", value: 80, moving_average: 80, percentage_change: null, direction: "STABLE" }, { research_id: 31, observed_at: now, value: 84.7, moving_average: 82.35, percentage_change: 5.9, direction: "UP" }] }] }, knowledge_graph_summary: { id: 3, structure_version: "1.0", node_count: 2, edge_count: 0, created_at: now, nodes: [], edges: [] }, execution_time_ms: 15000, token_usage: 315, cost: 0, explainability: { methodology_version: "1.0", metrics: { visibility_score: { formula: "weighted sum", inputs: { research_id: 31 }, normalization: "bounded 0..100", weight: 1, version: "1.0" }, authority: { inputs: {}, version: "1.0", status: "NOT_CALCULATED_IN_SCORING_V1" } }, prompts: [{ uuid: "prompt-uuid", response_id: 1, text: "Где купить Skinjestique?", language: "ru", country: "RU", provider: "ollama", model: "qwen2.5:3b", created_at: now }], responses: [{ response_id: 1, provider: "ollama", model: "qwen2.5:3b", prompt: "Где купить Skinjestique?", raw_response: { content: "Полный ответ Skinjestique" }, normalized_response: { content: "Полный ответ Skinjestique" }, tokens: 315, cost: 0, latency_ms: 15000, finished_at: now, entity_ids: [1], citation_ids: [], recommendation_ids: [4] }], citations: [], unsupported_metrics: ["authority", "knowledge_graph_score"] } }
      : path.endsWith("/research/31/action-plan") ? { research_id: 31, engine_version: "1.0", generated_at: now, items: [{ recommendation: { id: 4, recommendation_type: "CITATION_AUTHORITY", priority: "HIGH", metric: "citation_score", metric_value: 0, explanation: "Citation Score below 50", expected_effect: "Improve citation" }, template: { title: "Усилить независимые источники", description: "Подготовить публикации в авторитетных отраслевых изданиях", steps: ["Выбрать отраслевые СМИ", "Подготовить подтверждённые материалы"], expected_result: "+18 к цитированию", estimated_time: "2 недели", version: "1.0" }, steps: ["Выбрать отраслевые СМИ", "Подготовить подтверждённые материалы"], expected_effect: "+18 к цитированию", estimated_time: "2 недели" }] }
      : path.endsWith("/research/31/simulation") ? { research_id: 31, model_version: "1.0", simulated_at: now, simulations: [{ recommendation_id: 4, metric: "citation_score", current_metric: 0, expected_metric_change: 18, predicted_visibility: 87.4, predicted_delta: 2.7, confidence_min: 70, confidence_expected: 82, confidence_max: 90, estimated_duration_days: 14, model_version: "1.0" }] }
      : path.endsWith("/research-tasks") ? [] : path.endsWith("/system/health") ? { status: "healthy" } : {};
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
  });
  await page.goto("/reports/latest");
  await page.getByLabel("Email").fill("analyst@example.com");
  await page.getByLabel("Пароль").fill("strong-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Skinjestique" })).toBeVisible();
  await expect(page.getByText("Как сформирована оценка")).toBeVisible();
  await expect(page.getByText(/Источники отсутствуют/)).toBeVisible();
  await expect(page.getByText(/Связи не найдены/)).toBeVisible();
  await expect(page.getByText("Усилить независимые источники")).toBeVisible();
  await expect(page.getByText("+18.0 к «Цитирование»")).toBeVisible();
  await expect(page.getByText("На основании каких запросов рассчитан рейтинг")).toBeVisible();
  await page.getByText("ollama/qwen2.5:3b · ответ #1").click();
  await expect(page.getByText("Где купить Skinjestique?")).toBeVisible();
  await expect(page.getByText("Ответы без сокращений")).toBeVisible();
  await page.screenshot({ path: "../docs/screenshots/BUG-003-after.png", fullPage: true });
});
