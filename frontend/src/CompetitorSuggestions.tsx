import { useEffect, useState } from "react";
import type { ApiClient } from "./api";

export function CompetitorSuggestions({ api, projectId, onSelect }: { api: ApiClient; projectId: number; onSelect: (name: string) => void }) {
  const [items, setItems] = useState<Awaited<ReturnType<ApiClient["competitorSuggestions"]>>>([]);
  const [status, setStatus] = useState("Ищем компании в ответах исследований…");
  useEffect(() => {
    let active = true;
    setItems([]); setStatus("Ищем компании в ответах исследований…");
    api.competitorSuggestions(projectId).then(result => {
      if (active) { setItems(result); setStatus(result.length ? "" : "Новых кандидатов пока нет. Завершите исследование этого проекта; компании из ответов появятся здесь автоматически."); }
    }).catch(error => { if (active) setStatus(error instanceof Error ? error.message : "Не удалось загрузить кандидатов"); });
    return () => { active = false; };
  }, [api, projectId]);
  return <section className="analytics-card"><h2>Кого ИИ называет в ваших запросах</h2><p role="status">{status}</p>{items.map(item => <article className="resource-proof" key={item.name}>
    <h3>{item.name}</h3><p>Найден в {item.evidence.length} ответах. {item.limitation}</p>
    <details><summary>Посмотреть доказательства</summary>{item.evidence.map(row => <p key={`${row.research_id}:${row.response_id}`}>Исследование #{row.research_id}, ответ #{row.response_id} · {row.provider}/{row.model}<br />{row.query}<br />{row.urls.join(" · ")}</p>)}</details>
    <button className="secondary" onClick={() => onSelect(item.name)}>Выбрать для наблюдения</button>
  </article>)}</section>;
}
