import { useEffect, useState } from "react";
import type { ApiClient, GeoSiteAudit } from "./api";

export function SiteImprovementPanel({ api, brand, website, projectId }: {
  api: ApiClient; brand: string; website: string; projectId?: number;
}) {
  const [url, setUrl] = useState(website);
  const [audit, setAudit] = useState<GeoSiteAudit>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    api.geoSiteAudits(projectId).then(items => {
      if (!cancelled) setAudit(items.find(item => item.brand.toLowerCase() === brand.toLowerCase() && item.website_url.replace(/\/$/, "") === website.replace(/\/$/, "")));
    }).catch(() => { if (!cancelled) setError("Не удалось загрузить прошлый аудит. Можно запустить новую проверку."); });
    return () => { cancelled = true; };
  }, [api, brand, website, projectId]);
  async function run() {
    setBusy(true); setError("");
    try { setAudit(await api.runGeoSiteAudit({ brand, website_url: url, project_id: projectId })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось проверить сайт"); }
    finally { setBusy(false); }
  }
  return <section className="analytics-card">
    <h2>Что изменить на сайте</h2>
    <p>Проверяем доступную HTML-страницу, robots.txt и sitemap. Это технический чек-лист, а не оценка вероятности рекомендации Алисой.</p>
    <label>Официальный сайт<input type="url" value={url} onChange={event => setUrl(event.target.value)} placeholder="https://example.ru" /></label>
    <button className="primary-action" disabled={busy || !url.trim()} onClick={run}>{busy ? "Проверяем сайт…" : "Проверить сайт и получить задачи"}</button>
    {error && <p role="alert">{error}</p>}
    {audit && <>
      <p>Проверено: {new Date(audit.created_at).toLocaleString("ru-RU")} · {audit.final_url}</p>
      <p><b>{audit.score} из 100</b> по техническому чек-листу версии {audit.algorithm_version}. Баллы не прибавляются к оценке видимости бренда.</p>
      {audit.checks.filter(check => !check.passed && check.recommendation).slice(0, 3).map(check => <article className="resource-proof" key={check.code}>
        <h3>{check.title}</h3><p><b>Обнаружено:</b> {check.evidence}</p><p><b>Задача:</b> {check.recommendation}</p>
        <p><b>Ответственный:</b> редактор или разработчик сайта. После изменения повторите проверку этого признака.</p>
      </article>)}
      <details><summary>Все проверки и основания оценки</summary>{audit.checks.map(check => <p key={check.code}>
        <b>{check.passed ? "Пройдено" : "Проверить"}: {check.title}</b> · {check.points}/{check.max_points}. {check.evidence} {check.recommendation}
      </p>)}</details><p>{audit.limitation}</p>
    </>}
  </section>;
}
