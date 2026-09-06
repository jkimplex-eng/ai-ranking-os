export type EvidenceAction = {
  id: string; channel: string; resource: string; reason: string; deliverable: string;
  affected_metric: string; expected_effect_range: number[]; confidence: number;
  effort: string; estimated_days: number; verification: string; causality_notice: string;
  owner?: string; prerequisites?: string; evidence_count?: number; effect_explanation?: string;
  evidence?: Array<{response_id: number; query: string; provider: string; model: string;
    mentioned: boolean; competitors: string[]; urls: string[]; answer?: string}>;
};

function safeUrl(value: string) {
  try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) && !url.username; }
  catch { return false; }
}

export type SourceAnalysis = {
  successful_responses: number; excluded_responses: number; method: string;
  limitation: string; next_step: string;
  resources: Array<{resource: string; provider: string; model: string; with_source: number;
    without_source: number; mentioned_with: number; mentioned_without: number;
    status: string; queries: string[]; urls: string[]}>;
};

export function EvidencePlan({ actions, sources }: { actions: EvidenceAction[]; sources?: SourceAnalysis }) {
  const card = (action: EvidenceAction, index: number) => <article className="analytics-card recommendation-detail" key={action.id}>
    <header><h2>{index + 1}. {action.resource}</h2><span>{index < 3 ? "В первую очередь" : "Следующий шаг"}</span></header>
    <div className="recommendation-logic">
      <div><b>Что обнаружили</b><p>{action.reason}</p></div>
      <div><b>Что сделать</b><p>{action.deliverable}</p></div>
      <div><b>Кто отвечает</b><p>{action.owner ?? "Назначьте ответственного"}</p></div>
    </div>
    <p><b>Перед началом:</b> {action.prerequisites ?? "Проверьте исходные данные и условия площадки."}</p>
    <p><b>Как измерить пользу:</b> {action.verification}</p>
    <p className="method-note">{action.effect_explanation ?? "Прирост оценки не установлен. Сначала требуется повторное измерение."}</p>
    <details><summary>На чём основан совет · {action.evidence?.length ?? 0} ответов</summary>
      {action.evidence?.length ? action.evidence.map(row => <div className="resource-proof" key={row.response_id}>
        <h3>{row.query}</h3><p>{row.provider} / {row.model} · ответ #{row.response_id} · {row.mentioned ? "бренд упомянут" : "бренд не упомянут"}</p>
        {row.answer && <details><summary>Прочитать исходный ответ</summary><p style={{whiteSpace: "pre-wrap"}}>{row.answer}</p></details>}
        {row.competitors.length > 0 && <p>Названы компании: {row.competitors.join(", ")}. Это не автоматически рекомендация.</p>}
        {row.urls.filter(safeUrl).map(url => <a href={url} key={url} target="_blank" rel="noreferrer">{url}</a>)}
        {!row.urls.length && <p>Проверяемая ссылка в этом ответе отсутствует.</p>}
      </div>) : <p>Доказательств для конкретной площадки пока нет: это задача по сбору данных, а не рекомендация размещения.</p>}
    </details>
    <small>{action.causality_notice}</small>
  </article>;
  return <section aria-label="Доказательный план действий">
    <h2>Три приоритетных действия</h2>
    <p>Выполните применимые задачи и сохраните дату и ссылку на изменение. Ненужные задачи не добавляются ради количества.</p>
    {actions.slice(0, 3).map(card)}
    {actions.length > 3 && <details><summary>Остальной план · {actions.length - 3}</summary>{actions.slice(3).map((action, index) => card(action, index + 3))}</details>}
    <aside className="analytics-card"><h3>Что мы знаем о выборе источников</h3>
      <p>Ссылки показывают, какие ресурсы указаны в сохранённых ответах. Они не раскрывают закрытый алгоритм Алисы и не доказывают, что публикация вызвала рекомендацию.</p>
      <p>Для проверки гипотез нужны повторные наблюдения по тем же вопросам, региону и модели, история публикаций и сравнение с вопросами без изменений. Ответы API-моделей учитываются отдельно от пользовательской Алисы.</p>
      {sources && <details><summary>Разобрать источники и расчёт · {sources.resources.length} наблюдений по ресурсам и моделям</summary>
        <p>{sources.method}</p><p>Успешных ответов: {sources.successful_responses}. Исключено ошибок и пустых ответов: {sources.excluded_responses}.</p>
        {!sources.resources.length && <p>В ответах нет проверяемых ссылок. По этой выборке нельзя определить используемые ресурсы.</p>}
        {sources.resources.map(source => <article key={`${source.provider}/${source.model}/${source.resource}`} className="resource-proof">
          <h3>{source.resource}</h3><p>{source.provider} / {source.model}</p>
          <p>Со ссылкой на ресурс: бренд упомянут в {source.mentioned_with} из {source.with_source} ответов. Без ссылки: {source.mentioned_without} из {source.without_source}.</p>
          <p>{source.status === "INSUFFICIENT_COMPARISON" ? "Недостаточно ответов в сравниваемых группах. Вывод о влиянии не делаем." : "Есть данные для описательного сравнения. Причина выбора ресурса не установлена."}</p>
          <details><summary>Вопросы и страницы</summary><ul>{source.queries.map(query => <li key={query}>{query}</li>)}</ul>
            {source.urls.filter(safeUrl).map(url => <p key={url}><a href={url} target="_blank" rel="noreferrer">{url}</a></p>)}
          </details>
        </article>)}
        <p>{sources.limitation}</p><p>{sources.next_step}</p>
      </details>}
    </aside>
  </section>;
}
