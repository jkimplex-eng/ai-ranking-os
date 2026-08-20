import { expect, test } from "@playwright/test";

test("login page exposes product entry point", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Понимайте, как AI видит ваш бренд" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
});

test("competitor center adds a brand and shows evidence-based daily analytics", async ({ page }) => {
  let projectCreated = false;
  let competitorCreated = false;
  const dashboard = () => ({
    project_id: 10,
    monitoring_enabled: false,
    methodology: "COMPETITOR_OBSERVATION_V1",
    limitation: "Значимость отражает наблюдаемую связь и не доказывает причинное влияние.",
    competitors: competitorCreated ? [{
      competitor_id: 22,
      name: "Librederm",
      domains: ["librederm.ru"],
      active: true,
      latest_visibility_score: 66.5,
      visibility_delta: 4.2,
      snapshots: [{
        snapshot_date: "2026-08-20",
        research_count: 1,
        response_count: 8,
        mention_count: 5,
        recommendation_count: 3,
        citation_count: 2,
        source_count: 1,
        observed_visibility_score: 66.5,
        algorithm_version: "1.0",
      }],
      publications: [{
        url: "https://beauty.example/serums",
        domain: "beauty.example",
        title: "Обзор сывороток",
        observation_count: 3,
        provider_count: 2,
        research_count: 2,
        mention_observations: 3,
        recommendation_observations: 2,
        significance_score: 58,
        significance_label: "Средняя",
        first_seen_at: "2026-08-19T10:00:00Z",
        last_seen_at: "2026-08-20T10:00:00Z",
        evidence_level: "OBSERVATION",
        explanation: "Источник встречался вместе с конкурентом в 3 ответах.",
      }],
    }] : [],
  });
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let status = 200;
    let json: unknown = {};
    if (path.endsWith("/auth/login")) json = { access_token: "access", refresh_token: "refresh-token-with-valid-length" };
    else if (path.endsWith("/auth/me")) json = { id: 1, display_name: "Admin", email: "admin@example.com", roles: ["superadmin"] };
    else if (path.endsWith("/workspace/projects") && request.method() === "POST") {
      projectCreated = true;
      status = 201;
      json = { id: 10, name: "Skinjestique", description: "", research_count: 0 };
    } else if (path.endsWith("/workspace/projects")) {
      json = projectCreated ? [{ id: 10, name: "Skinjestique", description: "", research_count: 0 }] : [];
    }
    else if (path.endsWith("/workspace/projects/10/competitors") && request.method() === "POST") {
      competitorCreated = true;
      status = 201;
      json = { id: 22, project_id: 10, name: "Librederm", domains: ["librederm.ru"], brands: [], notes: "", active: true };
    } else if (path.includes("/competitor-intelligence/projects/10")) json = dashboard();
    else if (path.endsWith("/research") || path.endsWith("/providers")) json = [];
    else if (path.endsWith("/system/health")) json = { status: "healthy" };
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(json) });
  });

  await page.goto("/");
  await page.getByLabel("Email").fill("admin@example.com");
  await page.getByLabel("Пароль").fill("strong-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await page.getByRole("button", { name: "Конкуренты" }).click();
  await page.getByLabel("Название проекта").fill("Skinjestique");
  await page.getByRole("button", { name: "Создать и продолжить" }).click();
  await page.getByLabel("Название").fill("Librederm");
  await page.getByLabel("Сайт").fill("librederm.ru");
  await page.getByRole("button", { name: "Добавить конкурента" }).click();

  await expect(page.getByRole("heading", { name: "Librederm" })).toBeVisible();
  await expect(page.getByText("66.5")).toBeVisible();
  await expect(page.getByRole("link", { name: "Обзор сывороток" })).toBeVisible();
  await expect(page.getByText(/не доказывает причинное влияние/)).toBeVisible();
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
          query_catalog: [{ id: "q-1", cluster: "category", intent: "buyer", text: "Какую увлажняющую сыворотку выбрать?" }],
          task_count: 1,
        };
      }
    } else if (path.endsWith("/research/wizard/brand-profile")) {
      json = { version: "1.0", brand: "Acme", website_url: "https://acme.example", pages_analyzed: 2, evidence_urls: ["https://acme.example"], description: "Acme", categories: ["Сыворотки"], products: [{ name: "Hydra Serum" }], attributes: ["увлажняющий"], confidence: .7, limitations: [] };
    } else if (path.endsWith("/router/models")) {
      json = { items: [{ id: "qwen-test", provider: "ollama", display_name: "Qwen", version: "2.5", status: "ACTIVE", tier: "FREE", capabilities: ["chat"], availability: 1, pricing: { input_per_million: 0, output_per_million: 0 } }], total: 1 };
    } else if (path.endsWith("/system/providers")) {
      json = { providers: [{ model_id: "qwen-test", provider: "ollama", latency_ms: 20, circuit_state: "CLOSED", interface: { available: true, mock: false, models: 2 } }] };
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
  await page.getByLabel("Официальный сайт").fill("https://acme.example");
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Qwen/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: "Проверить" }).click();

  await expect(page.getByLabel("Запрос 1")).toHaveValue("Какую увлажняющую сыворотку выбрать?");
  expect(refreshed).toBe(true);
  expect(reviewAttempts).toBe(2);
});

test("wizard recovers a completed research after the run connection is lost", async ({ page }) => {
  let researchPolls = 0;
  let runAttempted = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/research/wizard/run")) {
      runAttempted = true;
      return route.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ detail: "Failed to fetch" }) });
    }
    let json: unknown = {};
    if (path.endsWith("/auth/login")) json = { access_token: "access", refresh_token: "refresh-token-with-valid-length" };
    else if (path.endsWith("/auth/me")) json = { id: 1, display_name: "Analyst", email: "analyst@example.com", roles: ["analyst"] };
    else if (path.endsWith("/router/models")) json = { items: [{ id: "local-llama", provider: "ollama", display_name: "Qwen", version: "2.5", status: "ACTIVE", tier: "FREE", capabilities: ["chat"], availability: 1, pricing: { input_per_million: 0, output_per_million: 0 } }], total: 1 };
    else if (path.endsWith("/system/providers")) json = { providers: [{ model_id: "local-llama", provider: "ollama", latency_ms: 20, circuit_state: "CLOSED", interface: { available: true, mock: false, models: 2 } }] };
    else if (path.endsWith("/research/wizard/review")) json = { valid: true, title: "AI Visibility: Acme", prompt: "Analyze Acme", provider_models: ["ollama/local-llama"], selected_models: ["ollama/local-llama"], languages: ["ru"], regions: ["RU"], pipeline: [], estimated_cost_usd: 0, estimated_time_ms: 2400, query_catalog: [], task_count: 8 };
    else if (path.endsWith("/research/wizard/brand-profile")) json = { version: "1.0", brand: "Acme", website_url: "https://acme.example", pages_analyzed: 2, evidence_urls: ["https://acme.example"], description: "Acme", categories: ["Сыворотки"], products: [{ name: "Hydra Serum" }], attributes: ["увлажняющий"], confidence: .7, limitations: [] };
    else if (path.endsWith("/research")) {
      researchPolls += 1;
      json = runAttempted ? [{ id: 77, title: "AI Visibility: Acme", status: "COMPLETED" }] : [];
    } else if (path.endsWith("/research/77/final-report")) json = { research: { id: 77, title: "AI Visibility: Acme", status: "COMPLETED" }, score: { visibility_score: 52, mention_score: 50, recommendation_score: 50, citation_score: 0, coverage_score: 100, confidence_score: 70, version: "1.1" }, responses: [], recommendations: [], sources: [], detected_entities: [], explainability: { metrics: {}, prompts: [], responses: [], citations: [], sample_scope: { query_count: 8, response_count: 8, successful_response_count: 8 } } };
    else if (path.endsWith("/research/77/action-plan")) json = { research_id: 77, engine_version: "1.0", generated_at: "2026-08-12T00:00:00Z", items: [] };
    else if (path.endsWith("/research/77/simulation")) json = { research_id: 77, model_version: "1.0", simulated_at: "2026-08-12T00:00:00Z", simulations: [] };
    else if (path.endsWith("/research/77/laboratory")) json = { provenance: {}, models: [], sources: [], entities: [], graph: { status: "EMPTY", nodes: [], edges: [] }, timeline: [], publications: [] };
    else if (path.endsWith("/research-tasks")) json = [];
    else if (path.endsWith("/system/health")) json = { status: "healthy" };
    else if (path.endsWith("/providers")) json = [];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
  });

  await page.goto("/");
  await page.getByLabel("Email").fill("analyst@example.com");
  await page.getByLabel("Пароль").fill("strong-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await page.getByRole("button", { name: "Проверить бренд" }).click();
  await page.getByLabel("Название бренда").fill("Acme");
  await page.getByLabel("Официальный сайт").fill("https://acme.example");
  for (let step = 1; step <= 3; step += 1) await page.getByRole("button", { name: /Продолжить/ }).click();
  await page.getByRole("button", { name: /Qwen/ }).click();
  for (let step = 1; step <= 4; step += 1) await page.getByRole("button", { name: /Продолжить|Проверить/ }).click();
  await page.getByRole("button", { name: "Запустить исследование" }).click();

  await expect(page).toHaveURL(/\/reports\/latest$/);
  await expect(page.getByRole("heading", { name: "Acme" })).toBeVisible();
  expect(researchPolls).toBeGreaterThan(1);
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
        : path.endsWith("/geo/platforms") || path.endsWith("/geo/prompt-sets") || path.endsWith("/publication-learning/influence")
          ? []
        : path.endsWith("/workspace")
          ? { id: 1, name: "Workspace", settings: {} }
          : path.endsWith("/router/status")
            ? { status: "ok", costs: {} }
          : path.endsWith("/router/history")
            ? { items: [], total: 0 }
          : path.endsWith("/provider-connections")
            ? []
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
    ["GEO-площадки", "/geo-opportunities", "Где публиковаться, чтобы вас рекомендовали ИИ"],
    ["Конкуренты", "/competitors", "Конкуренты"],
    ["История", "/history", "История"],
    ["Провайдеры ИИ", "/providers", "Провайдеры ИИ"],
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

test("GEO screen exposes real platform scoring and explainability", async ({ page }) => {
  const platform = { id: "platform-1", name: "Отраслевое СМИ", domain: "media.example", platform_type: "PUBLICATION", category: "BEAUTY", country: "RU", language: "ru", ai_engines: [], domain_trust: 82, topical_authority_score: 76, ai_citation_history: 12, cost_per_placement: 25000, evidence: { source: "USER_INPUT" }, active: true, created_at: "2026-08-19T00:00:00Z", updated_at: "2026-08-19T00:00:00Z" };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = {};
    let status = 200;
    if (path.endsWith("/auth/login")) json = { access_token: "access", refresh_token: "refresh-token-with-valid-length" };
    else if (path.endsWith("/auth/me")) json = { id: 1, display_name: "Analyst", email: "analyst@example.com", roles: ["analyst"] };
    else if (path.endsWith("/geo/platforms") && route.request().method() === "POST") { json = platform; status = 201; }
    else if (path.endsWith("/geo/platforms")) json = [platform];
    else if (path.endsWith("/geo/prompt-sets")) json = [{ id: "set-1", code: "beauty-core", version: 1, name: "Beauty Core", category: "BEAUTY", language: "ru", region: "RU", fingerprint: "0123456789abcdef", frozen: true, active: true, templates: [{ key: "category", query_type: "CATEGORY", template: "Какую {category} выбрать?" }], instances: [], created_at: "2026-08-19T00:00:00Z" }];
    else if (path.endsWith("/publication-learning/influence")) json = [{ id: 7, resource_domain: "media.example", channel: "EARNED", content_type: "ARTICLE", metric: "visibility_score", provider: "ALL", model: "ALL", category: "BEAUTY", language: "ru", region: "RU", sample_size: 3, expected_delta: 12.4, confidence_min: 4.1, confidence_max: 20.7, confidence_score: .71, evidence_grade: "MODERATE", evidence_level: "CORRELATION", positive_experiments: 3, negative_experiments: 0, neutral_experiments: 0, controlled_experiments: 2, effect_method: "MIXED_EVIDENCE_V1", last_observed_at: "2026-08-19T00:00:00Z", limitations: ["Correlation only"], algorithm_version: "1.2" }];
    else if (path.endsWith("/v1/eis/batch-prioritize")) json = { methodology_version: "heuristic_v1.0", limitations: ["Correlation-based estimates; no causal effect is claimed."], items: [{ cost_efficiency: 0.0034, score: { id: "score-1", platform_id: "platform-1", ai_engine: "YandexGPT", eis_value: 84.6, priority: "P1", evidence_status: "PARTIAL", methodology_version: "heuristic_v1.0", weight_set_version: "geo-eis-v1", explanation: {}, calculated_at: "2026-08-19T00:00:00Z", components: { authority: { value: 81, numerator: 81, denominator: 1, inputs: {}, weights: {}, exclusions: [] }, match: { value: 76, numerator: 76, denominator: 1, inputs: {}, weights: {}, exclusions: ["cep_coverage"] }, content: { value: 90, numerator: 90, denominator: 1, inputs: {}, weights: {}, exclusions: [] } } } }] };
    else if (path.endsWith("/research") || path.endsWith("/providers")) json = [];
    else if (path.endsWith("/system/health")) json = { status: "healthy" };
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(json) });
  });
  await page.goto("/geo-opportunities");
  await page.getByLabel("Email").fill("analyst@example.com");
  await page.getByLabel("Пароль").fill("strong-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Где публиковаться, чтобы вас рекомендовали ИИ" })).toBeVisible();
  await expect(page.getByText("Отраслевое СМИ")).toBeVisible();
  await expect(page.getByText("Beauty Core")).toBeVisible();
  await expect(page.getByText("Что уже повлияло на ответы ИИ")).toBeVisible();
  await expect(page.getByText("С КОНТРОЛЬНОЙ ГРУППОЙ")).toBeVisible();
  await expect(page.getByText("+12.4")).toBeVisible();
  await page.getByRole("button", { name: "Рассчитать приоритет" }).click();
  await expect(page.getByText("84.6")).toBeVisible();
  await expect(page.getByText("частичные данные")).toBeVisible();
  await expect(page.getByText(/не выдаёт корреляцию за доказанную причинность/)).toBeVisible();
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
