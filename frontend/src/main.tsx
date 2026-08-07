import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { ApiClient, type ReportResult, type WizardPayload, type WizardReview } from "./api";
import "./styles.css";

const api = new ApiClient();
const availableModels = [
  ["openai", "gpt-4o-mini"],
  ["anthropic", "claude-3-5-sonnet"],
  ["gemini", "gemini-1.5-pro"],
  ["deepseek", "deepseek-chat"],
  ["perplexity", "sonar-pro"],
  ["mistral", "mistral-large"],
];

function Login({ onReady }: { onReady: (name: string) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const tokens = await api.login(email, password);
      api.setToken(tokens.access_token);
      sessionStorage.setItem("refresh_token", tokens.refresh_token);
      const user = await api.me();
      onReady(user.display_name);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка входа");
    }
  }
  return <main className="login"><section className="card"><span className="eyebrow">AI RANKING OS</span><h1>Войдите в рабочее пространство</h1><p>Исследуйте, как AI-модели видят и рекомендуют ваш бренд.</p><form onSubmit={submit}><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required /></label>{error && <div className="error">{error}</div>}<button type="submit">Войти</button></form></section></main>;
}

function Wizard({ user }: { user: string }) {
  const [brand, setBrand] = useState("Skinjestique");
  const [selected, setSelected] = useState(["openai:gpt-4o-mini"]);
  const [language, setLanguage] = useState("en");
  const [region, setRegion] = useState("GLOBAL");
  const [review, setReview] = useState<WizardReview>();
  const [result, setResult] = useState<ReportResult>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const payload = (): WizardPayload => ({
    brand,
    models: selected.map((item) => {
      const [provider, model] = item.split(":");
      return { provider, model };
    }),
    languages: [language],
    regions: [region],
    prompt_code: "ai-visibility",
    research_template_code: "ai-visibility",
  });
  async function check() {
    setBusy(true); setError("");
    try { setReview(await api.review(payload())); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка проверки"); }
    finally { setBusy(false); }
  }
  async function run() {
    setBusy(true); setError("");
    try { setResult(await api.run(payload())); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка запуска"); }
    finally { setBusy(false); }
  }
  if (result) return <Report result={result} />;
  return <><header><div><span className="brand">AI Ranking OS</span><span className="badge">Production</span></div><span>{user}</span></header><main className="workspace"><div className="intro"><span className="eyebrow">НОВОЕ ИССЛЕДОВАНИЕ</span><h1>Где ваш бренд в ответах AI?</h1><p>Выберите модели — платформа автоматически соберёт ответы, извлечёт сигналы и подготовит отчёт.</p></div><section className="wizard card"><label>Бренд<input value={brand} onChange={(event) => setBrand(event.target.value)} required /></label><div><span className="label">AI-модели</span><div className="model-grid">{availableModels.map(([provider, model]) => { const key = `${provider}:${model}`; return <label className={`model ${selected.includes(key) ? "active" : ""}`} key={key}><input type="checkbox" checked={selected.includes(key)} onChange={() => setSelected((items) => items.includes(key) ? items.filter((item) => item !== key) : [...items, key])} /><b>{provider}</b><small>{model}</small></label>; })}</div></div><div className="row"><label>Язык<select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">English</option><option value="ru">Русский</option></select></label><label>Регион<select value={region} onChange={(event) => setRegion(event.target.value)}><option>GLOBAL</option><option>RU</option><option>US</option><option>EU</option></select></label></div>{review && <div className="review"><b>{review.title}</b><p>{review.prompt}</p><small>{review.pipeline.join(" → ")}</small></div>}{error && <div className="error">{error}</div>}<div className="actions"><button className="secondary" onClick={check} disabled={busy || !selected.length}>Проверить</button><button onClick={run} disabled={busy || !review?.valid}>{busy ? "Выполняется…" : "Запустить исследование"}</button></div></section></main></>;
}

function Report({ result }: { result: ReportResult }) {
  const report = result.report as { executive_summary?: string; score?: Record<string, number | string>; insights?: Array<{ title?: string; explanation?: string }>; recommendations?: Array<{ explanation?: string; priority?: string }>; detected_entities?: unknown[]; sources?: unknown[]; latency_ms?: number; token_usage?: number; cost?: number };
  const score = report.score ?? {};
  const metrics = [["Visibility", score.visibility_score], ["Mention", score.mention_score], ["Recommendation", score.recommendation_score], ["Citation", score.citation_score], ["Coverage", score.coverage_score], ["Confidence", score.confidence_score]];
  return <><header><div><span className="brand">AI Ranking OS</span><span className="badge">Report #{result.research.id}</span></div><span className="success">{result.research.status}</span></header><main className="report"><span className="eyebrow">AI VISIBILITY REPORT</span><h1>{result.research.title}</h1><p className="summary">{report.executive_summary}</p><section className="score-grid">{metrics.map(([name, value]) => <div className="metric card" key={String(name)}><small>{name}</small><strong>{String(value ?? "—")}</strong></div>)}</section><section className="report-grid"><div className="card"><h2>Insights</h2>{report.insights?.length ? report.insights.map((item, index) => <p key={index}><b>{item.title}</b><br />{item.explanation}</p>) : <p>Значимых отклонений не обнаружено.</p>}</div><div className="card"><h2>Recommendations</h2>{report.recommendations?.length ? report.recommendations.map((item, index) => <p key={index}><span className="badge">{item.priority}</span> {item.explanation}</p>) : <p>Критических рекомендаций нет.</p>}</div></section><section className="card stats"><h2>Выполнение</h2><div><span>Сущности <b>{report.detected_entities?.length ?? 0}</b></span><span>Источники <b>{report.sources?.length ?? 0}</b></span><span>Latency <b>{report.latency_ms ?? 0} ms</b></span><span>Tokens <b>{report.token_usage ?? 0}</b></span><span>Cost <b>${report.cost ?? 0}</b></span></div></section></main></>;
}

function App() {
  const [user, setUser] = useState("");
  return user ? <Wizard user={user} /> : <Login onReady={setUser} />;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
