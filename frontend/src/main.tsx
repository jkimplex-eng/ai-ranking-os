import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { ApiClient, type ReportResult, type WizardPayload, type WizardReview } from "./api";
import "./styles.css";

const api = new ApiClient();
const models = [
  ["openai", "gpt-4o-mini"], ["anthropic", "claude-3-5-sonnet"],
  ["gemini", "gemini-1.5-pro"], ["deepseek", "deepseek-chat"],
  ["perplexity", "sonar-pro"], ["mistral", "mistral-large"],
];
const metricMeta = [
  ["Mention", "mention_score"], ["Recommendation", "recommendation_score"],
  ["Citation", "citation_score"], ["Coverage", "coverage_score"],
  ["Confidence", "confidence_score"],
] as const;

type Screen = "home" | "wizard" | "report";
type ReportShape = {
  executive_summary?: string;
  score?: Record<string, number | string>;
  trend?: { points?: Array<Record<string, unknown>> };
  benchmark?: Record<string, unknown>;
  insights?: Array<{ title?: string; explanation?: string }>;
  recommendations?: Array<{ explanation?: string; priority?: string; metric?: string }>;
  detected_entities?: unknown[]; sources?: unknown[];
  latency_ms?: number; token_usage?: number; cost?: number;
};

function valueOf(score: Record<string, number | string>, key: string) {
  const value = Number(score[key] ?? 0);
  return Number.isFinite(value) ? value : 0;
}
function tone(value: number) { return value >= 80 ? "good" : value >= 55 ? "watch" : "critical"; }
function healthLabel(value: number) { return value >= 85 ? "Отлично" : value >= 70 ? "Очень хорошо" : value >= 50 ? "Требует внимания" : "Критично"; }

function Login({ onReady }: { onReady: (name: string) => void }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const tokens = await api.login(email, password); api.setToken(tokens.access_token);
      sessionStorage.setItem("refresh_token", tokens.refresh_token);
      onReady((await api.me()).display_name);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка входа"); }
    finally { setBusy(false); }
  }
  return <main className="login-shell"><section className="login-panel"><div className="logo-mark">AR</div><span className="eyebrow">AI RANKING OS</span><h1>Понимайте, как AI видит ваш бренд</h1><p>Измеряйте присутствие, находите точки роста и превращайте данные в понятный план действий.</p><form onSubmit={submit}><label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required /></label><label>Пароль<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" minLength={8} required /></label>{error && <div className="error" role="alert">{error}</div>}<button type="submit" disabled={busy}>{busy ? "Входим…" : "Войти"}</button></form></section><aside className="login-story"><span>AI visibility, made actionable</span><blockquote>«Не просто следите за рейтингом. Понимайте, что именно изменить, чтобы AI чаще рекомендовал ваш бренд».</blockquote><div className="story-metric"><strong>89.9</strong><span>пример AI Visibility</span></div></aside></main>;
}

function Shell({ user, children, onHome, onLogout }: { user: string; children: React.ReactNode; onHome: () => void; onLogout: () => void }) {
  return <><header className="topbar"><button className="wordmark" onClick={onHome}><span className="logo-mark small">AR</span><span>AI Ranking OS</span></button><nav><button className="nav-link" onClick={onHome}>Обзор</button><button className="nav-link">История</button><button className="nav-link">Рекомендации</button></nav><div className="account"><span className="avatar">{user.slice(0, 1).toUpperCase()}</span><span>{user}</span><button className="icon-button" aria-label="Выйти" onClick={async () => { await api.logout(); onLogout(); }}>↗</button></div></header>{children}</>;
}

function MetricBar({ label, value }: { label: string; value: number }) {
  return <div className="metric-row"><div><span>{label}</span><strong>{value.toFixed(value % 1 ? 1 : 0)}</strong></div><div className="track" aria-label={`${label}: ${value}`}><span className={tone(value)} style={{ width: `${Math.min(value, 100)}%` }} /></div></div>;
}

function Dashboard({ report, onStart, onOpen }: { report?: ReportResult; onStart: () => void; onOpen: () => void }) {
  if (!report) return <main className="page"><section className="welcome"><span className="eyebrow">ДОБРО ПОЖАЛОВАТЬ</span><h1>Что хотите узнать сегодня?</h1><p>Начните с первого исследования — результат появится здесь в виде понятной картины состояния бренда.</p><div className="choice-grid"><button className="choice primary-choice" onClick={onStart}><span className="choice-icon">◎</span><b>Проверить бренд</b><small>Узнать видимость в ответах AI</small><i>Начать →</i></button><button className="choice"><span className="choice-icon">◇</span><b>Исследовать конкурента</b><small>Сравнить позиции и рекомендации</small><i>Скоро</i></button><button className="choice"><span className="choice-icon">↗</span><b>Посмотреть историю</b><small>Следить за динамикой показателей</small><i>Скоро</i></button><button className="choice"><span className="choice-icon">✓</span><b>Открыть рекомендации</b><small>Перейти к плану улучшений</small><i>Скоро</i></button></div></section></main>;
  const data = report.report as ReportShape; const score = data.score ?? {};
  const visibility = valueOf(score, "visibility_score");
  const weakest = metricMeta.map(([label, key]) => ({ label, value: valueOf(score, key) })).sort((a, b) => a.value - b.value)[0];
  return <main className="page"><div className="page-heading"><div><span className="eyebrow">СОСТОЯНИЕ БРЕНДА</span><h1>{report.research.title.replace(/^AI Visibility:\s*/, "")}</h1><p>Последнее исследование · данные обновлены недавно</p></div><button onClick={onStart}>Новое исследование</button></div><section className="dashboard-grid"><article className="hero-score panel"><div className="score-label">AI Visibility</div><div className="score-line"><strong>{visibility.toFixed(2)}</strong><span className={`status ${tone(visibility)}`}>● {healthLabel(visibility)}</span></div><div className="delta good">↑ 4.2 <span>за последний период</span></div><button className="text-action" onClick={onOpen}>Открыть полный отчёт →</button></article><article className="health panel"><div className="section-label">Общее состояние бренда</div><div className="health-ring" style={{ "--score": `${visibility * 3.6}deg` } as React.CSSProperties}><span>{Math.round(visibility)}</span></div><div><h2>{healthLabel(visibility)}</h2><p>Сильное присутствие в AI-ответах. Основной резерв роста — качество подтверждающих источников.</p><div className="problem"><span>Главная проблема</span><b>{weakest.label}</b><em>{weakest.value.toFixed(1)}</em></div></div></article><article className="metrics panel"><div className="section-label">Ключевые показатели</div>{metricMeta.map(([label, key]) => <MetricBar key={key} label={label} value={valueOf(score, key)} />)}</article><Benchmark visibility={visibility} /><Trend visibility={visibility} /></section></main>;
}

function Benchmark({ visibility }: { visibility: number }) {
  return <article className="benchmark panel"><div className="section-head"><div><span className="section-label">Benchmark</span><h2>Позиция относительно рынка</h2></div><span className="badge neutral">Предварительно</span></div>{[["Skinjestique", visibility], ["Среднее рынка", 61], ["Лидеры категории", 95]].map(([name, value]) => <div className="benchmark-row" key={String(name)}><span>{name}</span><div className="track"><i style={{ width: `${value}%` }} /></div><strong>{Number(value).toFixed(0)}</strong></div>)}</article>;
}

function Trend({ visibility }: { visibility: number }) {
  const points = [Math.max(0, visibility - 12), Math.max(0, visibility - 6), visibility];
  const coords = points.map((value, i) => `${18 + i * 132},${150 - value}`).join(" ");
  return <article className="trend panel"><div className="section-head"><div><span className="section-label">Динамика</span><h2>AI Visibility растёт</h2></div><span className="delta good">↑ 8%</span></div><svg viewBox="0 0 300 170" role="img" aria-label="График роста AI Visibility"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#5b8cff" stopOpacity=".35"/><stop offset="1" stopColor="#5b8cff" stopOpacity="0"/></linearGradient></defs><polygon points={`18,160 ${coords} 282,160`} fill="url(#area)"/><polyline points={coords} fill="none" stroke="#6f9cff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>{points.map((value, i) => <circle key={i} cx={18 + i * 132} cy={150 - value} r="5" fill="#09111f" stroke="#8eb0ff" strokeWidth="3" />)}</svg><div className="timeline">{["Июнь", "Июль", "Август"].map((month, i) => <div key={month}><span>{month}</span><strong>{points[i].toFixed(0)}</strong></div>)}</div></article>;
}

function Wizard({ onComplete, onCancel }: { onComplete: (result: ReportResult) => void; onCancel: () => void }) {
  const [step, setStep] = useState(1); const [brand, setBrand] = useState("Skinjestique");
  const [region, setRegion] = useState("GLOBAL"); const [language, setLanguage] = useState("ru");
  const [selected, setSelected] = useState(["openai:gpt-4o-mini"]); const [review, setReview] = useState<WizardReview>();
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const payload = (): WizardPayload => ({ brand, models: selected.map((item) => { const [provider, model] = item.split(":"); return { provider, model }; }), languages: [language], regions: [region], prompt_code: "ai-visibility", research_template_code: "ai-visibility" });
  async function next() { if (step < 4) return setStep(step + 1); setBusy(true); setError(""); try { setReview(await api.review(payload())); setStep(5); } catch (e) { setError(e instanceof Error ? e.message : "Не удалось проверить настройки"); } finally { setBusy(false); } }
  async function run() { setBusy(true); setError(""); try { onComplete(await api.run(payload())); } catch (e) { setError(e instanceof Error ? e.message : "Не удалось запустить исследование"); } finally { setBusy(false); } }
  const titles = ["Как называется бренд?", "Где вы работаете?", "На каком языке искать?", "Какие AI-модели проверить?", "Всё готово к исследованию"];
  return <main className="wizard-page"><button className="back-link" onClick={step === 1 ? onCancel : () => setStep(step - 1)}>← {step === 1 ? "На главную" : "Назад"}</button><div className="stepper">{[1,2,3,4,5].map((n) => <span key={n} className={n <= step ? "active" : ""}>{n < step ? "✓" : n}</span>)}</div><section className="wizard-focus"><span className="eyebrow">ШАГ {step} ИЗ 5</span><h1>{titles[step - 1]}</h1><p>{step === 1 ? "Введите название так, как его видят ваши клиенты." : step === 4 ? "Рекомендуем выбрать минимум три модели для объективной картины." : "Это поможет сделать исследование точнее."}</p>{step === 1 && <label className="hero-field">Название бренда<input autoFocus value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Например, Skinjestique" /></label>}{step === 2 && <div className="option-list">{[["GLOBAL","Весь мир"],["RU","Россия"],["EU","Европа"],["US","США"]].map(([value,label]) => <button className={region === value ? "selected" : ""} onClick={() => setRegion(value)} key={value}><span>{label}</span><small>{value}</small></button>)}</div>}{step === 3 && <div className="option-list">{[["ru","Русский"],["en","English"]].map(([value,label]) => <button className={language === value ? "selected" : ""} onClick={() => setLanguage(value)} key={value}><span>{label}</span><small>{value.toUpperCase()}</small></button>)}</div>}{step === 4 && <div className="model-grid">{models.map(([provider, model]) => { const key=`${provider}:${model}`; return <label className={`model ${selected.includes(key) ? "active" : ""}`} key={key}><input type="checkbox" checked={selected.includes(key)} onChange={() => setSelected((items) => items.includes(key) ? items.filter((x) => x !== key) : [...items,key])}/><span className="provider-icon">{provider.slice(0,1).toUpperCase()}</span><b>{provider}</b><small>{model}</small><i>{selected.includes(key) ? "✓" : "+"}</i></label>; })}</div>}{step === 5 && <div className="review-card"><div><span>Бренд</span><b>{brand}</b></div><div><span>Регион</span><b>{region}</b></div><div><span>Язык</span><b>{language.toUpperCase()}</b></div><div><span>Модели</span><b>{selected.length}</b></div><p>{review?.prompt}</p></div>}{error && <div className="error" role="alert">{error}</div>}<div className="wizard-actions">{step < 5 ? <button onClick={next} disabled={busy || !brand || (step === 4 && !selected.length)}>{busy ? "Проверяем…" : step === 4 ? "Проверить" : "Продолжить"} →</button> : <button onClick={run} disabled={busy}>{busy ? "Собираем ответы…" : "Запустить исследование"}</button>}</div></section></main>;
}

function RecommendationCard({ citation }: { citation: number }) {
  return <article className="action-card"><div className="action-top"><span className="priority">Высокий приоритет</span><span>Источник роста</span></div><h3>Опубликовать экспертные материалы в отраслевых СМИ</h3><p>Добавьте независимо проверяемые публикации и ссылки на бренд в авторитетных источниках.</p><div className="action-meta"><div><span>Ожидаемый эффект</span><b className="good">+{Math.max(8, Math.round((60 - citation) * .68))} Citation</b></div><div><span>Сложность</span><b>Средняя</b></div><div><span>Срок</span><b>2 недели</b></div></div><button className="secondary">Добавить в план</button></article>;
}

function Report({ result, onHome }: { result: ReportResult; onHome: () => void }) {
  const report = result.report as ReportShape; const score = report.score ?? {};
  const visibility = valueOf(score, "visibility_score"); const citation = valueOf(score, "citation_score");
  const strengths = metricMeta.filter(([, key]) => valueOf(score, key) >= 80).map(([label]) => label);
  return <main className="page report-page"><button className="back-link" onClick={onHome}>← К обзору</button><section className="report-hero"><div><span className="eyebrow">EXECUTIVE REPORT · #{result.research.id}</span><h1>{result.research.title}</h1><p>За последний период AI Visibility выросла. Бренд уверенно присутствует в рекомендациях моделей; главное ограничение — недостаток авторитетных цитирований.</p></div><div className="report-score"><span>AI Visibility</span><strong>{visibility.toFixed(1)}</strong><em className="good">↑ 8%</em></div></section><section className="score-strip">{[["Visibility","visibility_score"], ...metricMeta].map(([label,key]) => <div key={key}><span>{label}</span><strong>{valueOf(score,key).toFixed(1)}</strong><i className={tone(valueOf(score,key))}/></div>)}</section><section className="report-layout"><article className="panel strengths"><span className="section-label">TOP STRENGTHS</span><h2>Что уже работает</h2>{strengths.map((item) => <div className="strength" key={item}><span>★★★★★</span><b>{item}</b><small>Сильный сигнал бренда</small></div>)}</article><article className="panel weakness"><span className="section-label">ГЛАВНОЕ ОГРАНИЧЕНИЕ</span><h2>Citation</h2><strong>{citation.toFixed(1)}</strong><p>AI знает и рекомендует бренд, но недостаточно часто подтверждает ответы независимыми источниками.</p><div className="track"><span className="watch" style={{width:`${citation}%`}}/></div></article><article className="panel narrative"><span className="section-label">ЧТО ХОРОШО</span><h2>Ключевые выводы</h2><ul><li>AI рекомендует бренд в целевых запросах</li><li>Высокая узнаваемость названия</li><li>Хорошее покрытие выбранных моделей</li><li>Высокая уверенность в результатах</li></ul></article><article className="panel sources"><span className="section-label">KNOWLEDGE SOURCES</span><h2>Источники знаний</h2><div className="source-number">{report.sources?.length ?? 0}</div><p>источника обнаружено и связано с ответами моделей</p><button className="text-action">Изучить источники →</button></article></section><section className="plan-section"><div className="section-head"><div><span className="eyebrow">ПЛАН ДЕЙСТВИЙ</span><h2>Как улучшить результат</h2></div><span>Горизонт · 3 недели</span></div><RecommendationCard citation={citation}/><div className="weeks">{[["Неделя 1","Подготовить экспертную тему и список отраслевых площадок"],["Неделя 2","Опубликовать материал и обеспечить корректные ссылки"],["Неделя 3","Повторить исследование и измерить изменение Citation"]].map(([week,text],i) => <div key={week}><span>{i+1}</span><div><b>{week}</b><p>{text}</p></div></div>)}</div></section><section className="report-footer panel"><div><span>Сущности</span><b>{report.detected_entities?.length ?? 0}</b></div><div><span>Источники</span><b>{report.sources?.length ?? 0}</b></div><div><span>Время ответа</span><b>{report.latency_ms ?? 0} ms</b></div><div><span>Токены</span><b>{report.token_usage ?? 0}</b></div><div><span>Стоимость</span><b>${report.cost ?? 0}</b></div></section></main>;
}

function Assistant({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return <aside className={`assistant ${open ? "open" : ""}`}><button className="assistant-toggle" onClick={onToggle} aria-label="AI-помощник">✦</button>{open && <div className="assistant-body"><div className="assistant-head"><span className="logo-mark small">AI</span><div><b>Помощник</b><small>Онлайн</small></div><button className="icon-button" onClick={onToggle}>×</button></div><div className="assistant-message"><span>AI</span><p><b>Что означает Citation?</b><br/>Это показатель того, насколько часто ответы AI подтверждаются независимыми и авторитетными источниками. Чем он выше, тем больше доверия к упоминаниям бренда.</p></div><button className="assistant-action">Исправить автоматически</button><div className="assistant-input"><input placeholder="Задайте вопрос об отчёте…"/><button>↑</button></div></div>}</aside>;
}

function App() {
  const [user, setUser] = useState(""); const [screen, setScreen] = useState<Screen>("home");
  const [report, setReport] = useState<ReportResult>(); const [assistant, setAssistant] = useState(false);
  useEffect(() => { if (!user || report) return; api.listResearch().then(async (items) => { const latest=[...items].sort((a,b)=>b.id-a.id)[0]; if (!latest) return; const data=await api.finalReport(latest.id); setReport({research:latest,report_url:`/research/${latest.id}/final-report`,report:data}); }).catch(() => undefined); }, [user, report]);
  const content = useMemo(() => screen === "wizard" ? <Wizard onCancel={() => setScreen("home")} onComplete={(value) => {setReport(value);setScreen("report");}}/> : screen === "report" && report ? <Report result={report} onHome={() => setScreen("home")}/> : <Dashboard report={report} onStart={() => setScreen("wizard")} onOpen={() => setScreen("report")}/>, [screen, report]);
  if (!user) return <Login onReady={setUser}/>;
  return <Shell user={user} onHome={() => setScreen("home")} onLogout={() => {setUser("");setReport(undefined);}}>{content}<Assistant open={assistant} onToggle={() => setAssistant(!assistant)}/></Shell>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App/></StrictMode>);
