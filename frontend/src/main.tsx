import { StrictMode, useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ApiClient,
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
  type WorkspaceProjectItem,
  type WizardPayload,
  type WizardReview,
} from "./api";
import {
  AreaLineChart,
  Heatmap,
  NetworkGraph,
  RadarChart,
  Treemap,
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
  ["Mention", "mention_score"],
  ["Recommendation", "recommendation_score"],
  ["Citation", "citation_score"],
  ["Coverage", "coverage_score"],
  ["Confidence", "confidence_score"],
] as const;

type Screen = "home" | "research" | "wizard" | "reports" | "report" | "recommendations" | "graph" | "competitors" | "history" | "providers" | "analytics" | "notifications" | "organization" | "settings" | "feedback" | "profile" | "admin" | "onboarding";
type ReportShape = {
  executive_summary?: string;
  score?: Record<string, number | string>;
  trend?: { points?: Array<Record<string, unknown>> };
  benchmark?: Record<string, unknown>;
  insights?: Array<{ title?: string; explanation?: string }>;
  recommendations?: Array<{
    explanation?: string;
    priority?: string;
    metric?: string;
  }>;
  detected_entities?: unknown[];
  sources?: unknown[];
  latency_ms?: number;
  token_usage?: number;
  cost?: number;
};

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

function Login({ onReady }: { onReady: (name: string) => void }) {
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
      onReady((await api.me()).display_name);
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
}: {
  user: string;
  children: React.ReactNode;
  onNavigate: (screen: Screen) => void;
  active: Screen;
  onLogout: () => void;
}) {
  const nav = [
    ["⌂", "Dashboard", "home"], ["→", "Getting Started", "onboarding"],
    ["◉", "Research", "research"], ["▤", "Reports", "reports"],
    ["✓", "Recommendations", "recommendations"], ["⌘", "Knowledge Graph", "graph"],
    ["◇", "Competitors", "competitors"], ["↗", "History", "history"],
    ["✦", "AI Providers", "providers"], ["◫", "Product Analytics", "analytics"],
    ["♢", "Notifications", "notifications"], ["◎", "Organizations", "organization"],
    ["◌", "Feedback", "feedback"], ["♙", "User Profile", "profile"],
    ["⚙", "Settings", "settings"], ["▦", "Admin Console", "admin"],
  ] as const;
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
            <Badge tone="success">● Система работает</Badge>
            <button className="icon-button" aria-label="Уведомления">
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
  useEffect(() => { Promise.all([api.workspace(), api.listProviders(), api.apiKeys()]).then(([workspace, providerItems, apiKeyItems]) => { setSettings((current) => ({ ...current, ...workspace.settings })); setProviders(providerItems); setKeys(apiKeyItems); }).catch(() => undefined); }, []);
  const tabs = [["profile", "Профиль"], ["security", "Безопасность"], ["api", "API Keys"], ["providers", "LLM Providers"], ["preferences", "Язык и регион"], ["notifications", "Уведомления"], ["theme", "Тема"], ["organization", "Организация"]];
  const set = (key: string, value: unknown) => { setSaved(false); setSettings((current) => ({ ...current, [key]: value })); };
  return <main className="analytics-page settings-page"><header className="analytics-hero"><div><span className="eyebrow">PREFERENCES</span><h1>Настройки</h1><p>Единый центр персональных и системных настроек.</p></div><button className="primary-action" onClick={() => api.updateWorkspace(settings).then(() => setSaved(true))}>{saved ? "Сохранено ✓" : "Сохранить"}</button></header>
    <div className="settings-layout"><nav className="settings-nav">{tabs.map(([key, label]) => <button className={tab === key ? "active" : ""} onClick={() => setTab(key)} key={key}>{label}</button>)}</nav><section className="analytics-card settings-panel">
      {tab === "profile" && <><h2>Профиль</h2><label>Имя<input value={user} disabled /></label><p className="empty-state">Контактные данные управляются Authentication.</p></>}
      {tab === "security" && <><h2>Безопасность</h2><div className="setting-row"><span>JWT-сессии и refresh rotation</span><b>Активно</b></div><div className="setting-row"><span>Отзыв токенов при выходе</span><b>Активно</b></div></>}
      {tab === "api" && <><h2>API Keys</h2>{keys.map((key) => <div className="setting-row" key={key.id}><span>{key.name}</span><code>{key.prefix}••••</code></div>)}</>}
      {tab === "providers" && <><h2>LLM Providers</h2>{providers.map((provider) => <div className="setting-row" key={provider.id}><span>{provider.display_name}</span><b>{provider.availability}</b></div>)}</>}
      {tab === "preferences" && <><h2>Язык и регион</h2><label>Язык<select value={String(settings.language)} onChange={(event) => set("language", event.target.value)}><option value="ru">Русский</option><option value="en">English</option></select></label><label>Регион<select value={String(settings.region)} onChange={(event) => set("region", event.target.value)}><option>GLOBAL</option><option>RU</option><option>EU</option><option>US</option></select></label></>}
      {tab === "notifications" && <><h2>Уведомления</h2><label className="toggle-row"><input type="checkbox" checked={Boolean((settings.notifications as Record<string, boolean>)?.in_app)} onChange={(event) => set("notifications", { ...(settings.notifications as object), in_app: event.target.checked })}/>In-app</label><label className="toggle-row"><input type="checkbox" checked={Boolean((settings.notifications as Record<string, boolean>)?.email)} onChange={(event) => set("notifications", { ...(settings.notifications as object), email: event.target.checked })}/>Email</label></>}
      {tab === "theme" && <><h2>Тема</h2><div className="theme-options">{["dark", "light", "system"].map((theme) => <button className={settings.theme === theme ? "active" : ""} onClick={() => set("theme", theme)} key={theme}>{theme}</button>)}</div></>}
      {tab === "organization" && <><h2>Организация</h2><p>Профиль, участники, роли и лимиты доступны в Organization Workspace.</p></>}
    </section></div></main>;
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

function OnboardingScreen({ onResearch }: { onResearch: () => void }) {
  const [organizations, setOrganizations] = useState<OrganizationItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => { api.organizations().then(setOrganizations).catch(() => undefined); }, []);
  const ready = organizations.length > 0;
  async function createDemoWorkspace() {
    setBusy(true); setMessage("");
    try {
      const existing = organizations.find((item) => item.slug === "demo-organization");
      const organization = existing ?? await api.createOrganization({ name: "Demo Organization", slug: "demo-organization" });
      await api.switchOrganization(organization.id);
      setOrganizations((items) => existing ? items : [...items, organization]);
      setMessage("Demo Organization готова. Можно запускать первое исследование.");
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Не удалось подготовить demo"); }
    finally { setBusy(false); }
  }
  return <main className="analytics-page onboarding-page"><header className="analytics-hero"><div><span className="eyebrow">CLOSED BETA</span><h1>Начните с первого результата</h1><p>Три коротких шага — и AI Ranking OS покажет, как модели видят ваш бренд.</p></div><Badge tone={ready ? "success" : "warning"}>● {ready ? "Workspace готов" : "Нужна организация"}</Badge></header>
    <section className="onboarding-steps"><article className="analytics-card onboarding-step"><span>01</span><h2>Создайте пространство</h2><p>Организация объединяет команду, проекты и лимиты.</p><button onClick={createDemoWorkspace} disabled={busy || ready}>{ready ? "Готово ✓" : busy ? "Создаём…" : "Создать Demo Organization"}</button></article><article className="analytics-card onboarding-step"><span>02</span><h2>Проверьте Skinjestique</h2><p>Воспроизводимый пример уже настроен в Research Wizard.</p><button onClick={onResearch} disabled={!ready}>Открыть исследование</button></article><article className="analytics-card onboarding-step"><span>03</span><h2>Получите отчёт</h2><p>Visibility, источники и план действий собираются автоматически.</p><div className="onboarding-result">Report → Share → Improve</div></article></section>
    {message && <div className="onboarding-message">{message}</div>}<section className="analytics-card beta-expectations"><h3>Что проверить в закрытой бете</h3><div><span>Исследование проходит без ручного вмешательства</span><b>Pipeline</b></div><div><span>Рекомендации понятны и применимы</span><b>Value</b></div><div><span>Отчёт можно передать клиенту</span><b>Sharing</b></div></section>
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
  const load = useCallback(() => api.organizations().then((items) => { setOrganizations(items); setSelected((current) => current ?? items.find((item) => item.is_default)?.id ?? items[0]?.id); }), []);
  useEffect(() => { load().catch(() => undefined); }, [load]);
  useEffect(() => { if (!selected) return; Promise.all([api.organizationMembers(selected), api.organizationActivity(selected)]).then(([memberItems, actions]) => { setMembers(memberItems); setActivity(actions); }).catch(() => undefined); }, [selected]);
  const current = organizations.find((item) => item.id === selected);
  return <main className="analytics-page organization-page"><header className="analytics-hero"><div><span className="eyebrow">TEAM WORKSPACE</span><h1>{current?.name ?? "Организация"}</h1><p>Участники, проекты, лимиты и журнал активности команды.</p></div><select value={selected ?? ""} onChange={(event) => { const id = Number(event.target.value); api.switchOrganization(id).then(() => { setSelected(id); load(); }); }}>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.role}</option>)}</select></header>
    <section className="analytics-kpis"><article className="analytics-card metric"><span>Участники</span><strong>{members.length}</strong><small>из {current?.limits.members ?? "—"}</small></article><article className="analytics-card metric"><span>Проекты</span><strong>{current?.limits.projects ?? "—"}</strong><small>доступный лимит</small></article><article className="analytics-card metric"><span>Часовой пояс</span><strong className="small-value">{current?.timezone ?? "UTC"}</strong><small>{current?.country ?? "GLOBAL"}</small></article></section>
    <section className="analytics-grid"><article className="analytics-card"><h3>Команда</h3>{members.map((member) => <div className="rank-row" key={member.id}><span>User {member.user_id}</span><b>{member.role}</b></div>)}<form className="invite-form" onSubmit={(event) => { event.preventDefault(); if (selected) api.inviteOrganizationMember(selected, email).then(() => setEmail("")); }}><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="email нового участника" required/><button>Пригласить</button></form></article><article className="analytics-card"><h3>Журнал активности</h3>{activity.slice(0, 8).map((item) => <div className="activity-row" key={item.id}><span>{item.action.replaceAll("_", " ")}</span><small>{new Date(item.created_at).toLocaleString("ru-RU")}</small></div>)}</article></section>
  </main>;
}

function NotificationsScreen() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [category, setCategory] = useState("");
  const [summary, setSummary] = useState({ unread: 0, total: 0, archived: 0 });
  const load = useCallback(
    () => Promise.all([api.notifications(category), api.notificationSummary()])
      .then(([notifications, counts]) => { setItems(notifications); setSummary(counts); }),
    [category],
  );
  useEffect(() => { load().catch(() => undefined); }, [load]);
  return <main className="analytics-page notifications-page">
    <header className="analytics-hero"><div><span className="eyebrow">INBOX</span><h1>Уведомления</h1><p>Важные изменения проектов, исследований и вашей организации.</p></div>
      <div className="notification-summary"><b>{summary.unread}</b><span>непрочитанных</span></div></header>
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
          {trendPoints.length ? <AreaLineChart values={trendPoints.map((point) => point.value)} /> : <p className="empty-state">События появятся после первого действия.</p>}
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
  const [costs, setCosts] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.listProviders(), api.routerStatus()])
      .then(([items, status]) => { setProviders(items); setCosts(status.costs); })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки"));
  }, []);
  const available = providers.filter((item) => item.availability === "AVAILABLE").length;
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
            {providers.map((provider) => <article className="panel provider-card" key={provider.id}>
              <header><span className="provider-logo">{provider.display_name.slice(0,2).toUpperCase()}</span>
                <div><h2>{provider.display_name}</h2><small>{provider.id}</small></div>
                <Badge tone={provider.availability === 'AVAILABLE' ? 'success' : 'warning'}>{provider.availability}</Badge></header>
              <div className="provider-stats"><div><span>Context</span><b>{Math.round(provider.context_window/1000)}K</b></div><div><span>Priority</span><b>#{provider.priority}</b></div><div><span>Tier</span><b>{provider.free_tier?'FREE':'PAID'}</b></div></div>
              <div className="capability-tags">{provider.capabilities.slice(0,6).map(cap => <span key={cap}>{cap}</span>)}</div>
            </article>)}
          </section>
        </>
      )}
    </main>
  );
}

function MetricBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-row">
      <div>
        <span>{label}</span>
        <strong>{value.toFixed(value % 1 ? 1 : 0)}</strong>
      </div>
      <div className="track" aria-label={`${label}: ${value}`}>
        <span
          className={tone(value)}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}

function Dashboard({
  report,
  onStart,
  onOpen,
}: {
  report?: ReportResult;
  onStart: () => void;
  onOpen: () => void;
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
            <button className="choice">
              <span className="choice-icon">◇</span>
              <b>Исследовать конкурента</b>
              <small>Сравнить позиции и рекомендации</small>
              <i>Скоро</i>
            </button>
            <button className="choice">
              <span className="choice-icon">↗</span>
              <b>Посмотреть историю</b>
              <small>Следить за динамикой показателей</small>
              <i>Скоро</i>
            </button>
            <button className="choice">
              <span className="choice-icon">✓</span>
              <b>Открыть рекомендации</b>
              <small>Перейти к плану улучшений</small>
              <i>Скоро</i>
            </button>
          </div>
        </section>
      </main>
    );
  const data = report.report as ReportShape;
  const score = data.score ?? {};
  const visibility = valueOf(score, "visibility_score");
  const weakest = metricMeta
    .map(([label, key]) => ({ label, value: valueOf(score, key) }))
    .sort((a, b) => a.value - b.value)[0];
  const kpis = [
    ["✦", "Recommendation", "recommendation_score", 3.1],
    ["◎", "Coverage", "coverage_score", 1.8],
    ["↗", "Citation", "citation_score", -2.4],
    ["◆", "Authority", "confidence_score", 2.2],
    ["⌁", "Trend", "visibility_score", 4.2],
  ] as const;
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
          <h1>{report.research.title.replace(/^AI Visibility:\s*/, "")}</h1>
          <p>Последнее исследование · данные обновлены недавно</p>
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
          <div className="rating" aria-label="Пять звёзд">
            ★★★★★
          </div>
          <div className="delta good">
            ↑ 4.2 <span>за последний месяц</span>
          </div>
          <button className="text-action" onClick={onOpen}>
            Открыть полный отчёт →
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
            <p>
              Сильное присутствие в AI-ответах. Основной резерв роста — качество
              подтверждающих источников.
            </p>
            <div className="problem">
              <span>Главная проблема</span>
              <b>{weakest.label}</b>
              <em>{weakest.value.toFixed(1)}</em>
            </div>
          </div>
        </article>
      </section>
      <section className="kpi-grid">
        {kpis.map(([icon, title, key, delta], index) => (
          <KpiCard
            key={title}
            icon={icon}
            title={title}
            value={valueOf(score, key)}
            delta={delta}
            points={[
              56 + index * 2,
              64 + index,
              61 + index * 3,
              74 + index * 2,
              valueOf(score, key),
            ]}
            onClick={() => setDetail(title)}
          />
        ))}
      </section>
      <section className="analytics-grid">
        <ChartContainer
          title="Динамика AI Visibility"
          caption="TREND"
          action={<Badge tone="success">↑ 8% за период</Badge>}
        >
          <AreaLineChart values={[68, 72, 71, 78, 82, visibility]} />
        </ChartContainer>
        <ChartContainer title="Баланс AI-сигналов" caption="RADAR">
          <RadarChart
            labels={[
              "Visibility",
              "Citation",
              "Coverage",
              "Authority",
              "Recommend",
              "Confidence",
            ]}
            values={[
              visibility,
              valueOf(score, "citation_score"),
              valueOf(score, "coverage_score"),
              valueOf(score, "confidence_score"),
              valueOf(score, "recommendation_score"),
              valueOf(score, "confidence_score"),
            ]}
          />
        </ChartContainer>
        <ChartContainer title="Pipeline исследования" caption="TIMELINE">
          <Timeline
            items={[
              {
                title: "Исследование завершено",
                detail: "Ответы всех моделей получены",
                done: true,
              },
              {
                title: "Граф построен",
                detail: "Сущности и связи обработаны",
                done: true,
              },
              {
                title: "Отчёт сформирован",
                detail: "Метрики рассчитаны",
                done: true,
              },
              {
                title: "Рекомендации готовы",
                detail: "План доступен в Action Center",
                done: true,
              },
              { title: "Следующая проверка", detail: "Через 30 дней" },
            ]}
          />
        </ChartContainer>
        <Benchmark visibility={visibility} />
        <Trend visibility={visibility} />
      </section>
      <ActionCenter citation={valueOf(score, "citation_score")} />
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
        <p>
          Показатель рассчитан по упоминаниям бренда, позиции рекомендации,
          качеству источников и согласованности ответов выбранных моделей.
        </p>
        <h3>Что влияет</h3>
        <MetricBar label="Качество источников" value={activeValue} />
        <MetricBar
          label="Покрытие моделей"
          value={Math.min(100, activeValue + 12)}
        />
        <div className="drawer-callout">
          <span>Ожидаемый рост</span>
          <strong>+{Math.max(6, Math.round((85 - activeValue) * 0.35))}</strong>
          <p>После выполнения приоритетного действия</p>
        </div>
        <Button onClick={onOpen}>Показать план действий</Button>
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

function Benchmark({ visibility }: { visibility: number }) {
  return (
    <article className="benchmark panel">
      <div className="section-head">
        <div>
          <span className="section-label">Benchmark</span>
          <h2>Позиция относительно рынка</h2>
        </div>
        <span className="badge neutral">Предварительно</span>
      </div>
      {[
        ["Skinjestique", visibility],
        ["Среднее рынка", 61],
        ["Лидеры категории", 95],
      ].map(([name, value]) => (
        <div className="benchmark-row" key={String(name)}>
          <span>{name}</span>
          <div className="track">
            <i style={{ width: `${value}%` }} />
          </div>
          <strong>{Number(value).toFixed(0)}</strong>
        </div>
      ))}
    </article>
  );
}

function Trend({ visibility }: { visibility: number }) {
  const points = [
    Math.max(0, visibility - 12),
    Math.max(0, visibility - 6),
    visibility,
  ];
  const coords = points
    .map((value, i) => `${18 + i * 132},${150 - value}`)
    .join(" ");
  return (
    <article className="trend panel">
      <div className="section-head">
        <div>
          <span className="section-label">Динамика</span>
          <h2>AI Visibility растёт</h2>
        </div>
        <span className="delta good">↑ 8%</span>
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
        {["Июнь", "Июль", "Август"].map((month, i) => (
          <div key={month}>
            <span>{month}</span>
            <strong>{points[i].toFixed(0)}</strong>
          </div>
        ))}
      </div>
    </article>
  );
}

function ActionCenter({ citation }: { citation: number }) {
  const [sort, setSort] = useState<"impact" | "time">("impact");
  const [done, setDone] = useState<number[]>([]);
  const [open, setOpen] = useState<number>();
  const actions = [
    {
      title: "Добавить публикации в отраслевых СМИ",
      impact: 11,
      days: 15,
      difficulty: "Средняя",
    },
    {
      title: "Усилить страницы с экспертными доказательствами",
      impact: 7,
      days: 7,
      difficulty: "Низкая",
    },
    {
      title: "Разместить бренд в независимых каталогах",
      impact: 5,
      days: 10,
      difficulty: "Средняя",
    },
  ].sort((a, b) => (sort === "impact" ? b.impact - a.impact : a.days - b.days));
  return (
    <section className="action-center">
      <div className="section-head">
        <div>
          <span className="eyebrow">ACTION CENTER</span>
          <h2>Что делать дальше</h2>
          <p>
            Три действия способны поднять Visibility до{" "}
            {Math.min(99, Math.round(89 + (60 - citation) * 0.14))}.
          </p>
        </div>
        <label className="sort-control">
          Сортировка
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as "impact" | "time")}
          >
            <option value="impact">По эффекту</option>
            <option value="time">По сроку</option>
          </select>
        </label>
      </div>
      <div className="action-list">
        {actions.map((action, index) => (
          <article
            className={`action-item ${done.includes(index) ? "completed" : ""}`}
            key={action.title}
          >
            <button
              className="complete-action"
              aria-label={`Отметить «${action.title}» выполненным`}
              onClick={() =>
                setDone((items) =>
                  items.includes(index)
                    ? items.filter((x) => x !== index)
                    : [...items, index],
                )
              }
            >
              {done.includes(index) ? "✓" : ""}
            </button>
            <div>
              <span className="priority">Приоритет</span>
              <h3>{action.title}</h3>
              <div className="action-facts">
                <b className="good">+{action.impact} Visibility</b>
                <span>{action.days} дней</span>
                <span>{action.difficulty} сложность</span>
              </div>
              {open === index && (
                <p>
                  Соберите список релевантных площадок, подготовьте материал с
                  проверяемыми данными и обеспечьте корректную ссылку на
                  официальный ресурс бренда.
                </p>
              )}
            </div>
            <button
              className="expand-action"
              onClick={() => setOpen(open === index ? undefined : index)}
            >
              {open === index ? "Свернуть" : "Раскрыть"} ↓
            </button>
          </article>
        ))}
      </div>
      <div className="roadmap">
        <div>
          <span>Сегодня</span>
          <b>План утверждён</b>
        </div>
        <i>→</i>
        <div>
          <span>Через неделю</span>
          <b>Первые публикации</b>
        </div>
        <i>→</i>
        <div>
          <span>Через месяц</span>
          <b>Visibility 94</b>
        </div>
        <i>→</i>
        <div>
          <span>Через квартал</span>
          <b>Устойчивый рост</b>
        </div>
      </div>
    </section>
  );
}

function Wizard({
  onComplete,
  onCancel,
}: {
  onComplete: (result: ReportResult) => void;
  onCancel: () => void;
}) {
  const [step, setStep] = useState(1);
  const [brand, setBrand] = useState("Skinjestique");
  const [region, setRegion] = useState("GLOBAL");
  const [language, setLanguage] = useState("ru");
  const [profile, setProfile] = useState<WizardPayload["routing_profile"]>("BALANCED");
  const [review, setReview] = useState<WizardReview>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
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
      onComplete(await api.run(payload()));
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
        onClick={step === 1 ? onCancel : () => setStep(step - 1)}
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

function RecommendationCard({ citation }: { citation: number }) {
  return (
    <article className="action-card">
      <div className="action-top">
        <span className="priority">Высокий приоритет</span>
        <span>Источник роста</span>
      </div>
      <h3>Опубликовать экспертные материалы в отраслевых СМИ</h3>
      <p>
        Добавьте независимо проверяемые публикации и ссылки на бренд в
        авторитетных источниках.
      </p>
      <div className="action-meta">
        <div>
          <span>Ожидаемый эффект</span>
          <b className="good">
            +{Math.max(8, Math.round((60 - citation) * 0.68))} Citation
          </b>
        </div>
        <div>
          <span>Сложность</span>
          <b>Средняя</b>
        </div>
        <div>
          <span>Срок</span>
          <b>2 недели</b>
        </div>
      </div>
      <button className="secondary">Добавить в план</button>
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
  const visibility = valueOf(score, "visibility_score");
  const citation = valueOf(score, "citation_score");
  const strengths = metricMeta
    .filter(([, key]) => valueOf(score, key) >= 80)
    .map(([label]) => label);
  return (
    <main className="page report-page">
      <button className="back-link" onClick={onHome}>
        ← К обзору
      </button>
      <section className="report-hero">
        <div>
          <span className="eyebrow">
            EXECUTIVE REPORT · #{result.research.id}
          </span>
          <h1>{result.research.title}</h1>
          <p>
            За последний период AI Visibility выросла. Бренд уверенно
            присутствует в рекомендациях моделей; главное ограничение —
            недостаток авторитетных цитирований.
          </p>
        </div>
        <div className="report-score">
          <span>AI Visibility</span>
          <strong>{visibility.toFixed(1)}</strong>
          <em className="good">↑ 8%</em>
        </div>
      </section>
      <section className="score-strip">
        {[["Visibility", "visibility_score"], ...metricMeta].map(
          ([label, key]) => (
            <div key={key}>
              <span>{label}</span>
              <strong>{valueOf(score, key).toFixed(1)}</strong>
              <i className={tone(valueOf(score, key))} />
            </div>
          ),
        )}
      </section>
      <section className="report-layout">
        <article className="panel strengths">
          <span className="section-label">TOP STRENGTHS</span>
          <h2>Что уже работает</h2>
          {strengths.map((item) => (
            <div className="strength" key={item}>
              <span>★★★★★</span>
              <b>{item}</b>
              <small>Сильный сигнал бренда</small>
            </div>
          ))}
        </article>
        <article className="panel weakness">
          <span className="section-label">ГЛАВНОЕ ОГРАНИЧЕНИЕ</span>
          <h2>Citation</h2>
          <strong>{citation.toFixed(1)}</strong>
          <p>
            AI знает и рекомендует бренд, но недостаточно часто подтверждает
            ответы независимыми источниками.
          </p>
          <div className="track">
            <span className="watch" style={{ width: `${citation}%` }} />
          </div>
        </article>
        <article className="panel narrative">
          <span className="section-label">ЧТО ХОРОШО</span>
          <h2>Ключевые выводы</h2>
          <ul>
            <li>AI рекомендует бренд в целевых запросах</li>
            <li>Высокая узнаваемость названия</li>
            <li>Хорошее покрытие выбранных моделей</li>
            <li>Высокая уверенность в результатах</li>
          </ul>
        </article>
        <article className="panel sources">
          <span className="section-label">KNOWLEDGE SOURCES</span>
          <h2>Источники знаний</h2>
          <div className="source-number">{report.sources?.length ?? 0}</div>
          <p>источника обнаружено и связано с ответами моделей</p>
          <button className="text-action">Изучить источники →</button>
        </article>
      </section>
      <section className="visualization-grid">
        <ChartContainer title="Присутствие по моделям" caption="HEATMAP">
          <Heatmap
            values={[
              visibility,
              citation,
              valueOf(score, "coverage_score"),
              valueOf(score, "recommendation_score"),
            ]}
          />
        </ChartContainer>
        <ChartContainer title="Структура источников" caption="TREEMAP">
          <Treemap sources={report.sources?.length ?? 0} />
        </ChartContainer>
        <ChartContainer title="Knowledge Graph" caption="ENTITY NETWORK">
          <NetworkGraph
            brand={result.research.title.replace(/^AI Visibility:\s*/, "")}
          />
        </ChartContainer>
      </section>
      <section className="plan-section">
        <div className="section-head">
          <div>
            <span className="eyebrow">ПЛАН ДЕЙСТВИЙ</span>
            <h2>Как улучшить результат</h2>
          </div>
          <span>Горизонт · 3 недели</span>
        </div>
        <RecommendationCard citation={citation} />
        <div className="weeks">
          {[
            [
              "Неделя 1",
              "Подготовить экспертную тему и список отраслевых площадок",
            ],
            [
              "Неделя 2",
              "Опубликовать материал и обеспечить корректные ссылки",
            ],
            [
              "Неделя 3",
              "Повторить исследование и измерить изменение Citation",
            ],
          ].map(([week, text], i) => (
            <div key={week}>
              <span>{i + 1}</span>
              <div>
                <b>{week}</b>
                <p>{text}</p>
              </div>
            </div>
          ))}
        </div>
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
          <span>Время ответа</span>
          <b>{report.latency_ms ?? 0} ms</b>
        </div>
        <div>
          <span>Токены</span>
          <b>{report.token_usage ?? 0}</b>
        </div>
        <div>
          <span>Стоимость</span>
          <b>${report.cost ?? 0}</b>
        </div>
      </section>
    </main>
  );
}

function Assistant({
  open,
  onToggle,
}: {
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <aside className={`assistant ${open ? "open" : ""}`}>
      <button
        className="assistant-toggle"
        onClick={onToggle}
        aria-label="AI-помощник"
      >
        ✦
      </button>
      {open && (
        <div className="assistant-body">
          <div className="assistant-head">
            <span className="logo-mark small">AI</span>
            <div>
              <b>Помощник</b>
              <small>Онлайн</small>
            </div>
            <button className="icon-button" onClick={onToggle}>
              ×
            </button>
          </div>
          <div className="assistant-message">
            <span>AI</span>
            <p>
              <b>Что означает Citation?</b>
              <br />
              Это показатель того, насколько часто ответы AI подтверждаются
              независимыми и авторитетными источниками. Чем он выше, тем больше
              доверия к упоминаниям бренда.
            </p>
          </div>
          <button className="assistant-action">Исправить автоматически</button>
          <div className="assistant-input">
            <input placeholder="Задайте вопрос об отчёте…" />
            <button>↑</button>
          </div>
        </div>
      )}
    </aside>
  );
}

function App() {
  const [user, setUser] = useState("");
  const [screen, setScreen] = useState<Screen>(
    () => pathScreens[window.location.pathname] ?? "home",
  );
  const [report, setReport] = useState<ReportResult>();
  const [assistant, setAssistant] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authReady, setAuthReady] = useState(false);
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
      .then((profile) => { setUser(profile.display_name); setLoading(true); })
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
        const data = await api.finalReport(latest.id);
        setReport({
          research: latest,
          report_url: `/research/${latest.id}/final-report`,
          report: data,
        });
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [user, report]);
  const content = useMemo(
    () =>
      screen === "wizard" ? (
        <Wizard
          onCancel={() => navigate("home")}
          onComplete={(value) => {
            setReport(value);
            navigate("report");
          }}
        />
      ) : screen === "research" ? (
        <RecordsScreen key="research" kind="research" onNewResearch={() => navigate("wizard")} />
      ) : screen === "reports" ? (
        <RecordsScreen key="reports" kind="reports" onNewResearch={() => navigate("wizard")} />
      ) : screen === "recommendations" ? (
        <RecordsScreen key="recommendations" kind="recommendations" onNewResearch={() => navigate("wizard")} />
      ) : screen === "graph" ? (
        <RecordsScreen key="graph" kind="graph" onNewResearch={() => navigate("wizard")} />
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
      ) : screen === "analytics" ? (
        <ProductAnalyticsScreen />
      ) : screen === "notifications" ? (
        <NotificationsScreen />
      ) : screen === "organization" ? (
        <OrganizationScreen />
      ) : screen === "settings" ? (
        <SettingsScreen user={user} />
      ) : screen === "admin" ? (
        <AdminConsoleScreen />
      ) : screen === "onboarding" ? (
        <OnboardingScreen onResearch={() => navigate("wizard")} />
      ) : screen === "report" && report ? (
        <Report result={report} onHome={() => navigate("home")} />
      ) : loading ? (
        <DashboardSkeleton />
      ) : (
        <Dashboard
          report={report}
          onStart={() => navigate("wizard")}
          onOpen={() => navigate("report")}
        />
      ),
    [screen, report, loading, user, navigate],
  );
  if (!authReady) return <DashboardSkeleton />;
  if (!user)
    return (
      <Login
        onReady={(name) => {
          setLoading(true);
          setUser(name);
          navigate(pathScreens[window.location.pathname] ?? "home", true);
        }}
      />
    );
  return (
    <Shell
      user={user}
      active={screen}
      onNavigate={navigate}
      onLogout={() => {
        setUser("");
        setReport(undefined);
        navigate("home", true);
      }}
    >
      {content}
      <Assistant open={assistant} onToggle={() => setAssistant(!assistant)} />
    </Shell>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
