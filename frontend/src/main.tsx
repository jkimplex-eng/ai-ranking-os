import { StrictMode, useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ApiClient,
  type ActionPlanItem,
  type AuthProfile,
  type AdminAudit,
  type AdminFeedback,
  type AdminUser,
  type CompetitorItem,
  type FeedbackItem,
  type GraphSnapshot,
  type ProductAnalyticsDashboard as AnalyticsDashboard,
  type NotificationItem,
  type OrganizationItem,
  type ProviderItem,
  type RecommendationItem,
  type ReportCatalogItem,
  type ReportResult,
  type ResearchItem,
  type RouterHistoryItem,
  type SimulationItem,
  type SystemProviderItem,
  type WorkspaceProjectItem,
  type WizardPayload,
  type WizardReview,
} from "./api";
import {
  AreaLineChart,
  RadarChart,
} from "./charts";
import {
  Badge,
  Button,
  ChartContainer,
  Drawer,
  KpiCard,
  Skeleton,
  Timeline,
} from "./ui";
import "./styles.css";

const api = new ApiClient();
const screenPaths: Record<Screen, string> = {
  home: "/",
  onboarding: "/getting-started",
  research: "/research",
  wizard: "/research/new",
  reports: "/reports",
  report: "/reports/latest",
  recommendations: "/recommendations",
  graph: "/knowledge-graph",
  competitors: "/competitors",
  history: "/history",
  providers: "/providers",
  analytics: "/product-analytics",
  notifications: "/notifications",
  organization: "/organizations",
  settings: "/settings",
  feedback: "/feedback",
  profile: "/profile",
  admin: "/admin",
};
const pathScreens = Object.fromEntries(
  Object.entries(screenPaths).map(([screen, path]) => [path, screen]),
) as Record<string, Screen>;
const routingProfiles = [
  ["FAST", "Fast", "Минимальная задержка для быстрых проверок", "⚡"],
  ["BALANCED", "Balanced", "Баланс качества, скорости и цены", "◐"],
  ["HIGH_QUALITY", "High Quality", "Максимальное качество итогового анализа", "◆"],
  ["FREE", "Free", "Только бесплатные и локальные модели", "○"],
  ["PRIVATE", "Private", "Данные не покидают вашу инфраструктуру", "◈"],
  ["ENTERPRISE", "Enterprise", "Несколько моделей, failover и строгие политики", "▣"],
] as const;
const metricMeta = [
  ["Упоминания", "mention_score"],
  ["Рекомендации", "recommendation_score"],
  ["Цитирование", "citation_score"],
  ["Покрытие", "coverage_score"],
  ["Достоверность", "confidence_score"],
] as const;

type Screen = "home" | "research" | "wizard" | "reports" | "report" | "recommendations" | "graph" | "competitors" | "history" | "providers" | "analytics" | "notifications" | "organization" | "settings" | "feedback" | "profile" | "admin" | "onboarding";
type ReportShape = {
  executive_summary?: string;
  research?: ResearchItem;
  score?: Record<string, number | string> & { id?: number; research_id?: number; calculated_at?: string; version?: string };
  trend?: { metrics?: TrendMetric[] };
  benchmark?: { entity_count?: number; calculated_at?: string; entries?: BenchmarkEntry[] };
  insights?: Array<{ title?: string; explanation?: string }>;
  recommendations?: Array<{
    id?: number;
    recommendation_type?: string;
    explanation?: string;
    priority?: string;
    metric?: string;
    expected_effect?: string;
    metric_value?: number;
    created_at?: string;
  }>;
  provider_statistics?: Record<string, unknown>;
  detected_entities?: Array<{ id?: number; response_id?: number; name?: string; entity_type?: string; confidence?: number }>;
  sources?: Array<{ id?: number; response_id?: number; url?: string; title?: string; source?: string }>;
  responses?: Array<{
    id: number; provider: string; model: string; content: string;
    processing_status: string; created_at: string; finished_at: string;
    latency_ms?: number; total_tokens: number; cost: number; error_type?: string;
  }>;
  knowledge_graph_summary?: GraphSnapshot;
  latency_ms?: number;
  token_usage?: number;
  cost?: number;
  execution_time_ms?: number;
  explainability?: {
    methodology_version: string;
    metrics: Record<string, { formula?: string; inputs: Record<string, unknown>; normalization?: string; weight?: number; version: string; status?: string }>;
    prompts: Array<{ uuid: string; response_id: number; text: string; language?: string | string[]; country?: string | string[]; provider: string; model: string; created_at: string }>;
    responses: Array<{ response_id: number; provider: string; model: string; prompt: string; raw_response: Record<string, unknown>; normalized_response: Record<string, unknown>; tokens: number; cost: number; latency_ms?: number; finished_at: string; error_type?: string; error_message?: string; entity_ids: number[]; citation_ids: number[]; recommendation_ids: number[] }>;
    citations: Array<{ citation_id: number; response_id: number; url?: string; domain?: string; source?: string; title?: string; position: number }>;
    unsupported_metrics: string[];
  };
};
type TrendPoint = { research_id: number; observed_at: string; value: number; moving_average: number; percentage_change?: number | null; direction: string };
type TrendMetric = { metric: string; direction: string; points: TrendPoint[] };
type BenchmarkMetric = { value: number; population_average: number; leader_value: number };
type BenchmarkEntry = { observation_count: number; metrics: Record<string, BenchmarkMetric> };

function valueOf(score: Record<string, number | string>, key: string) {
  const value = Number(score[key] ?? 0);
  return Number.isFinite(value) ? value : 0;
}
function tone(value: number) {
  return value >= 80 ? "good" : value >= 55 ? "watch" : "critical";
}
function healthLabel(value: number) {
  return value >= 85
    ? "Отлично"
    : value >= 70
      ? "Очень хорошо"
      : value >= 50
        ? "Требует внимания"
        : "Критично";
}

function Login({ onReady }: { onReady: (profile: AuthProfile) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.login(email, password);
      onReady(await api.me());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="logo-mark">AR</div>
        <span className="eyebrow">AI RANKING OS</span>
        <h1>Понимайте, как AI видит ваш бренд</h1>
        <p>
          Измеряйте присутствие, находите точки роста и превращайте данные в
          понятный план действий.
        </p>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              minLength={8}
              required
            />
          </label>
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          <button type="submit" disabled={busy}>
            {busy ? "Входим…" : "Войти"}
          </button>
        </form>
      </section>
      <aside className="login-story">
        <span>AI visibility, made actionable</span>
        <blockquote>
          «Не просто следите за рейтингом. Понимайте, что именно изменить, чтобы
          AI чаще рекомендовал ваш бренд».
        </blockquote>
        <div className="story-metric">
          <strong>89.9</strong>
          <span>пример AI Visibility</span>
        </div>
      </aside>
    </main>
  );
}

function Shell({
  user,
  children,
  onNavigate,
  active,
  onLogout,
  roles,
}: {
  user: string;
  children: React.ReactNode;
  onNavigate: (screen: Screen) => void;
  active: Screen;
  onLogout: () => void;
  roles: string[];
}) {
  const [systemReady, setSystemReady] = useState<boolean>();
  useEffect(() => { api.systemHealth().then((health) => setSystemReady(health.status === "healthy" || health.status === "ready")).catch(() => setSystemReady(false)); }, []);
  const isAdmin = roles.some((role) => ["superadmin", "admin", "organization_admin", "SUPERADMIN", "ADMIN", "ORGANIZATION_ADMIN"].includes(role));
  const navSource = [
    ["⌂", "Dashboard", "home"], ["→", "Getting Started", "onboarding"],
    ["◉", "Research", "research"], ["▤", "Reports", "reports"],
    ["✓", "Recommendations", "recommendations"], ["⌘", "Knowledge Graph", "graph"],
    ["◇", "Competitors", "competitors"], ["↗", "History", "history"],
    ["✦", "AI Providers", "providers"], ["◫", "Product Analytics", "analytics"],
    ["♢", "Notifications", "notifications"], ["◎", "Organizations", "organization"],
    ["◌", "Feedback", "feedback"], ["♙", "User Profile", "profile"],
    ["⚙", "Settings", "settings"], ["▦", "Admin Console", "admin"],
  ] as const;
  const nav = navSource.filter(([, , target]) => isAdmin || (target !== "admin" && target !== "analytics"));
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="wordmark" onClick={() => onNavigate("home")}>
          <span className="logo-mark small">AR</span>
          <span>AI Ranking OS</span>
        </button>
        <nav>
          {nav.map(([icon, label, target]) => (
            <button
              key={label}
              className={active === target ? "active" : ""}
              onClick={() => onNavigate(target)}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="avatar">{user.slice(0, 1).toUpperCase()}</span>
          <div>
            <b>{user}</b>
            <small>Workspace</small>
          </div>
          <button
            className="icon-button"
            aria-label="Выйти"
            onClick={async () => {
              await api.logout();
              onLogout();
            }}
          >
            ↗
          </button>
        </div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div>
            <span className="mobile-brand">AI Ranking OS</span>
          </div>
          <div className="top-actions">
            <Badge tone={systemReady === true ? "success" : systemReady === false ? "danger" : "neutral"}>● {systemReady === true ? "Система работает" : systemReady === false ? "Система недоступна" : "Проверка системы"}</Badge>
            <button className="icon-button" aria-label="Уведомления" onClick={() => onNavigate("notifications")}>
              ♢
            </button>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}

function SettingsScreen({ user }: { user: string }) {
  const [tab, setTab] = useState("profile");
  const [settings, setSettings] = useState<Record<string, unknown>>({ language: "ru", region: "GLOBAL", theme: "dark", notifications: { email: true, in_app: true } });
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [keys, setKeys] = useState<Array<{ id: number; name: string; prefix: string }>>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { Promise.all([api.workspace(), api.listProviders(), api.apiKeys()]).then(([workspace, providerItems, apiKeyItems]) => { setSettings((current) => ({ ...current, ...workspace.settings })); setProviders(providerItems); setKeys(apiKeyItems); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки настроек")); }, []);
  const tabs = [["profile", "Профиль"], ["security", "Безопасность"], ["api", "API Keys"], ["providers", "LLM Providers"], ["preferences", "Язык и регион"], ["notifications", "Уведомления"], ["theme", "Тема"], ["organization", "Организация"]];
  const set = (key: string, value: unknown) => { setSaved(false); setSettings((current) => ({ ...current, [key]: value })); };
  return <main className="analytics-page settings-page"><header className="analytics-hero"><div><span className="eyebrow">PREFERENCES</span><h1>Настройки</h1><p>Единый центр персональных и системных настроек.</p></div><button className="primary-action" onClick={() => api.updateWorkspace(settings).then(() => setSaved(true))}>{saved ? "Сохранено ✓" : "Сохранить"}</button></header>
    {error && <div className="error" role="alert">{error}</div>}
    <div className="settings-layout"><nav className="settings-nav">{tabs.map(([key, label]) => <button className={tab === key ? "active" : ""} onClick={() => setTab(key)} key={key}>{label}</button>)}</nav><section className="analytics-card settings-panel">
      {tab === "profile" && <><h2>Профиль</h2><label>Имя<input value={user} disabled /></label><p className="empty-state">Контактные данные управляются Authentication.</p></>}
      {tab === "security" && <><h2>Безопасность</h2><div className="setting-row"><span>JWT-сессии и refresh rotation</span><b>Активно</b></div><div className="setting-row"><span>Отзыв токенов при выходе</span><b>Активно</b></div></>}
      {tab === "api" && <><h2>API Keys</h2>{keys.length ? keys.map((key) => <div className="setting-row" key={key.id}><span>{key.name}</span><code>{key.prefix}••••</code></div>) : <p className="empty-state">API-ключи ещё не созданы.</p>}</>}
      {tab === "providers" && <><h2>LLM Providers</h2>{providers.length ? providers.map((provider) => <div className="setting-row" key={provider.id}><span>{provider.display_name}</span><b>{provider.availability}</b></div>) : <p className="empty-state">Провайдеры недоступны.</p>}</>}
      {tab === "preferences" && <><h2>Язык и регион</h2><label>Язык<select value={String(settings.language)} onChange={(event) => set("language", event.target.value)}><option value="ru">Русский</option><option value="en">English</option></select></label><label>Регион<select value={String(settings.region)} onChange={(event) => set("region", event.target.value)}><option>GLOBAL</option><option>RU</option><option>EU</option><option>US</option></select></label></>}
      {tab === "notifications" && <><h2>Уведомления</h2><label className="toggle-row"><input type="checkbox" checked={Boolean((settings.notifications as Record<string, boolean>)?.in_app)} onChange={(event) => set("notifications", { ...(settings.notifications as object), in_app: event.target.checked })}/>In-app</label><label className="toggle-row"><input type="checkbox" checked={Boolean((settings.notifications as Record<string, boolean>)?.email)} onChange={(event) => set("notifications", { ...(settings.notifications as object), email: event.target.checked })}/>Email</label></>}
      {tab === "theme" && <><h2>Тема</h2><div className="theme-options">{["dark", "light", "system"].map((theme) => <button className={settings.theme === theme ? "active" : ""} onClick={() => set("theme", theme)} key={theme}>{theme}</button>)}</div></>}
      {tab === "organization" && <><h2>Организация</h2><p>Профиль, участники, роли и лимиты доступны в Organization Workspace.</p></>}
    </section></div></main>;
}

function metricEvidence(key: string, data: ReportShape, research: ResearchItem) {
  const responses = data.responses ?? [];
  const score = data.score ?? {};
  const processed = responses.filter((item) => item.processing_status === "PROCESSED").length;
  const total = responses.length;
  const value = valueOf(score, key);
  const target = String(research.metadata?.brand ?? research.title.replace(/^AI Visibility:\s*/, ""));
  const mentions = responses.filter((item) => item.content.toLocaleLowerCase().includes(target.toLocaleLowerCase())).length;
  const recommended = Math.round(valueOf(score, "recommendation_score") / 100 * total);
  const citations = data.sources?.length ?? 0;
  const uniqueModels = new Set(responses.map((item) => `${item.provider}/${item.model}`)).size;
  const entities = data.detected_entities ?? [];
  const averageConfidence = entities.length ? entities.reduce((sum, item) => sum + Number(item.confidence ?? 0), 0) / entities.length * 100 : 50;
  const details: Record<string, { lines: string[]; formula: string }> = {
    mention_score: { lines: [`${total} ответов моделей`, `${mentions} ответов содержат бренд`], formula: `${mentions} / ${Math.max(total, 1)} × 100 = ${value.toFixed(1)}` },
    recommendation_score: { lines: [`${total} ответов моделей`, `${recommended} ответов содержат извлечённую рекомендацию`], formula: `${recommended} / ${Math.max(total, 1)} × 100 = ${value.toFixed(1)}` },
    citation_score: { lines: [`${total} ответов моделей`, `${citations} независимых источников`, `Максимум v1: ${total * 3} источников`], formula: `${citations} / ${Math.max(total * 3, 1)} × 100 = ${value.toFixed(1)}` },
    coverage_score: { lines: [`${uniqueModels} уникальных пар «провайдер/модель»`, `${research.total_tasks ?? total} запланированных задач`], formula: `${uniqueModels} / ${Math.max(research.total_tasks ?? total, 1)} × 100 = ${value.toFixed(1)}` },
    confidence_score: { lines: [`${processed} из ${total} ответов обработано`, `${entities.length} извлечённых сущностей`, `Средняя достоверность сущностей: ${averageConfidence.toFixed(1)}`], formula: `70% успешности обработки + 30% достоверности сущностей = ${value.toFixed(1)}` },
    visibility_score: { lines: ["Mention × 35%", "Recommendation × 20%", "Citation × 15%", "Coverage × 20%", "Confidence × 10%"], formula: `Взвешенная сумма Scoring ${String(score.version ?? "1.0")} = ${value.toFixed(1)}` },
  };
  return details[key] ?? { lines: [`Research #${research.id}`], formula: value.toFixed(1) };
}

function GraphScreen() {
  const [graph, setGraph] = useState<GraphSnapshot>();
  const [query, setQuery] = useState("");
  const [nodeType, setNodeType] = useState("ALL");
  const [selected, setSelected] = useState<number>();
  const [error, setError] = useState("");
  useEffect(() => { api.graph().then(setGraph).catch((reason) => setError(reason instanceof Error ? reason.message : "Граф недоступен")); }, []);
  if (error) return <main className="analytics-page"><div className="error" role="alert">{error}</div></main>;
  if (!graph) return <DashboardSkeleton />;
  const types = [...new Set(graph.nodes.map((node) => node.node_type))];
  const visible = graph.nodes.filter((node) => (nodeType === "ALL" || node.node_type === nodeType) && (!query || `${node.name} ${node.aliases.join(" ")}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())));
  const visibleIds = new Set(visible.map((node) => node.id));
  const edges = graph.edges.filter((edge) => visibleIds.has(edge.source_node_id) && visibleIds.has(edge.target_node_id));
  const positions = new Map(visible.map((node, index) => { const angle = index * Math.PI * 2 / Math.max(visible.length, 1) - Math.PI / 2; return [node.id, { x: 310 + Math.cos(angle) * 215, y: 230 + Math.sin(angle) * 165 }]; }));
  const selectedNode = graph.nodes.find((node) => node.id === selected);
  const connected = selected == null ? [] : graph.edges.filter((edge) => edge.source_node_id === selected || edge.target_node_id === selected);
  return <main className="analytics-page graph-page"><header className="analytics-hero"><div><span className="eyebrow">SNAPSHOT #{graph.id} · v{graph.structure_version}</span><h1>Knowledge Graph</h1><p>{graph.node_count} сущностей · {graph.edge_count} связей · {new Date(graph.created_at).toLocaleString("ru-RU")}</p></div></header>
    <section className="analytics-card graph-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск по имени или алиасу"/><select value={nodeType} onChange={(event) => setNodeType(event.target.value)}><option value="ALL">Все типы</option>{types.map((type) => <option key={type}>{type}</option>)}</select></section>
    {!visible.length ? <div className="analytics-card empty-state">Сущности по выбранным условиям не найдены.</div> : <section className="graph-real-layout"><article className="analytics-card"><svg viewBox="0 0 620 460" className="network" aria-label="Реальный граф знаний"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#607899"/></marker></defs>{edges.map((edge) => { const source = positions.get(edge.source_node_id); const target = positions.get(edge.target_node_id); if (!source || !target) return null; return <g key={edge.id}><line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#607899" markerEnd="url(#arrow)"/><title>{edge.edge_type} · confidence {(edge.confidence * 100).toFixed(0)}%</title></g>; })}{visible.map((node) => { const point = positions.get(node.id)!; return <g key={node.id} className="graph-node" onClick={() => setSelected(node.id)}><circle cx={point.x} cy={point.y} r={selected === node.id ? 25 : 19} fill={selected === node.id ? "#3b82f6" : "#263d62"}/><text x={point.x} y={point.y + 34} textAnchor="middle" fill="#c8d4e6" fontSize="11">{node.name}</text><title>{node.node_type} · confidence {(node.confidence * 100).toFixed(0)}%</title></g>; })}</svg>{!edges.length && <p className="empty-state">Связи пока не обнаружены. Показаны только реальные узлы snapshot.</p>}</article><aside className="analytics-card graph-detail">{selectedNode ? <><span className="eyebrow">{selectedNode.node_type}</span><h2>{selectedNode.name}</h2><p>Confidence {(selectedNode.confidence * 100).toFixed(1)}%</p><p>Aliases: {selectedNode.aliases.join(", ") || "нет"}</p><h3>Связи ({connected.length})</h3>{connected.map((edge) => <div className="setting-row" key={edge.id}><span>{edge.edge_type}</span><b>{(edge.confidence * 100).toFixed(0)}%</b></div>)}</> : <p className="empty-state">Выберите узел, чтобы увидеть confidence, алиасы и связи.</p>}</aside></section>}
  </main>;
}

type RecordsKind = "research" | "reports" | "recommendations" | "graph" | "competitors" | "history" | "feedback" | "profile";
type DisplayRecord = { id: string; title: string; status: string; detail: string; meta?: string };

function RecordsScreen({ kind, onNewResearch }: { kind: RecordsKind; onNewResearch: () => void }) {
  const [records, setRecords] = useState<DisplayRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const titles: Record<RecordsKind, [string, string]> = {
    research: ["Исследования", "Запуски, прогресс и состояние выполнения"],
    reports: ["Отчёты", "Сформированные результаты исследований"],
    recommendations: ["Рекомендации", "Приоритетные действия из последнего исследования"],
    graph: ["Knowledge Graph", "Реальные сущности и связи последнего snapshot"],
    competitors: ["Конкуренты", "Конкуренты из проектов рабочего пространства"],
    history: ["История", "Хронология исследований от новых к старым"],
    feedback: ["Feedback", "Ваши обращения и их текущий статус"],
    profile: ["Профиль", "Данные текущей авторизованной учётной записи"],
  };
  useEffect(() => {
    const load = async () => {
      if (kind === "research" || kind === "history") {
        const items: ResearchItem[] = await api.listResearch();
        return [...items].sort((a, b) => b.id - a.id).map((item) => ({ id: String(item.id), title: item.title, status: item.status, detail: `${item.progress_percent ?? 0}% · ${item.completed_tasks ?? 0}/${item.total_tasks ?? 0} задач`, meta: item.created_at ? new Date(item.created_at).toLocaleString("ru-RU") : undefined }));
      }
      if (kind === "reports") return (await api.reports()).items.map((item: ReportCatalogItem) => ({ id: String(item.research_id), title: item.title, status: item.status, detail: `AI Visibility: ${item.visibility_score?.toFixed(1) ?? "—"}`, meta: new Date(item.created_at).toLocaleString("ru-RU") }));
      if (kind === "recommendations") {
        const latest = [...await api.listResearch()].sort((a, b) => b.id - a.id)[0];
        if (!latest) return [];
        return (await api.recommendations(latest.id)).recommendations.map((item: RecommendationItem) => ({ id: String(item.id), title: item.explanation, status: item.priority, detail: `${item.metric}: ${item.metric_value.toFixed(1)}`, meta: item.expected_effect }));
      }
      if (kind === "graph") {
        const graph: GraphSnapshot = await api.graph();
        return graph.nodes.map((node) => ({ id: String(node.id), title: node.name, status: node.node_type, detail: `Confidence ${(node.confidence * 100).toFixed(0)}%`, meta: `Snapshot #${graph.id} · ${graph.node_count} узлов · ${graph.edge_count} связей` }));
      }
      if (kind === "competitors") {
        const projects: WorkspaceProjectItem[] = await api.workspaceProjects();
        const groups = await Promise.all(projects.map(async (project) => ({ project, items: await api.projectCompetitors(project.id) })));
        return groups.flatMap(({ project, items }) => items.map((item: CompetitorItem) => ({ id: `${project.id}-${item.id}`, title: item.name, status: item.active ? "ACTIVE" : "INACTIVE", detail: item.domains.join(", ") || "Домен не указан", meta: project.name })));
      }
      if (kind === "feedback") return (await api.feedback()).map((item: FeedbackItem) => ({ id: String(item.id), title: item.title, status: item.status, detail: `${item.feedback_type} · ${item.priority}`, meta: new Date(item.created_at).toLocaleString("ru-RU") }));
      const profile = await api.me();
      return [{ id: profile.email, title: profile.display_name, status: "ACTIVE", detail: profile.email }];
    };
    load().then(setRecords).catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки")).finally(() => setLoading(false));
  }, [kind]);
  return <main className="analytics-page records-page"><header className="analytics-hero"><div><span className="eyebrow">REAL DATA</span><h1>{titles[kind][0]}</h1><p>{titles[kind][1]}</p></div>{kind === "research" && <button className="primary-action" onClick={onNewResearch}>Новое исследование</button>}</header>
    {error ? <div className="error" role="alert">{error}</div> : loading ? <DashboardSkeleton /> : <section className="records-list">{records.length ? records.map((item) => <article className="analytics-card record-card" key={item.id}><div><small>{item.meta}</small><h2>{item.title}</h2><p>{item.detail}</p></div><Badge tone={item.status === "COMPLETED" || item.status === "ACTIVE" ? "success" : item.status === "FAILED" || item.status === "CRITICAL" ? "danger" : "warning"}>{item.status}</Badge></article>) : <div className="analytics-card empty-state">Данных пока нет. Они появятся после первого действия в этом разделе.</div>}</section>}
  </main>;
}

function OnboardingScreen({ onResearch, onOrganization }: { onResearch: () => void; onOrganization: () => void }) {
  const [organizations, setOrganizations] = useState<OrganizationItem[]>([]);
  useEffect(() => { api.organizations().then(setOrganizations).catch(() => undefined); }, []);
  const ready = organizations.length > 0;
  return <main className="analytics-page onboarding-page"><header className="analytics-hero"><div><span className="eyebrow">CLOSED BETA</span><h1>Начните с первого результата</h1><p>Три коротких шага — и AI Ranking OS покажет, как модели видят ваш бренд.</p></div><Badge tone={ready ? "success" : "warning"}>● {ready ? "Workspace готов" : "Нужна организация"}</Badge></header>
    <section className="onboarding-steps"><article className="analytics-card onboarding-step"><span>01</span><h2>Настройте пространство</h2><p>Организация объединяет команду, проекты и лимиты.</p><button onClick={onOrganization}>{ready ? "Открыть организацию" : "Создать организацию"}</button></article><article className="analytics-card onboarding-step"><span>02</span><h2>Проверьте свой бренд</h2><p>Укажите бренд, регион, язык и профиль маршрутизации.</p><button onClick={onResearch} disabled={!ready}>Открыть исследование</button></article><article className="analytics-card onboarding-step"><span>03</span><h2>Получите отчёт</h2><p>Visibility, источники и план действий собираются автоматически.</p><div className="onboarding-result">Report → Share → Improve</div></article></section>
    <section className="analytics-card beta-expectations"><h3>Что проверить в закрытой бете</h3><div><span>Исследование проходит без ручного вмешательства</span><b>Pipeline</b></div><div><span>Рекомендации понятны и применимы</span><b>Value</b></div><div><span>Отчёт можно передать клиенту</span><b>Sharing</b></div></section>
  </main>;
}

type AdminData = {
  users: AdminUser[];
  organizations: OrganizationItem[];
  research: Array<{ id: number; title: string; status: string }>;
  reports: Array<{ research_id: number; title: string; status: string; visibility_score?: number }>;
  providers: ProviderItem[];
  jobs: Array<{ id: number; state: string; attempts: number }>;
  feedback: AdminFeedback[];
  audit: AdminAudit[];
  health: Record<string, unknown>;
};

function AdminConsoleScreen() {
  const [section, setSection] = useState("Users");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [data, setData] = useState<AdminData>();
  const load = useCallback(() => Promise.all([
    api.adminUsers(search), api.organizations(), api.listResearch(), api.adminReports(),
    api.listProviders(), api.adminJobs(), api.adminFeedback(), api.adminAudit(), api.systemHealth(),
  ]).then(([users, organizations, research, reportPage, providers, jobs, feedback, auditPage, health]) =>
    setData({ users, organizations, research, reports: reportPage.items, providers, jobs, feedback, audit: auditPage.items, health })
  ).catch((reason) => setError(reason instanceof Error ? reason.message : "Admin Console недоступен")), [search]);
  useEffect(() => { load(); }, [load]);
  const sections = ["Users", "Organizations", "Research", "Reports", "Providers", "Jobs", "Feedback", "Product Analytics", "Audit", "Health", "Settings"];
  const rows = section === "Users" ? data?.users.map((item) => [item.display_name, item.email, item.status, `${item.research_count} исследований`])
    : section === "Organizations" ? data?.organizations.map((item) => [item.name, item.role, item.country ?? "GLOBAL", item.timezone])
      : section === "Research" ? data?.research.map((item) => [item.title, item.status, `#${item.id}`])
        : section === "Reports" ? data?.reports.map((item) => [item.title, item.status, item.visibility_score?.toFixed(1) ?? "—"])
          : section === "Providers" ? data?.providers.map((item) => [item.display_name, item.availability, item.free_tier ? "FREE" : "PAID"])
            : section === "Jobs" ? data?.jobs.map((item) => [`Execution #${item.id}`, item.state, `${item.attempts} попыток`])
              : section === "Feedback" ? data?.feedback.map((item) => [item.title, item.feedback_type, item.priority, item.status])
                : section === "Audit" ? data?.audit.map((item) => [item.action, item.category, item.resource, item.actor_id]) : undefined;
  return <main className="analytics-page admin-page"><header className="analytics-hero"><div><span className="eyebrow">CONTROL PLANE</span><h1>Admin Console</h1><p>Пользователи, инфраструктура и продукт — в едином операционном контуре.</p></div><Badge tone={error ? "warning" : "success"}>● {error ? "Требует внимания" : "Система работает"}</Badge></header>
    <div className="admin-layout"><nav className="admin-nav">{sections.map((item) => <button key={item} className={section === item ? "active" : ""} onClick={() => setSection(item)}>{item}</button>)}</nav><section className="analytics-card admin-content"><div className="admin-toolbar"><div><span className="eyebrow">{section.toUpperCase()}</span><h2>{section}</h2></div>{section === "Users" && <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск пользователя" />}</div>
      {error ? <div className="error">{error}</div> : !data ? <Skeleton /> : section === "Product Analytics" ? <div className="admin-summary"><strong>{numeric(data.users as unknown as Record<string, unknown>, "length")}</strong><p>Подробная продуктовая аналитика доступна в основном разделе Product Analytics.</p></div> : section === "Health" ? <pre className="health-json">{JSON.stringify(data.health, null, 2)}</pre> : section === "Settings" ? <p className="empty-state">Системные и пользовательские параметры доступны через Settings Center.</p> : <div className="admin-table">{rows?.length ? rows.map((row, index) => <div className="admin-row" key={`${section}-${index}`}>{row.map((value, cell) => <span key={cell}>{value}</span>)}</div>) : <p className="empty-state">Нет данных для отображения.</p>}</div>}
    </section></div></main>;
}

function OrganizationScreen() {
  const [organizations, setOrganizations] = useState<OrganizationItem[]>([]);
  const [selected, setSelected] = useState<number>();
  const [members, setMembers] = useState<Array<{ id: number; user_id: number; role: string }>>([]);
  const [activity, setActivity] = useState<Array<{ id: number; action: string; actor_id: number; created_at: string }>>([]);
  const [email, setEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(() => api.organizations().then((items) => { setOrganizations(items); setSelected((current) => current ?? items.find((item) => item.is_default)?.id ?? items[0]?.id); }), []);
  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки организаций")); }, [load]);
  useEffect(() => { if (!selected) return; Promise.all([api.organizationMembers(selected), api.organizationActivity(selected)]).then(([memberItems, actions]) => { setMembers(memberItems); setActivity(actions); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки организации")); }, [selected]);
  const current = organizations.find((item) => item.id === selected);
  return <main className="analytics-page organization-page"><header className="analytics-hero"><div><span className="eyebrow">TEAM WORKSPACE</span><h1>{current?.name ?? "Организация"}</h1><p>Участники, проекты, лимиты и журнал активности команды.</p></div><select value={selected ?? ""} onChange={(event) => { const id = Number(event.target.value); api.switchOrganization(id).then(() => { setSelected(id); load(); }); }}>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}</select></header>
    {error && <div className="error" role="alert">{error}</div>}
    {!organizations.length && <section className="analytics-card empty-state"><h2>Организаций пока нет</h2><p>Создайте рабочее пространство для проектов и исследований.</p><form className="invite-form" onSubmit={(event) => { event.preventDefault(); const slug = newName.trim().toLowerCase().replace(/[^a-z0-9а-яё]+/gi, "-").replace(/^-|-$/g, ""); api.createOrganization({ name: newName.trim(), slug }).then(() => { setNewName(""); load(); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка создания")); }}><input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Название организации" required/><button>Создать организацию</button></form></section>}
    {current && <>
    <section className="analytics-kpis"><article className="analytics-card metric"><span>Участники</span><strong>{members.length}</strong><small>из {current?.limits.members ?? "—"}</small></article><article className="analytics-card metric"><span>Проекты</span><strong>{current?.limits.projects ?? "—"}</strong><small>доступный лимит</small></article><article className="analytics-card metric"><span>Часовой пояс</span><strong className="small-value">{current?.timezone ?? "UTC"}</strong><small>{current?.country ?? "GLOBAL"}</small></article></section>
    <section className="analytics-grid"><article className="analytics-card"><h3>Команда</h3>{members.map((member) => <div className="rank-row" key={member.id}><span>User {member.user_id}</span><b>{member.role}</b></div>)}<form className="invite-form" onSubmit={(event) => { event.preventDefault(); if (selected) api.inviteOrganizationMember(selected, email).then(() => setEmail("")); }}><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="email нового участника" required/><button>Пригласить</button></form></article><article className="analytics-card"><h3>Журнал активности</h3>{activity.slice(0, 8).map((item) => <div className="activity-row" key={item.id}><span>{item.action.replaceAll("_", " ")}</span><small>{new Date(item.created_at).toLocaleString("ru-RU")}</small></div>)}</article></section>
    </>}
  </main>;
}

function NotificationsScreen() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [category, setCategory] = useState("");
  const [summary, setSummary] = useState({ unread: 0, total: 0, archived: 0 });
  const [error, setError] = useState("");
  const load = useCallback(
    () => Promise.all([api.notifications(category), api.notificationSummary()])
      .then(([notifications, counts]) => { setItems(notifications); setSummary(counts); }),
    [category],
  );
  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки уведомлений")); }, [load]);
  return <main className="analytics-page notifications-page">
    <header className="analytics-hero"><div><span className="eyebrow">INBOX</span><h1>Уведомления</h1><p>Важные изменения проектов, исследований и вашей организации.</p></div>
      <div className="notification-summary"><b>{summary.unread}</b><span>непрочитанных</span></div></header>
    {error && <div className="error" role="alert">{error}</div>}
    <div className="notification-filters" role="group" aria-label="Категории уведомлений">
      {["", "RESEARCH", "REPORT", "ORGANIZATION", "FEEDBACK", "SYSTEM"].map((value) => <button key={value || "ALL"} className={category === value ? "active" : ""} onClick={() => setCategory(value)}>{value || "Все"}</button>)}
    </div>
    <section className="notification-list">{items.length ? items.map((item) => <article className={`notification-item ${item.is_read ? "" : "unread"}`} key={item.id}>
      <span className={`notification-priority ${item.priority.toLowerCase()}`} />
      <div><small>{item.category} · {new Date(item.created_at).toLocaleString("ru-RU")}</small><h3>{item.title}</h3><p>{item.message}</p></div>
      <div className="notification-actions">{!item.is_read && <button onClick={() => api.markNotificationRead(item.id).then(load)}>Прочитано</button>}<button onClick={() => api.archiveNotification(item.id).then(load)}>В архив</button></div>
    </article>) : <div className="analytics-card empty-state">Здесь пока нет уведомлений.</div>}</section>
  </main>;
}

function numeric(section: Record<string, unknown>, key: string) {
  const value = Number(section[key] ?? 0);
  return Number.isFinite(value) ? value : 0;
}

function ProductAnalyticsScreen() {
  const [period, setPeriod] = useState("DAILY");
  const [provider, setProvider] = useState("");
  const [data, setData] = useState<AnalyticsDashboard>();
  const [error, setError] = useState("");
  useEffect(() => {
    api.productAnalytics(period, provider)
      .then(setData)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки"));
  }, [period, provider]);
  if (error) return <main className="analytics-page"><div className="error">{error}</div></main>;
  if (!data) return <main className="analytics-page"><DashboardSkeleton /></main>;
  const trendPoints = data.trends.map((point, index) => ({
    label: String(point.bucket ?? index),
    value: Number(point.events ?? 0),
  }));
  const usage = (data.providers.usage as Array<{ key: string; count: number }> | undefined) ?? [];
  const topUsers = (data.users.top_users as Array<{ key: string; count: number }> | undefined) ?? [];
  return (
    <main className="analytics-page">
      <header className="analytics-hero">
        <div><span className="eyebrow">PRODUCT INTELLIGENCE</span><h1>Product Analytics</h1>
          <p>Как команды используют AI Ranking OS — от активности до стоимости моделей.</p></div>
        <div className="analytics-filters">
          <label>Период<select value={period} onChange={(event) => { setError(""); setPeriod(event.target.value); }}>
            <option value="HOURLY">По часам</option><option value="DAILY">По дням</option>
            <option value="WEEKLY">По неделям</option><option value="MONTHLY">По месяцам</option>
          </select></label>
          <label>Провайдер<input value={provider} onChange={(event) => { setError(""); setProvider(event.target.value); }} placeholder="Все провайдеры" /></label>
        </div>
      </header>
      <section className="analytics-kpis" aria-label="Основные показатели">
        <article className="analytics-card metric"><span>Активны сегодня</span><strong>{numeric(data.users, "dau")}</strong><small>WAU {numeric(data.users, "wau")}</small></article>
        <article className="analytics-card metric"><span>Исследования</span><strong>{numeric(data.research, "count")}</strong><small>{numeric(data.research, "success_rate")}% успешно</small></article>
        <article className="analytics-card metric"><span>Отчёты</span><strong>{numeric(data.reports, "count")}</strong><small>{numeric(data.reports, "average_generation_ms")} ms</small></article>
        <article className="analytics-card metric"><span>Стоимость</span><strong>${numeric(data.overview, "cost").toFixed(2)}</strong><small>{numeric(data.providers, "average_tokens")} токенов</small></article>
      </section>
      <section className="analytics-grid">
        <ChartContainer title="Динамика использования" caption="Все события продукта">
          {trendPoints.length ? <AreaLineChart points={trendPoints.map((point) => ({ value: point.value, label: point.label }))} /> : <p className="empty-state">События появятся после первого действия.</p>}
        </ChartContainer>
        <article className="analytics-card"><span className="eyebrow">RESEARCH HEALTH</span><h2>{numeric(data.research, "success_rate")}%</h2>
          <p>успешных исследований</p><div className="success-track"><span style={{ width: `${numeric(data.research, "success_rate")}%` }} /></div>
          <dl><div><dt>Среднее время</dt><dd>{numeric(data.research, "average_duration_ms")} ms</dd></div><div><dt>Ошибки</dt><dd>{numeric(data.errors, "count")}</dd></div></dl></article>
      </section>
      <section className="analytics-three">
        <article className="analytics-card"><h3>Провайдеры</h3>{usage.length ? usage.map((item) => <div className="rank-row" key={item.key}><span>{item.key}</span><b>{item.count}</b></div>) : <p className="empty-state">Нет данных</p>}</article>
        <article className="analytics-card"><h3>Пользователи</h3><div className="metric-pair"><span>DAU / WAU / MAU</span><b>{numeric(data.users, "dau")} / {numeric(data.users, "wau")} / {numeric(data.users, "mau")}</b></div><div className="metric-pair"><span>Retention</span><b>{numeric(data.users, "retention_percent")}%</b></div>{topUsers.slice(0, 3).map((item) => <div className="rank-row" key={item.key}><span>User {item.key}</span><b>{item.count}</b></div>)}</article>
        <article className="analytics-card"><h3>Обратная связь и ошибки</h3><div className="signal-number">{numeric(data.feedback, "count")}<small> отзывов</small></div><div className={`analytics-signal ${numeric(data.errors, "count") ? "danger" : "safe"}`}>{numeric(data.errors, "count") ? `${numeric(data.errors, "count")} ошибок требуют внимания` : "Критических ошибок нет"}</div></article>
      </section>
    </main>
  );
}

function ProvidersDashboard() {
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [runtime, setRuntime] = useState<SystemProviderItem[]>([]);
  const [history, setHistory] = useState<RouterHistoryItem[]>([]);
  const [providerStats, setProviderStats] = useState<Record<string, Record<string, number>>>({});
  const [costs, setCosts] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.listProviders(), api.routerStatus(), api.systemProviders(), api.routerHistory(), api.listResearch()])
      .then(async ([items, status, system, routerHistory, research]) => {
        setProviders(items); setCosts(status.costs); setRuntime(system.providers); setHistory(routerHistory.items);
        const latest = [...research].sort((a, b) => b.id - a.id)[0];
        if (latest) {
          const report = await api.finalReport(latest.id) as ReportShape;
          setProviderStats((report.provider_statistics ?? {}) as Record<string, Record<string, number>>);
        }
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки"));
  }, []);
  const available = providers.filter((item) => item.availability === "READY").length;
  return (
    <main className="page providers-page">
      <div className="page-heading">
        <div><span className="eyebrow">INTELLIGENT ROUTING</span><h1>AI Providers</h1>
          <p>Модели, политики, маршрутизация, стоимость и состояние инфраструктуры.</p></div>
        <Badge tone="success">● {available}/{providers.length || "—"} доступны</Badge>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      {!providers.length && !error ? <div className="provider-cards">{[1,2,3].map(i => <Skeleton key={i} />)}</div> : (
        <>
          <section className="provider-summary">
            <div className="panel"><span>Провайдеры</span><strong>{providers.length}</strong><small>единый registry</small></div>
            <div className="panel"><span>Free / Local</span><strong>{providers.filter(p => p.free_tier).length}</strong><small>без платного API</small></div>
            <div className="panel"><span>Расход сегодня</span><strong>${Number(costs.daily_usd || 0).toFixed(2)}</strong><small>контроль бюджета</small></div>
            <div className="panel"><span>Streaming</span><strong>{providers.filter(p => p.streaming).length}</strong><small>моделей и шлюзов</small></div>
          </section>
          <div className="provider-tabs" role="tablist">
            {['Models','Policies','Router','Benchmarks','Costs','Failover','Health'].map((tab, i) => <button className={i===0?'active':''} key={tab}>{tab}</button>)}
          </div>
          <section className="provider-cards">
            {providers.map((provider) => { const health = runtime.find((item) => item.provider === provider.id); const last = history.find((item) => item.selected_models.some((model) => health?.model_id === model)); const stats = providerStats[provider.id] ?? {}; return <article className="panel provider-card" key={provider.id}>
              <header><span className="provider-logo">{provider.display_name.slice(0,2).toUpperCase()}</span>
                <div><h2>{provider.display_name}</h2><small>{provider.id}</small></div>
                <Badge tone={provider.availability === 'READY' ? 'success' : 'warning'}>{provider.availability}</Badge></header>
              <div className="provider-stats"><div><span>Configured</span><b>{provider.availability === "NOT_CONFIGURED" ? "NO" : "YES"}</b></div><div><span>Connected</span><b>{health?.interface.available ? "YES" : "NO"}</b></div><div><span>Mock</span><b>{health?.interface.mock ? "YES" : "NO"}</b></div><div><span>Last Request</span><b>{last ? new Date(last.created_at).toLocaleString("ru-RU") : "—"}</b></div><div><span>Last Success</span><b>{last && !last.error ? new Date(last.created_at).toLocaleString("ru-RU") : "—"}</b></div><div><span>Last Error</span><b>{last?.error || "—"}</b></div><div><span>Tokens</span><b>{Number(stats.total_tokens ?? stats.tokens ?? 0) || "—"}</b></div><div><span>Cost</span><b>{last ? `$${last.estimated_cost_usd.toFixed(4)}` : "—"}</b></div><div><span>Latency</span><b>{Number(stats.latency_ms ?? last?.latency_ms ?? 0) ? `${Number(stats.latency_ms ?? last?.latency_ms).toFixed(0)} ms` : "—"}</b></div></div>
              <div className="capability-tags">{provider.capabilities.slice(0,6).map(cap => <span key={cap}>{cap}</span>)}</div>
            </article>})}
          </section>
        </>
      )}
    </main>
  );
}

function Dashboard({
  report,
  onStart,
  onOpen,
  onNavigate,
}: {
  report?: ReportResult;
  onStart: () => void;
  onOpen: (researchId?: number) => void;
  onNavigate: (screen: Screen) => void;
}) {
  const [detail, setDetail] = useState<string>();
  if (!report)
    return (
      <main className="page">
        <section className="welcome">
          <span className="eyebrow">ДОБРО ПОЖАЛОВАТЬ</span>
          <h1>Что хотите узнать сегодня?</h1>
          <p>
            Начните с первого исследования — результат появится здесь в виде
            понятной картины состояния бренда.
          </p>
          <div className="choice-grid">
            <button className="choice primary-choice" onClick={onStart}>
              <span className="choice-icon">◎</span>
              <b>Проверить бренд</b>
              <small>Узнать видимость в ответах AI</small>
              <i>Начать →</i>
            </button>
            <button className="choice" onClick={() => onNavigate("competitors")}>
              <span className="choice-icon">◇</span>
              <b>Исследовать конкурента</b>
              <small>Сравнить позиции и рекомендации</small>
              <i>Открыть →</i>
            </button>
            <button className="choice" onClick={() => onNavigate("history")}>
              <span className="choice-icon">↗</span>
              <b>Посмотреть историю</b>
              <small>Следить за динамикой показателей</small>
              <i>Открыть →</i>
            </button>
            <button className="choice" onClick={() => onNavigate("recommendations")}>
              <span className="choice-icon">✓</span>
              <b>Открыть рекомендации</b>
              <small>Перейти к плану улучшений</small>
              <i>Открыть →</i>
            </button>
          </div>
        </section>
      </main>
    );
  const data = report.report as ReportShape;
  const research = (data.research ?? report.research) as ResearchItem;
  const score = data.score ?? {};
  const visibility = valueOf(score, "visibility_score");
  const trends = data.trend?.metrics ?? [];
  const trendFor = (metric: string) => trends.find((item) => item.metric === metric);
  const visibilityTrend = trendFor("visibility");
  const visibilityPoints = visibilityTrend?.points.slice(-6) ?? [];
  const visibilityDelta = visibilityPoints.at(-1)?.percentage_change;
  const weakest = metricMeta
    .map(([label, key]) => ({ label, value: valueOf(score, key) }))
    .sort((a, b) => a.value - b.value)[0];
  const kpis = [
    ["✦", "Рекомендации", "recommendation_score", "recommendation"],
    ["◉", "Упоминания", "mention_score", "mention"],
    ["◎", "Покрытие", "coverage_score", "coverage"],
    ["↗", "Цитирование", "citation_score", "citation"],
    ["◆", "Достоверность", "confidence_score", "confidence"],
  ] as const;
  const selectedKey = kpis.find(([, label]) => label === detail)?.[2] ?? "visibility_score";
  const evidence = metricEvidence(selectedKey, data, research);
  const latestResponse = [...(data.responses ?? [])].sort((a, b) => String(b.finished_at).localeCompare(String(a.finished_at)))[0];
  const calculatedAt = typeof score.calculated_at === "string" ? score.calculated_at : undefined;
  const activeValue = detail
    ? valueOf(
        score,
        kpis.find(([, label]) => label === detail)?.[2] ?? "visibility_score",
      )
    : 0;
  return (
    <main className="page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">СОСТОЯНИЕ БРЕНДА</span>
          <h1>{research.title.replace(/^AI Visibility:\s*/, "")}</h1>
          <p>Исследование #{research.id} · {research.created_at ? new Date(research.created_at).toLocaleString("ru-RU") : "дата не записана"}</p>
        </div>
        <Button onClick={onStart}>Новое исследование</Button>
      </div>
      <section className="dashboard-grid">
        <article className="hero-score panel">
          <div className="score-label">AI Visibility</div>
          <div className="score-line">
            <strong>{visibility.toFixed(2)}</strong>
            <span className={`status ${tone(visibility)}`}>
              ● {healthLabel(visibility)}
            </span>
          </div>
          {visibilityDelta == null ? <div className="delta"><span>Недостаточно данных для сравнения</span></div> : <div className={`delta ${visibilityDelta >= 0 ? "good" : "critical"}`}>
            {visibilityDelta >= 0 ? "↑" : "↓"} {Math.abs(visibilityDelta).toFixed(1)}% <span>к предыдущему исследованию</span>
          </div>}
          <button className="text-action" onClick={() => onOpen(research.id)}>
            Почему мой рейтинг такой? →
          </button>
        </article>
        <article className="health panel">
          <div className="section-label">AI Health</div>
          <div
            className="health-ring"
            style={
              { "--score": `${visibility * 3.6}deg` } as React.CSSProperties
            }
          >
            <span>{Math.round(visibility)}%</span>
          </div>
          <div>
            <h2>{healthLabel(visibility)}</h2>
            <p>Состояние рассчитано из фактических ответов моделей. Минимальная базовая метрика — {weakest.label}.</p>
            <div className="problem">
              <span>Главная проблема</span>
              <b>{weakest.label}</b>
              <em>{weakest.value.toFixed(1)}</em>
            </div>
          </div>
        </article>
      </section>
      <section className="kpi-grid">
        {kpis.map(([icon, title, key, trendKey]) => {
          const metricTrend = trendFor(trendKey);
          const metricPoints = metricTrend?.points.slice(-5) ?? [];
          return (
          <KpiCard
            key={title}
            icon={icon}
            title={title}
            value={valueOf(score, key)}
            delta={metricPoints.at(-1)?.percentage_change}
            points={metricPoints.length ? metricPoints.map((point) => point.value) : [valueOf(score, key)]}
            onClick={() => setDetail(title)}
          />
        )})}
      </section>
      <section className="analytics-grid">
        <ChartContainer
          title="Динамика AI Visibility"
          caption="TREND"
          action={visibilityDelta == null ? <Badge tone="neutral">Нет сравнения</Badge> : <Badge tone={visibilityDelta >= 0 ? "success" : "danger"}>{visibilityDelta >= 0 ? "↑" : "↓"} {Math.abs(visibilityDelta).toFixed(1)}%</Badge>}
        >
          {visibilityPoints.length > 1 ? <AreaLineChart points={visibilityPoints.map((point) => ({ value: point.value, label: new Date(point.observed_at).toLocaleDateString("ru-RU"), researchId: point.research_id }))} onSelect={(id) => onOpen(id)} /> : <p className="empty-state">Недостаточно данных: для тренда нужны минимум два исследования.</p>}
        </ChartContainer>
        <ChartContainer title="Баланс AI-сигналов" caption="RADAR">
          <RadarChart
            labels={[
              "Упоминания",
              "Цитирование",
              "Покрытие",
              "Рекомендации",
              "Достоверность",
            ]}
            values={[
              valueOf(score, "mention_score"),
              valueOf(score, "citation_score"),
              valueOf(score, "coverage_score"),
              valueOf(score, "recommendation_score"),
              valueOf(score, "confidence_score"),
            ]}
          />
        </ChartContainer>
        <ChartContainer title="Pipeline исследования" caption="TIMELINE">
          <PipelineStatus result={report} data={data} />
        </ChartContainer>
        <Benchmark brand={research.title.replace(/^AI Visibility:\s*/, "")} entry={data.benchmark?.entries?.[0]} entityCount={data.benchmark?.entity_count} />
        <Trend metric={visibilityTrend} />
      </section>
      <ActionCenter recommendations={data.recommendations ?? []} />
      <Drawer
        open={Boolean(detail)}
        title={detail ?? "Метрика"}
        onClose={() => setDetail(undefined)}
      >
        <div className="drawer-score">
          <strong>{activeValue.toFixed(1)}</strong>
          <Badge
            tone={
              activeValue >= 80
                ? "success"
                : activeValue >= 50
                  ? "warning"
                  : "danger"
            }
          >
            {healthLabel(activeValue)}
          </Badge>
        </div>
        <h3>Почему такая оценка</h3>
        {evidence.lines.map((line) => <p key={line}>{line}</p>)}
        <h3>Что влияет</h3>
        <div className="drawer-callout"><span>Расчёт</span><strong>{evidence.formula}</strong></div>
        {latestResponse && <p>Последний ответ: {latestResponse.provider}/{latestResponse.model} · {latestResponse.total_tokens} токенов · {latestResponse.latency_ms ?? "—"} ms.</p>}
        {calculatedAt && <p>Оценка рассчитана {new Date(calculatedAt).toLocaleString("ru-RU")} · алгоритм {String(score.version ?? "—")}.</p>}
        <Button onClick={() => onOpen(research.id)}>Открыть полный отчёт</Button>
      </Drawer>
    </main>
  );
}

function DashboardSkeleton() {
  return (
    <main className="page" aria-label="Загрузка состояния бренда">
      <div className="skeleton-heading">
        <Skeleton />
        <Skeleton />
      </div>
      <div className="skeleton-grid">
        <Skeleton />
        <Skeleton />
      </div>
      <div className="skeleton-kpis">
        {[1, 2, 3, 4, 5].map((item) => (
          <Skeleton key={item} />
        ))}
      </div>
    </main>
  );
}

function Benchmark({ brand, entry, entityCount = 0 }: { brand: string; entry?: BenchmarkEntry; entityCount?: number }) {
  const metric = entry?.metrics.visibility;
  return (
    <article className="benchmark panel">
      <div className="section-head">
        <div>
          <span className="section-label">Benchmark</span>
          <h2>Позиция относительно рынка</h2>
        </div>
        <span className="badge neutral">{metric && entityCount >= 2 ? `${entityCount} объектов` : "Нет данных"}</span>
      </div>
      {metric && entityCount >= 2 ? [
        [brand, metric.value],
        ["Среднее выборки", metric.population_average],
        ["Лидер выборки", metric.leader_value],
      ].map(([name, value]) => (
        <div className="benchmark-row" key={String(name)}>
          <span>{name}</span>
          <div className="track">
            <i style={{ width: `${value}%` }} />
          </div>
          <strong>{Number(value).toFixed(0)}</strong>
        </div>
      )) : <p className="empty-state">Benchmark появится, когда будет достаточно объектов для сравнения.</p>}
    </article>
  );
}

function Trend({ metric }: { metric?: TrendMetric }) {
  const source = metric?.points.slice(-3) ?? [];
  const points = source.map((point) => point.value);
  if (points.length < 2) return <article className="trend panel"><div className="section-head"><div><span className="section-label">Динамика</span><h2>AI Visibility</h2></div></div><p className="empty-state">Тренд появится после повторного исследования.</p></article>;
  const coords = points
    .map((value, i) => `${18 + i * 132},${150 - value}`)
    .join(" ");
  return (
    <article className="trend panel">
      <div className="section-head">
        <div>
          <span className="section-label">Динамика</span>
          <h2>AI Visibility · {metric?.direction ?? "STABLE"}</h2>
        </div>
        {source.at(-1)?.percentage_change != null && <span className={`delta ${(source.at(-1)?.percentage_change ?? 0) >= 0 ? "good" : "critical"}`}>{(source.at(-1)?.percentage_change ?? 0) >= 0 ? "↑" : "↓"} {Math.abs(source.at(-1)?.percentage_change ?? 0).toFixed(1)}%</span>}
      </div>
      <svg
        viewBox="0 0 300 170"
        role="img"
        aria-label="График роста AI Visibility"
      >
        <defs>
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#5b8cff" stopOpacity=".35" />
            <stop offset="1" stopColor="#5b8cff" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={`18,160 ${coords} 282,160`} fill="url(#area)" />
        <polyline
          points={coords}
          fill="none"
          stroke="#6f9cff"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((value, i) => (
          <circle
            key={i}
            cx={18 + i * 132}
            cy={150 - value}
            r="5"
            fill="#09111f"
            stroke="#8eb0ff"
            strokeWidth="3"
          />
        ))}
      </svg>
      <div className="timeline">
        {source.map((point, i) => (
          <div key={point.observed_at}>
            <span>{new Date(point.observed_at).toLocaleDateString("ru-RU", { day: "2-digit", month: "short" })}</span>
            <strong>{points[i].toFixed(0)}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function ActionCenter({ recommendations }: { recommendations: NonNullable<ReportShape["recommendations"]> }) {
  return (
    <section className="action-center">
      <div className="section-head">
        <div>
          <span className="eyebrow">ACTION CENTER</span>
          <h2>Что делать дальше</h2>
          <p>Рекомендации, рассчитанные для последнего исследования.</p>
        </div>
      </div>
      <div className="action-list">
        {recommendations.length ? recommendations.map((action, index) => (
          <article className="action-item" key={`${action.explanation}-${index}`}>
            <div>
              <span className="priority">{action.priority ?? "Приоритет не указан"}</span>
              <h3>{action.explanation ?? "Рекомендация"}</h3>
              <div className="action-facts">
                <b>{action.metric ?? "Метрика не указана"}</b>
                <span>{action.expected_effect ?? "Эффект не рассчитан"}</span>
              </div>
            </div>
          </article>
        )) : <div className="empty-state">Рекомендации не сформированы.</div>}
      </div>
      <button className="primary-action" onClick={() => { window.history.pushState({ screen: "recommendations" }, "", "/recommendations"); window.dispatchEvent(new PopStateEvent("popstate")); }}>Открыть рекомендации</button>
    </section>
  );
}

function PipelineStatus({ result, data }: { result: ReportResult; data: ReportShape }) {
  const rows = [
    ...(result.tasks ?? []).map((task) => ({ title: `${task.provider ?? "Provider"}/${task.model ?? "model"}`, detail: `${task.status} · ${new Date(task.created_at).toLocaleString("ru-RU")}${task.error ? ` · ${task.error}` : ""}`, done: task.status === "COMPLETED" })),
    ...(data.responses ?? []).map((response) => ({ title: `Response #${response.id}: ${response.processing_status}`, detail: `${response.provider}/${response.model} · ${response.total_tokens} токенов · ${response.latency_ms ?? "—"} ms · $${Number(response.cost).toFixed(6)}`, done: response.processing_status === "PROCESSED" })),
    ...(data.knowledge_graph_summary?.created_at ? [{ title: "Knowledge Graph", detail: new Date(data.knowledge_graph_summary.created_at).toLocaleString("ru-RU"), done: true }] : []),
    ...(typeof data.score?.calculated_at === "string" ? [{ title: "Scoring", detail: `${new Date(data.score.calculated_at).toLocaleString("ru-RU")} · v${String(data.score.version ?? "—")}`, done: true }] : []),
  ];
  return rows.length ? <Timeline items={rows} /> : <p className="empty-state">Pipeline stages не записаны для этого исследования.</p>;
}

function Wizard({
  onComplete,
  onCancel,
}: {
  onComplete: (result: ReportResult) => void;
  onCancel: () => void;
}) {
  const saved = useMemo(() => { try { return JSON.parse(sessionStorage.getItem("research-wizard") ?? "{}") as Partial<{ step: number; brand: string; region: string; language: string; profile: WizardPayload["routing_profile"] }>; } catch { return {}; } }, []);
  const [step, setStep] = useState(saved.step && saved.step >= 1 && saved.step <= 5 ? saved.step : 1);
  const [brand, setBrand] = useState(saved.brand ?? "");
  const [region, setRegion] = useState(saved.region ?? "GLOBAL");
  const [language, setLanguage] = useState(saved.language ?? "ru");
  const [profile, setProfile] = useState<WizardPayload["routing_profile"]>(saved.profile ?? "BALANCED");
  const [review, setReview] = useState<WizardReview>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { sessionStorage.setItem("research-wizard", JSON.stringify({ step, brand, region, language, profile })); }, [step, brand, region, language, profile]);
  const payload = (): WizardPayload => ({
    brand,
    routing_profile: profile,
    languages: [language],
    regions: [region],
    prompt_code: "ai-visibility",
    research_template_code: "ai-visibility",
  });
  async function next() {
    if (step < 4) return setStep(step + 1);
    setBusy(true);
    setError("");
    try {
      setReview(await api.review(payload()));
      setStep(5);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Не удалось проверить настройки",
      );
    } finally {
      setBusy(false);
    }
  }
  async function run() {
    setBusy(true);
    setError("");
    try {
      const result = await api.run(payload());
      if (result.research.status !== "COMPLETED") throw new Error("Исследование завершилось с ошибкой. Подробности доступны в разделе Research.");
      sessionStorage.removeItem("research-wizard");
      onComplete(result);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Не удалось запустить исследование",
      );
    } finally {
      setBusy(false);
    }
  }
  const titles = [
    "Как называется бренд?",
    "Где вы работаете?",
    "На каком языке искать?",
    "Как провести исследование?",
    "Всё готово к исследованию",
  ];
  return (
    <main className="wizard-page">
      <button
        className="back-link"
        onClick={step === 1 ? () => { sessionStorage.removeItem("research-wizard"); onCancel(); } : () => setStep(step - 1)}
      >
        ← {step === 1 ? "На главную" : "Назад"}
      </button>
      <div className="stepper">
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className={n <= step ? "active" : ""}>
            {n < step ? "✓" : n}
          </span>
        ))}
      </div>
      <section className="wizard-focus">
        <span className="eyebrow">ШАГ {step} ИЗ 5</span>
        <h1>{titles[step - 1]}</h1>
        <p>
          {step === 1
            ? "Введите название так, как его видят ваши клиенты."
            : step === 4
              ? "Выберите режим — Router сам найдёт подходящие доступные модели."
              : "Это поможет сделать исследование точнее."}
        </p>
        {step === 1 && (
          <label className="hero-field">
            Название бренда
            <input
              autoFocus
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="Например, Skinjestique"
            />
          </label>
        )}
        {step === 2 && (
          <div className="option-list">
            {[
              ["GLOBAL", "Весь мир"],
              ["RU", "Россия"],
              ["EU", "Европа"],
              ["US", "США"],
            ].map(([value, label]) => (
              <button
                className={region === value ? "selected" : ""}
                onClick={() => setRegion(value)}
                key={value}
              >
                <span>{label}</span>
                <small>{value}</small>
              </button>
            ))}
          </div>
        )}
        {step === 3 && (
          <div className="option-list">
            {[
              ["ru", "Русский"],
              ["en", "English"],
            ].map(([value, label]) => (
              <button
                className={language === value ? "selected" : ""}
                onClick={() => setLanguage(value)}
                key={value}
              >
                <span>{label}</span>
                <small>{value.toUpperCase()}</small>
              </button>
            ))}
          </div>
        )}
        {step === 4 && (
          <div className="model-grid routing-profile-grid">
            {routingProfiles.map(([value, title, description, icon]) => {
              return (
                <button
                  type="button"
                  className={`model routing-profile ${profile === value ? "active" : ""}`}
                  key={value}
                  onClick={() => setProfile(value)}
                >
                  <span className="provider-icon">{icon}</span>
                  <b>{title}</b>
                  <small>{description}</small>
                  <i>{profile === value ? "✓" : ""}</i>
                </button>
              );
            })}
          </div>
        )}
        {step === 5 && (
          <div className="review-card">
            <div>
              <span>Бренд</span>
              <b>{brand}</b>
            </div>
            <div>
              <span>Регион</span>
              <b>{region}</b>
            </div>
            <div>
              <span>Язык</span>
              <b>{language.toUpperCase()}</b>
            </div>
            <div>
              <span>Режим</span>
              <b>{routingProfiles.find(([value]) => value === profile)?.[1]}</b>
            </div>
            <p>{review?.prompt}</p>
            <div><span>Выбранные модели</span><b>{review?.selected_models?.join(", ") || review?.provider_models?.join(", ") || "Router не вернул план"}</b></div>
            <div><span>Оценка времени</span><b>{review?.estimated_time_ms ? `${review.estimated_time_ms} ms` : "Не рассчитана"}</b></div>
            <div><span>Оценка стоимости</span><b>{review?.estimated_cost_usd != null ? `$${review.estimated_cost_usd.toFixed(6)}` : "Не рассчитана"}</b></div>
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        <div className="wizard-actions">
          {step < 5 ? (
            <button
              onClick={next}
              disabled={busy || !brand}
            >
              {busy ? "Проверяем…" : step === 4 ? "Проверить" : "Продолжить"} →
            </button>
          ) : (
            <button onClick={run} disabled={busy}>
              {busy ? "Собираем ответы…" : "Запустить исследование"}
            </button>
          )}
        </div>
      </section>
    </main>
  );
}

const metricNames: Record<string, string> = { mention_score: "Упоминания", recommendation_score: "Рекомендации", citation_score: "Цитирование", coverage_score: "Покрытие", confidence_score: "Достоверность", visibility_score: "AI-видимость" };
function cleanBrand(title: string) { const raw = title.replace(/^AI Visibility:\s*/i, "").trim(); return raw ? raw.charAt(0).toLocaleUpperCase() + raw.slice(1) : "Бренд"; }

function RecommendationCard({ recommendation, plan, simulation }: { recommendation: NonNullable<ReportShape["recommendations"]>[number]; plan?: ActionPlanItem; simulation?: SimulationItem }) {
  const metric = metricNames[recommendation.metric ?? ""] ?? recommendation.metric ?? "Метрика";
  const priorities: Record<string, string> = { LOW: "НИЗКИЙ", MEDIUM: "СРЕДНИЙ", HIGH: "ВЫСОКИЙ", CRITICAL: "КРИТИЧЕСКИЙ" };
  return (
    <article className="action-card">
      <div className="action-top">
        <span className="priority">{priorities[recommendation.priority ?? ""] ?? "Приоритет не указан"}</span>
        <span>{metric} · сейчас {recommendation.metric_value?.toFixed(1) ?? "—"}</span>
      </div>
      <h3>{plan?.template?.title ?? `Улучшить показатель «${metric}»`}</h3>
      <p><b>Почему:</b> {metric} имеет значение {recommendation.metric_value?.toFixed(1) ?? "—"} из 100; детерминированное правило версии 1.0 сработало для исследования.</p>
      <p><b>Что сделать:</b> {plan?.template?.description ?? recommendation.explanation ?? "Открыть рекомендации и подготовить план улучшения."}</p>
      {plan?.steps?.length ? <ol>{plan.steps.map((step) => <li key={step}>{step}</li>)}</ol> : null}
      <div className="action-meta">
        <div>
          <span>Ожидаемый эффект</span>
          <b className="good">{simulation ? `ПРОГНОЗ: +${simulation.expected_metric_change.toFixed(1)} к «${metric}»` : plan?.expected_effect ?? recommendation.expected_effect ?? "Не рассчитан"}</b>
        </div>
        <div><span>Вероятность</span><b>{simulation ? `${simulation.confidence_min.toFixed(0)}–${simulation.confidence_max.toFixed(0)}%` : "Не рассчитана"}</b></div>
        <div><span>Срок</span><b>{plan?.estimated_time ?? (simulation ? `${simulation.estimated_duration_days} дней` : "Не рассчитан")}</b></div>
      </div>
    </article>
  );
}

function Report({
  result,
  onHome,
}: {
  result: ReportResult;
  onHome: () => void;
}) {
  const report = result.report as ReportShape;
  const score = report.score ?? {};
  const brand = cleanBrand(result.research.title);
  const visibility = valueOf(score, "visibility_score");
  const weakest = metricMeta.map(([label, key]) => ({ label, value: valueOf(score, key) })).sort((a, b) => a.value - b.value)[0];
  const visibilityMetric = report.trend?.metrics?.find((item) => item.metric === "visibility");
  const latestDelta = visibilityMetric?.points.at(-1)?.percentage_change;
  const strengths = metricMeta
    .filter(([, key]) => valueOf(score, key) >= 80)
    .map(([label]) => label);
  const responses = report.responses ?? [];
  const models = [...new Set(responses.map((item) => `${item.provider}/${item.model}`))];
  const graph = report.knowledge_graph_summary;
  const previousPoint = visibilityMetric?.points.at(-2);
  const currentPoint = visibilityMetric?.points.at(-1);
  const evidenceResearch = (report.research ?? result.research) as ResearchItem;
  const visibilityEvidence = metricEvidence("visibility_score", report, evidenceResearch);
  const planFor = (recommendation: NonNullable<ReportShape["recommendations"]>[number]) => result.actionPlan?.items.find((item) => item.recommendation.metric === recommendation.metric);
  const simulationFor = (recommendation: NonNullable<ReportShape["recommendations"]>[number]) => result.simulation?.simulations.find((item) => item.metric === recommendation.metric);
  return (
    <main className="page report-page">
      <button className="back-link" onClick={onHome}>
        ← К обзору
      </button>
      <section className="report-hero">
        <div>
          <span className="eyebrow">
            АНАЛИТИЧЕСКИЙ ОТЧЁТ · #{result.research.id}
          </span>
          <h1>{brand}</h1>
          <p>AI-видимость бренда составляет {visibility.toFixed(1)} из 100. Главная точка роста — «{weakest.label}» ({weakest.value.toFixed(1)}). Оценка основана только на сохранённых результатах исследования #{result.research.id}.</p>
        </div>
        <div className="report-score">
          <span>AI-видимость</span>
          <strong>{visibility.toFixed(1)}</strong>
          <em className={latestDelta == null ? "" : latestDelta >= 0 ? "good" : "critical"}>{latestDelta == null ? "Нет сравнения" : `${latestDelta >= 0 ? "↑" : "↓"} ${Math.abs(latestDelta).toFixed(1)}%`}</em>
        </div>
      </section>
      <nav className="report-nav" aria-label="Разделы отчёта"><a href="#summary">Сводка</a><a href="#findings">Выводы</a><a href="#evidence">Доказательства</a><a href="#sources">Источники</a><a href="#graph">Граф</a><a href="#actions">План действий</a></nav>
      <section id="summary" className="panel report-proof"><div><span>Как сформирована оценка</span><strong>{visibility.toFixed(1)}</strong></div><dl><div><dt>Моделей</dt><dd>{models.length}</dd></div><div><dt>Ответов</dt><dd>{responses.length}</dd></div><div><dt>Сущностей</dt><dd>{report.detected_entities?.length ?? 0}</dd></div><div><dt>Рекомендаций</dt><dd>{report.recommendations?.length ?? 0}</dd></div><div><dt>Исследование</dt><dd>#{result.research.id}</dd></div><div><dt>Алгоритм</dt><dd>{String(score.version ?? "не указан")}</dd></div></dl><details><summary>Показать расчёт</summary>{visibilityEvidence.lines.map((line) => <p key={line}>{line}</p>)}<code>{visibilityEvidence.formula}</code></details></section>
      <section className="explainability-stack" aria-label="Первичные доказательства">
        <article className="panel"><span className="section-label">МЕТОДОЛОГИЯ · v{report.explainability?.methodology_version ?? score.version ?? "—"}</span><h2>Расчёт каждой метрики</h2>{report.explainability ? Object.entries(report.explainability.metrics).map(([key, metric]) => <details className="evidence-details" key={key}><summary>{metricNames[key] ?? key} · {metric.status ? "не рассчитывается" : valueOf(score, key).toFixed(1)}</summary>{metric.status ? <p>Эта метрика не входит в production Scoring v1.0 и не влияет на AI-видимость.</p> : <><p><b>Формула:</b> {metric.formula}</p><p><b>Нормализация:</b> {metric.normalization}</p><p><b>Вес:</b> {metric.weight == null ? "не применяется" : `${metric.weight * 100}%`}</p><pre>{JSON.stringify(metric.inputs, null, 2)}</pre></>}</details>) : <p className="empty-state">Для старого исследования методология не сохранена в report payload.</p>}</article>
        <article className="panel"><span className="section-label">КАТАЛОГ ЗАПРОСОВ</span><h2>На основании каких запросов рассчитан рейтинг</h2>{report.explainability?.prompts.length ? report.explainability.prompts.map((prompt) => <details className="evidence-details" key={prompt.uuid}><summary>{prompt.provider}/{prompt.model} · ответ #{prompt.response_id}</summary><p><b>UUID:</b> {prompt.uuid}</p><p><b>Язык:</b> {String(prompt.language ?? "не записан")} · <b>Страна:</b> {String(prompt.country ?? "не записана")}</p><pre className="raw-evidence">{prompt.text || "Текст запроса не был записан"}</pre></details>) : <p className="empty-state">Запросы не были записаны для этого исследования.</p>}</article>
        <article className="panel"><span className="section-label">ИСХОДНЫЕ ОТВЕТЫ МОДЕЛЕЙ</span><h2>Ответы без сокращений</h2>{report.explainability?.responses.length ? report.explainability.responses.map((response) => <details className="evidence-details" key={response.response_id}><summary>{response.provider}/{response.model} · {response.tokens} токенов · {response.latency_ms ?? "—"} ms</summary><p>Стоимость ${Number(response.cost).toFixed(6)} · завершён {new Date(response.finished_at).toLocaleString("ru-RU")}</p>{response.error_type ? <div className="error">{response.error_type}: {response.error_message}</div> : null}<p>Сущности: {response.entity_ids.length} · источники: {response.citation_ids.length} · рекомендации: {response.recommendation_ids.length}</p><h3>Исходный ответ</h3><pre className="raw-evidence">{JSON.stringify(response.raw_response, null, 2)}</pre><h3>Нормализованный ответ</h3><pre className="raw-evidence">{JSON.stringify(response.normalized_response, null, 2)}</pre></details>) : <p className="empty-state">Ответы моделей отсутствуют.</p>}</article>
        <article className="panel"><span className="section-label">АНАЛИЗ ЦИТИРОВАНИЯ</span><h2>Источники по моделям и доменам</h2>{responses.map((response) => { const citations = report.explainability?.citations.filter((item) => item.response_id === response.id) ?? []; return <div className="citation-model-row" key={response.id}><b>{response.provider}/{response.model}</b><span>{citations.length ? `${citations.length} источников: ${[...new Set(citations.map((item) => item.domain ?? item.source ?? "без домена"))].join(", ")}` : "внешние источники не обнаружены"}</span></div>; })}</article>
      </section>
      <section className="score-strip">
        {[["Visibility", "visibility_score"], ...metricMeta].map(
          ([label, key]) => (
            <div key={key}>
              <span>{metricNames[String(key)] ?? label}</span>
              <strong>{valueOf(score, key).toFixed(1)}</strong>
              <i className={tone(valueOf(score, key))} />
            </div>
          ),
        )}
      </section>
      <section id="evidence" className="report-layout">
        <article className="panel strengths">
          <span className="section-label">СИЛЬНЫЕ СТОРОНЫ</span>
          <h2>Что уже работает</h2>
          {strengths.length ? strengths.map((item) => {
            const key = metricMeta.find(([label]) => label === item)?.[1] ?? "visibility_score";
            const evidence = metricEvidence(key, report, evidenceResearch);
            return (
            <div className="strength" key={item}>
              <span>★★★★★</span>
              <b>{metricNames[key] ?? item} · {valueOf(score, key).toFixed(1)}</b>
              <small>{evidence.lines.join(" · ")}</small>
            </div>
          )}) : <p className="empty-state">Метрик выше 80 баллов в текущем исследовании нет.</p>}
        </article>
        <article className="panel weakness">
          <span className="section-label">ГЛАВНОЕ ОГРАНИЧЕНИЕ</span>
          <h2>{weakest.label}</h2>
          <strong>{weakest.value.toFixed(1)}</strong>
          <p>Минимальное значение среди метрик текущего исследования.</p>
          <div className="track">
            <span className={tone(weakest.value)} style={{ width: `${weakest.value}%` }} />
          </div>
        </article>
        <article id="findings" className="panel narrative">
          <span className="section-label">КЛЮЧЕВЫЕ ВЫВОДЫ</span>
          <h2>Изменение относительно предыдущего исследования</h2>
          {previousPoint && currentPoint ? <div className="finding-change"><span>Было <b>{previousPoint.value.toFixed(1)}</b> · {new Date(previousPoint.observed_at).toLocaleDateString("ru-RU")}</span><span>Стало <b>{currentPoint.value.toFixed(1)}</b> · {new Date(currentPoint.observed_at).toLocaleDateString("ru-RU")}</span><p>Изменение: {currentPoint.percentage_change == null ? "не рассчитано" : `${currentPoint.percentage_change >= 0 ? "+" : ""}${currentPoint.percentage_change.toFixed(1)}%`}. Причина определяется фактическими ответами, источниками и покрытием текущего запуска.</p></div> : <p className="empty-state">Недостаточно данных для сравнения: требуется предыдущее исследование того же объекта.</p>}
        </article>
        <article id="sources" className="panel sources">
          <span className="section-label">ИСТОЧНИКИ ЗНАНИЙ</span>
          <h2>Источники знаний</h2>
          <div className="source-number">{report.sources?.length ?? 0}</div>
          {report.sources?.length ? <ul>{report.sources.map((source, index) => <li key={source.id ?? index}>{source.title ?? source.source ?? source.url ?? "Источник без названия"}{source.url ? <a href={source.url} target="_blank" rel="noreferrer">Открыть</a> : null}</li>)}</ul> : <p className="empty-state"><b>Источники отсутствуют.</b> В ответах моделей не найдено независимых внешних подтверждений: официальных сайтов, энциклопедий, научных публикаций или отраслевых СМИ. Поэтому «Цитирование» равно {valueOf(score, "citation_score").toFixed(1)}.</p>}
        </article>
      </section>
      <section id="graph" className="panel report-graph"><span className="section-label">ГРАФ ЗНАНИЙ</span><h2>{graph?.node_count ?? 0} узлов · {graph?.edge_count ?? 0} связей</h2>{(graph?.edge_count ?? 0) > 0 ? <p>Связи построены из извлечённых сущностей и доказательств текущего исследования. Подробности доступны в разделе «Граф знаний».</p> : <p className="empty-state"><b>Связи не найдены.</b> Извлечённых сущностей недостаточно либо ответы не содержат подтверждённых отношений между ними.</p>}</section>
      <section id="actions" className="plan-section">
        <div className="section-head">
          <div>
            <span className="eyebrow">ПЛАН ДЕЙСТВИЙ</span>
            <h2>Как улучшить результат</h2>
          </div>
        </div>
        {report.recommendations?.length ? report.recommendations.map((recommendation, index) => <RecommendationCard recommendation={recommendation} plan={planFor(recommendation)} simulation={simulationFor(recommendation)} key={`${recommendation.explanation}-${index}`} />) : <div className="empty-state">Рекомендации не сформированы: все правила v1 пройдены либо недостаточно данных.</div>}
      </section>
      <section className="report-footer panel">
        <div>
          <span>Сущности</span>
          <b>{report.detected_entities?.length ?? 0}</b>
        </div>
        <div>
          <span>Источники</span>
          <b>{report.sources?.length ?? 0}</b>
        </div>
        <div>
          <span>Время выполнения</span>
          <b>{((report.execution_time_ms ?? report.latency_ms ?? 0) / 1000).toFixed(1)} сек</b>
        </div>
        <div>
          <span>Токены</span>
          <b>{report.token_usage ?? 0}</b>
        </div>
        <div>
          <span>Стоимость</span>
          <b>${Number(report.cost ?? 0).toFixed(6)}</b>
        </div>
        <div><span>Модели</span><b>{models.length}</b></div>
        <div><span>Ответы</span><b>{responses.length}</b></div>
        <div><span>Связи графа</span><b>{graph?.edge_count ?? 0}</b></div>
        <div><span>Рекомендации</span><b>{report.recommendations?.length ?? 0}</b></div>
      </section>
    </main>
  );
}

function App() {
  const [user, setUser] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [screen, setScreen] = useState<Screen>(
    () => pathScreens[window.location.pathname] ?? "home",
  );
  const [report, setReport] = useState<ReportResult>();
  const [loading, setLoading] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const loadReport = useCallback(async (research: ResearchItem) => {
    const [data, tasks, actionPlan, simulation] = await Promise.all([
      api.finalReport(research.id), api.researchTasks(research.id).catch(() => []),
      api.actionPlan(research.id).catch(() => undefined), api.simulation(research.id).catch(() => undefined),
    ]);
    setReport({ research, report_url: `/research/${research.id}/final-report`, report: data, tasks, actionPlan, simulation });
  }, []);
  const navigate = useCallback((next: Screen, replace = false) => {
    const path = screenPaths[next];
    window.history[replace ? "replaceState" : "pushState"]({ screen: next }, "", path);
    setScreen(next);
  }, []);
  useEffect(() => {
    const onPopState = () => setScreen(pathScreens[window.location.pathname] ?? "home");
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  useEffect(() => {
    api.restoreSession()
      .then(() => api.me())
      .then((profile) => { setUser(profile.display_name); setRoles(profile.roles); setLoading(true); })
      .catch(() => undefined)
      .finally(() => setAuthReady(true));
  }, []);
  useEffect(() => {
    if (!user || report) return;
    api
      .listResearch()
      .then(async (items) => {
        const latest = [...items].sort((a, b) => b.id - a.id)[0];
        if (!latest) return;
        await loadReport(latest);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [user, report, loadReport]);
  const isAdmin = roles.some((role) => ["superadmin", "admin", "organization_admin", "SUPERADMIN", "ADMIN", "ORGANIZATION_ADMIN"].includes(role));
  const content = useMemo(
    () =>
      screen === "wizard" ? (
        <Wizard
          onCancel={() => navigate("home")}
          onComplete={(value) => { loadReport(value.research as ResearchItem).then(() => navigate("report")); }}
        />
      ) : screen === "research" ? (
        <RecordsScreen key="research" kind="research" onNewResearch={() => navigate("wizard")} />
      ) : screen === "reports" ? (
        <RecordsScreen key="reports" kind="reports" onNewResearch={() => navigate("wizard")} />
      ) : screen === "recommendations" ? (
        <RecordsScreen key="recommendations" kind="recommendations" onNewResearch={() => navigate("wizard")} />
      ) : screen === "graph" ? (
        <GraphScreen />
      ) : screen === "competitors" ? (
        <RecordsScreen key="competitors" kind="competitors" onNewResearch={() => navigate("wizard")} />
      ) : screen === "history" ? (
        <RecordsScreen key="history" kind="history" onNewResearch={() => navigate("wizard")} />
      ) : screen === "feedback" ? (
        <RecordsScreen key="feedback" kind="feedback" onNewResearch={() => navigate("wizard")} />
      ) : screen === "profile" ? (
        <RecordsScreen key="profile" kind="profile" onNewResearch={() => navigate("wizard")} />
      ) : screen === "providers" ? (
        <ProvidersDashboard />
      ) : screen === "analytics" && isAdmin ? (
        <ProductAnalyticsScreen />
      ) : screen === "notifications" ? (
        <NotificationsScreen />
      ) : screen === "organization" ? (
        <OrganizationScreen />
      ) : screen === "settings" ? (
        <SettingsScreen user={user} />
      ) : screen === "admin" && isAdmin ? (
        <AdminConsoleScreen />
      ) : screen === "admin" || screen === "analytics" ? (
        <main className="analytics-page"><div className="error" role="alert">Недостаточно прав для просмотра этого раздела.</div></main>
      ) : screen === "onboarding" ? (
        <OnboardingScreen onResearch={() => navigate("wizard")} onOrganization={() => navigate("organization")} />
      ) : screen === "report" && report ? (
        <Report result={report} onHome={() => navigate("home")} />
      ) : loading ? (
        <DashboardSkeleton />
      ) : (
        <Dashboard
          report={report}
          onStart={() => navigate("wizard")}
          onOpen={(researchId) => {
            if (researchId && researchId !== report?.research.id) {
              api.listResearch().then((items) => { const target = items.find((item) => item.id === researchId); return target ? loadReport(target) : undefined; }).then(() => navigate("report")).catch(() => undefined);
            } else navigate("report");
          }}
          onNavigate={navigate}
        />
      ),
    [screen, report, loading, user, isAdmin, navigate, loadReport],
  );
  if (!authReady) return <DashboardSkeleton />;
  if (!user)
    return (
      <Login
        onReady={(profile) => {
          setLoading(true);
          setUser(profile.display_name);
          setRoles(profile.roles);
          navigate(pathScreens[window.location.pathname] ?? "home", true);
        }}
      />
    );
  return (
    <Shell
      user={user}
      roles={roles}
      active={screen}
      onNavigate={navigate}
      onLogout={() => {
        setUser("");
        setRoles([]);
        setReport(undefined);
        navigate("home", true);
      }}
    >
      {content}
    </Shell>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
