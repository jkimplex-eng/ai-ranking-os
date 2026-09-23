import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";

test("downloaded plan keeps evidence and refuses unsafe links", async ({ page }) => {
  const research = { id: 42, title: "AI Visibility: Brand", status: "COMPLETED", created_at: "2026-09-01T00:00:00Z" };
  const action = {
    id: "source-42", channel: "EARNED_MEDIA", resource: "example.org",
    reason: "Источник указан в сохранённом ответе.",
    deliverable: "Подготовить авторский материал.", affected_metric: "citation_score",
    expected_effect_range: [], confidence: 0, effort: "MEDIUM", estimated_days: 0,
    verification: "Повторить те же вопросы.", causality_notice: "Причинность не доказана.",
    owner: "Редактор", prerequisites: "Проверить правила редакции.",
    evidence: [{
      response_id: 7, query: "Где купить Brand?", provider: "yandex", model: "api",
      mentioned: true, competitors: ["Other"], answer: "<script>alert(1)</script>",
      urls: ["javascript:alert(1)", "https://example.org/article"],
    }],
  };
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/auth/login") || path.endsWith("/auth/refresh"))
      json = { access_token: "access", refresh_token: "refresh-token-with-valid-length" };
    else if (path.endsWith("/auth/me"))
      json = { id: 1, display_name: "Owner", email: "owner@example.com", roles: ["superadmin"] };
    else if (path.endsWith("/research")) json = [research];
    else if (path.endsWith("/research/42/final-report"))
      json = {
        research, score: { visibility_score: 35, mention_score: 50, recommendation_score: 0,
          citation_score: 0, coverage_score: 100, confidence_score: 80, version: "3.0" },
        responses: [], sources: [{ url: "javascript:alert(1)", title: "Unsafe" }],
        geo_opportunities: [action],
      };
    else if (path.endsWith("/system/health")) json = { status: "healthy" };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
  });
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Пароль", { exact: true }).fill("strong-password");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page.getByRole("button", { name: /Скачать план действий/ })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /Скачать план действий/ }).click();
  const download = await downloadPromise;
  const html = await readFile(await download.path(), "utf8");
  expect(html).toContain("API-модели: 35.0 из 100 · генеративный поиск Яндекса не измерен");
  expect(html).toContain("Редактор");
  expect(html).toContain("Сохранённый ответ");
  expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
  expect(html).toContain('href="https://example.org/article"');
  expect(html).not.toContain('href="javascript:');
  expect(html).not.toContain("Единая GEO-оценка");
});

test("partial Yandex measurement shows the recommendation denominator and failures", async ({ page }) => {
  const research = { id: 43, title: "AI Visibility: Brand", status: "COMPLETED", created_at: "2026-09-01T00:00:00Z" };
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/auth/login") || path.endsWith("/auth/refresh"))
      json = { access_token: "access", refresh_token: "refresh-token-with-valid-length" };
    else if (path.endsWith("/auth/me"))
      json = { id: 1, display_name: "Owner", email: "owner@example.com", roles: ["superadmin"] };
    else if (path.endsWith("/research")) json = [research];
    else if (path.endsWith("/research/43/final-report"))
      json = {
        research, score: { visibility_score: 20, mention_score: 0, recommendation_score: 0,
          citation_score: 0, coverage_score: 100, confidence_score: 50, version: "3.0" },
        responses: [], sources: [],
        yandex_generative_evidence: {
          status: "PARTIAL", visibility_score: 100, queries_measured: 1, queries_failed: 1,
          recommendation_count: 1, recommendation_rate_percent: 100,
          mention_count: 1, target_citation_count: 1,
          sample_scope: { requested_queries: 2, measured_answers: 1, failed_queries: 1,
            confidence_status: "INSUFFICIENT_SAMPLE", limitation: "Только эта выборка" },
          observations: [], source_patterns: [], limitations: ["Только эта выборка"],
        },
      };
    else if (path.endsWith("/research/43/simulation")) json = { simulations: [] };
    else if (path.endsWith("/research/43/action-plan")) json = { items: [] };
    else if (path.endsWith("/system/health")) json = { status: "healthy" };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
  });
  await page.goto("/reports/latest");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Пароль", { exact: true }).fill("strong-password");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page.getByText("В генеративном поиске Яндекса бренд рекомендован в 1 из 1 полученных ответов (100.0%).")).toBeVisible();
  await expect(page.getByText("Частичный замер: 1 запросов завершились ошибкой и не входят в знаменатель.")).toBeVisible();
  await expect(page.getByText("Малая выборка: результат нельзя считать устойчивой оценкой за пределами этих вопросов.")).toBeVisible();
});
