import type { SourceAnalysis } from "./EvidencePlan";

export function MeasuredSources({ analysis }: { analysis?: SourceAnalysis }) {
  if (!analysis) return null;
  return <section className="analytics-card">
    <h2>Ресурсы из ответов исследования</h2>
    <p>Успешных ответов: {analysis.successful_responses}. Ошибок и пустых ответов исключено: {analysis.excluded_responses}.</p>
    {!analysis.resources.length && <p>В этих ответах ссылки не обнаружены. Основания выбора источников неизвестны; для измерения нужен ответ со ссылками.</p>}
    {analysis.resources.map(source => <article className="resource-proof" key={`${source.provider}/${source.model}/${source.resource}`}>
      <h3>{source.resource}</h3><p>{source.provider} / {source.model} · ссылка указана в {source.with_source} из {source.with_source + source.without_source} ответов ({(100 * source.with_source / Math.max(1, source.with_source + source.without_source)).toFixed(1)}%).</p>
      <p>Бренд упомянут в {source.mentioned_with} ответах со ссылкой на ресурс. Упоминание само по себе не означает рекомендацию.</p>
      <details><summary>Вопросы и конкретные страницы</summary>{source.queries.map(query => <p key={query}>{query}</p>)}{source.urls.filter(url => { try { const parsed = new URL(url); return ["http:", "https:"].includes(parsed.protocol) && !parsed.username; } catch { return false; } }).map(url => <p key={url}><a href={url} target="_blank" rel="noreferrer">{url}</a></p>)}</details>
      <p>Следующее действие: изучить указанные страницы, проверить тематическое соответствие и правила размещения. Повторить эти же вопросы после публикации.</p>
    </article>)}
    <p>{analysis.limitation} Ссылка в тексте модели требует проверки; она не раскрывает скрытые обучающие источники модели. Результаты API модели и пользовательской Алисы учитываются отдельно.</p>
  </section>;
}
