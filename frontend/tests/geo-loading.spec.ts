import { expect, test } from "@playwright/test";

test("GEO distinguishes unavailable APIs from empty data and can retry", async ({ page }) => {
  let failed = true;
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = [];
    if (path.endsWith("/auth/login") || path.endsWith("/auth/refresh")) json = {access_token: "access", refresh_token: "refresh-token-with-valid-length"};
    else if (path.endsWith("/auth/me")) json = {id: 5, display_name: "Owner", email: "owner@example.org", roles: ["analyst"]};
    else if (path.endsWith("/research")) json = [{id: 69, title: "разуммаркета", status: "COMPLETED", metadata: {brand: "разуммаркета", website_url: "https://example.org", query_catalog: []}}];
    else if (path.endsWith("/final-report")) json = {yandex_generative_evidence: {source_patterns: [], limitations: ["Нет запросов Wordstat для замера."]}};
    else if (path.endsWith("/yandex-wordstat/status") || path.endsWith("/automation/dashboard")) {
      if (failed) return route.fulfill({status: 503, json: {detail: "Сервис временно недоступен"}});
      json = path.endsWith("/status") ? {connected: true} : {plans: [], latest_runs: [], methodology: {}};
    }
    else if (path.endsWith("/latest") || path.endsWith("/analytics")) return route.fulfill({status: 404, json: {detail: "Нет снимка"}});
    else if (path.endsWith("/alice-learning/dashboard")) json = {observation_count: 0, top_factors: [], recommended_actions: [], limitations: []};
    else if (path.endsWith("/system/health")) json = {status: "healthy"};
    await route.fulfill({status: 200, json});
  });
  await page.goto("/geo-opportunities");
  await page.getByLabel("Email").fill("owner@example.org");
  await page.getByLabel("Пароль", {exact: true}).fill("strong-password");
  await page.getByRole("button", {name: "Войти", exact: true}).click();
  await expect(page.getByText("Не удалось загрузить мониторинг", {exact: true})).toBeVisible();
  await expect(page.getByText("Не удалось загрузить Wordstat", {exact: true})).toBeVisible();
  await expect(page.getByText("Для разуммаркета мониторинг ещё не включён", {exact: true})).toHaveCount(0);
  await expect(page.getByRole("button", {name: "Включить проверку разуммаркета"})).toBeDisabled();
  await expect(page.getByText("Нет запросов Wordstat для замера.", {exact: true})).toBeVisible();
  const brand = page.locator('.geo-audit-intro > label').filter({hasText: "Бренд"}).locator("input");
  await expect(brand).toHaveValue("разуммаркета");
  failed = false;
  await page.getByRole("button", {name: "Повторить загрузку данных"}).click();
  await expect(page.getByText("Подключён — можно получать реальные данные спроса.", {exact: true})).toBeVisible();
  await expect(page.getByRole("button", {name: "Включить проверку разуммаркета"})).toBeEnabled();
  await expect(page.getByText("Для разуммаркета мониторинг ещё не включён", {exact: true})).toBeVisible();
});
