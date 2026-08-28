import { StrictMode, useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import {
  ApiClient,
  type ActionPlanItem,
  type AliceAutomationDashboard,
  type AliceLearningDashboard,
  type AuthProfile,
  type AdminAudit,
  type AdminFeedback,
  type AdminUser,
  type CompetitorDashboard,
  type CompetitorItem,
  type FeedbackItem,
  type GraphSnapshot,
  type GeoPlatform,
  type GeoSiteAudit,
  type EisPriorityResult,
  type PublicationInfluenceEstimate,
  type FrozenPromptSet,
  type ProductAnalyticsDashboard as AnalyticsDashboard,
  type NotificationItem,
  type OrganizationItem,
  type ProviderItem,
  type ProviderConnection,
  type RecommendationItem,
  type ReportCatalogItem,
  type ReportResult,
  type BrandProfile,
  type ResearchItem,
  type RouterHistoryItem,
  type RouterModel,
  type SimulationItem,
  type SystemProviderItem,
  type SocialDashboard,
  type TelegramConnection,
  type WorkspaceProjectItem,
  type YandexWebmasterHost,
  type YandexWebmasterStatus,
  type YandexIntelligence,
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
const ACTIVE_RESEARCH_KEY = "ai-ranking-active-research";

function researchBrand(item: ResearchItem | undefined) {
  if (!item) return "";
  return String(item.metadata?.brand ?? item.title.replace(/^AI Visibility:\s*/i, "")).trim();
}
const screenPaths: Record<Screen, string> = {
  home: "/",
  expert: "/expert-guide",
  onboarding: "/getting-started",
  research: "/research",
  wizard: "/research/new",
  reports: "/reports",
  report: "/reports/latest",
  recommendations: "/recommendations",
  graph: "/knowledge-graph",
  geo: "/geo-opportunities",
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

type Screen = "home" | "expert" | "research" | "wizard" | "reports" | "report" | "recommendations" | "graph" | "geo" | "competitors" | "history" | "providers" | "analytics" | "notifications" | "organization" | "settings" | "feedback" | "profile" | "admin" | "onboarding";
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
    sample_scope?: { query_count: number; response_count: number; successful_response_count: number; failed_response_count: number; provider_model_count: number; languages: string[]; regions: string[]; limitation: string };
  };
  query_catalog?: Array<{ id: string; cluster: string; intent: string; text: string; buyer_stage?: string; brand_mode?: string; rationale?: string }>;
  research_patterns?: {
    sample: { queries: number; responses: number; successful_responses: number; providers: string[]; models: string[] };
    query_matrix: Array<{ response_id: number; cluster: string; query: string; provider: string; model: string; mentioned: boolean; competitors: string[]; sources: string[] }>;
    deficit_queries: Array<{ response_id: number; cluster: string; query: string; provider: string; model: string; mentioned: boolean; competitors: string[]; sources: string[] }>;
    competitors: Array<{ name: string; response_count: number }>;
    source_patterns: Array<{ resource: string; response_count: number }>;
  };
  geo_opportunities?: Array<{ id: string; channel: string; resource: string; reason: string; deliverable: string; affected_metric: string; expected_effect_range: number[]; confidence: number; effort: string; estimated_days: number; verification: string; causality_notice: string }>;
  competitive_influence?: { version: string; causality_status: string; verification: string; competitors: Array<{ competitor: string; website_url: string; response_count: number; profile_confidence: number; evidence_urls: string[]; matched_products: Array<{ target_product: string; competitor_product: string; feature_similarity: number; target_price?: string | number; competitor_price?: string | number; currency?: string; target_evidence_url?: string; competitor_evidence_url?: string }> }>; source_influence: Array<{ resource: string; response_count: number; relationship: string; explanation: string }> };
  publication_learning?: { status: string; explanation: string; experiments: Array<{ id: number; publication_id: number; baseline_research_id: number; followup_research_id: number; evidence_grade: string; evidence_level: string; causality_status: string; metric_deltas: Record<string, number>; adjusted_metric_deltas: Record<string, number>; design_type: string; treatment_pairs: number; control_pairs: number; effect_method: string; sample_size: number }>; influence_estimates: Array<{ id: number; resource_domain: string; channel: string; content_type: string; metric: string; provider: string; model: string; sample_size: number; expected_delta: number; confidence_min: number; confidence_max: number; confidence_score: number; evidence_grade: string; evidence_level: string; controlled_experiments: number; effect_method: string }> };
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
  const primaryNav = [
    ["⌂", "Обзор", "home"], ["＋", "Новое исследование", "wizard"],
    ["▤", "Результаты", "reports"], ["✓", "План действий", "recommendations"],
    ["◇", "Конкуренты", "competitors"],
  ] as const;
  const expertNavSource = [
    ["?", "Как пользоваться", "expert"],
    ["◉", "Все исследования", "research"], ["↗", "История изменений", "history"],
    ["⌘", "Связи и источники", "graph"], ["◈", "Где публиковаться", "geo"],
    ["✦", "Подключения ИИ", "providers"], ["◫", "Аналитика продукта", "analytics"],
  ] as const;
  const workspaceNavSource = [
    ["♢", "Уведомления", "notifications"], ["◎", "Организация", "organization"],
    ["♙", "Профиль", "profile"], ["⚙", "Настройки", "settings"], ["◌", "Обратная связь", "feedback"],
    ["→", "Как начать", "onboarding"], ["▦", "Администрирование", "admin"],
  ] as const;
  const visible = (items: readonly (readonly [string, string, Screen])[]) =>
    items.filter(([, , target]) => isAdmin || (target !== "admin" && target !== "analytics"));
  const renderNav = (items: readonly (readonly [string, string, Screen])[]) => items.map(([icon, label, target]) => (
    <button key={target} className={active === target ? "active" : ""} onClick={() => onNavigate(target)}>
      <span>{icon}</span><span className="nav-label">{label}</span>
    </button>
  ));
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="wordmark" onClick={() => onNavigate("home")}>
          <span className="logo-mark small">AR</span>
          <span>AI Ranking OS</span>
        </button>
        <nav aria-label="Основная навигация">
          <span className="nav-section-label">Главное</span>
          {renderNav(primaryNav)}
          <details className="nav-group"><summary><span>⋯</span><span className="nav-label">Для экспертов</span></summary>{renderNav(visible(expertNavSource))}</details>
          <details className="nav-group"><summary><span>⚙</span><span className="nav-label">Рабочее пространство</span></summary>{renderNav(visible(workspaceNavSource))}</details>
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
        <nav className="mobile-nav" aria-label="Мобильная навигация">
          {primaryNav.slice(0, 4).map(([icon, label, target]) => (
            <button key={target} className={active === target ? "active" : ""} onClick={() => onNavigate(target)}><span>{icon}</span><small>{label === "Новое исследование" ? "Проверить" : label}</small></button>
          ))}
        </nav>
      </div>
    </div>
  );
}

function SettingsScreen({ user }: { user: string }) {
  const [tab, setTab] = useState(() => new URLSearchParams(window.location.search).get("tab") || "profile");
  const [settings, setSettings] = useState<Record<string, unknown>>({ language: "ru", region: "GLOBAL", theme: "dark", notifications: { email: true, in_app: true } });
  const [providers, setProviders] = useState<ProviderItem[]>([]);
  const [keys, setKeys] = useState<Array<{ id: number; name: string; prefix: string }>>([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [webmaster, setWebmaster] = useState<YandexWebmasterStatus | null>(null);
  const [webmasterHosts, setWebmasterHosts] = useState<YandexWebmasterHost[]>([]);
  const [webmasterBusy, setWebmasterBusy] = useState(false);
  useEffect(() => { Promise.all([api.workspace(), api.listProviders(), api.apiKeys()]).then(([workspace, providerItems, apiKeyItems]) => { setSettings((current) => ({ ...current, ...workspace.settings })); setProviders(providerItems); setKeys(apiKeyItems); }).catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки настроек")); }, []);
  const connectWebmaster = () => {
    setWebmasterBusy(true); setError("");
    api.authorizeYandexWebmaster().then(({ authorization_url }) => window.location.assign(authorization_url)).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Не удалось начать подключение");
      setWebmasterBusy(false);
    });
  };
  useEffect(() => { api.yandexWebmasterStatus().then((status) => {
    setWebmaster(status);
    if (status.connected) void api.yandexWebmasterHosts().then((hosts) => {
      setWebmasterHosts(hosts);
      if (!hosts.length) setError("OAuth подключён, но Яндекс Вебмастер не вернул ни одного сайта. Добавьте и подтвердите сайт в кабинете Вебмастера либо подключите другой Яндекс-аккаунт.");
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось получить сайты Яндекс Вебмастера"));
  }).catch(() => setWebmaster(null)); }, []);
  const tabs = [["profile", "Профиль"], ["security", "Безопасность"], ["api", "API Keys"], ["providers", "LLM Providers"], ["integrations", "Интеграции"], ["preferences", "Язык и регион"], ["notifications", "Уведомления"], ["theme", "Тема"], ["organization", "Организация"]];
  const set = (key: string, value: unknown) => { setSaved(false); setSettings((current) => ({ ...current, [key]: value })); };
  return <main className="analytics-page settings-page"><header className="analytics-hero"><div><span className="eyebrow">PREFERENCES</span><h1>Настройки</h1><p>Единый центр персональных и системных настроек.</p></div><button className="primary-action" onClick={() => api.updateWorkspace(settings).then(() => setSaved(true))}>{saved ? "Сохранено ✓" : "Сохранить"}</button></header>
    {error && <div className="error" role="alert">{error}</div>}
    <div className="settings-layout"><nav className="settings-nav">{tabs.map(([key, label]) => <button className={tab === key ? "active" : ""} onClick={() => setTab(key)} key={key}>{label}</button>)}</nav><section className="analytics-card settings-panel">
      {tab === "profile" && <><h2>Профиль</h2><label>Имя<input value={user} disabled /></label><p className="empty-state">Контактные данные управляются Authentication.</p></>}
      {tab === "security" && <><h2>Безопасность</h2><div className="setting-row"><span>JWT-сессии и refresh rotation</span><b>Активно</b></div><div className="setting-row"><span>Отзыв токенов при выходе</span><b>Активно</b></div></>}
      {tab === "api" && <><h2>API Keys</h2>{keys.length ? keys.map((key) => <div className="setting-row" key={key.id}><span>{key.name}</span><code>{key.prefix}••••</code></div>) : <p className="empty-state">API-ключи ещё не созданы.</p>}</>}
      {tab === "providers" && <><h2>LLM Providers</h2>{providers.length ? providers.map((provider) => <div className="setting-row" key={provider.id}><span>{provider.display_name}</span><b>{provider.availability}</b></div>) : <p className="empty-state">Провайдеры недоступны.</p>}</>}
      {tab === "integrations" && <><h2>Яндекс Вебмастер</h2><p>Подключите подтверждённые сайты и реальные поисковые запросы. Доступ выдаётся через Яндекс OAuth; пароль и OAuth-токен не отображаются и не передаются в браузер.</p>
        <div className="setting-row"><span>OAuth-доступ</span><Badge tone={webmaster?.connected ? "success" : "warning"}>{webmaster?.connected ? "ПОДКЛЮЧЁН" : "НЕ ПОДКЛЮЧЁН"}</Badge></div>
        {webmaster?.connected ? <><div className="setting-row"><span>Доступные сайты</span><b>{webmasterHosts.length || "НЕТ"}</b></div>{webmasterHosts.some((host) => host.verified) ? <label>Подтверждённый сайт<select value={webmaster.selected_host_id ?? ""} onChange={(event) => { const host = webmasterHosts.find((item) => item.host_id === event.target.value); if (host) void api.selectYandexWebmasterHost(host.host_id, host.unicode_host_url || host.ascii_host_url).then((status) => { setWebmaster(status); setError(""); }); }}><option value="">Выберите подтверждённый сайт</option>{webmasterHosts.filter((host) => host.verified).map((host) => <option key={host.host_id} value={host.host_id}>{host.unicode_host_url || host.ascii_host_url} · подтверждён</option>)}</select></label> : <div className="webmaster-empty"><h3>Почему список пуст</h3><p>OAuth работает, но подключённый Яндекс-аккаунт не вернул ни одного подтверждённого сайта. Приложение не может добавить сайт вместо владельца.</p><ol><li>Откройте Яндекс Вебмастер под тем же аккаунтом.</li><li>Добавьте сайт и подтвердите право владения.</li><li>Вернитесь сюда и нажмите «Обновить список».</li></ol><a href="https://webmaster.yandex.ru/sites/" target="_blank" rel="noreferrer">Открыть Яндекс Вебмастер ↗</a></div>}<div className="button-row"><button className="secondary" disabled={webmasterBusy} onClick={() => { setWebmasterBusy(true); api.yandexWebmasterHosts().then(setWebmasterHosts).catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось обновить сайты")).finally(() => setWebmasterBusy(false)); }}>Обновить список</button><button className="secondary" disabled={webmasterBusy} onClick={connectWebmaster}>Подключить другой аккаунт</button><button className="secondary" disabled={webmasterBusy} onClick={() => { setWebmasterBusy(true); api.disconnectYandexWebmaster().then(() => { setWebmaster({ connected: false, status: "NOT_CONFIGURED" }); setWebmasterHosts([]); setError(""); }).finally(() => setWebmasterBusy(false)); }}>Отключить</button></div></> : <button className="primary-action" disabled={webmasterBusy} onClick={connectWebmaster}>Подключить Яндекс Вебмастер</button>}
        <p className="empty-state">После выбора сайта система сможет использовать реальные запросы Яндекс Поиска при подготовке карты GEO-исследования. Данные «Видимость в Алисе AI» будут подключены только через официальный API или экспорт — без браузерного скрейпинга.</p></>}
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
  const [researches, setResearches] = useState<ResearchItem[]>([]);
  const [researchId, setResearchId] = useState<number>();
  const [query, setQuery] = useState("");
  const [nodeType, setNodeType] = useState("ALL");
  const [selected, setSelected] = useState<number>();
  const [error, setError] = useState("");
  useEffect(() => {
    api.listResearch().then((items) => {
      const completed = [...items]
        .filter((item) => item.status === "COMPLETED")
        .sort((left, right) => right.id - left.id);
      setResearches(completed);
      const savedId = Number(sessionStorage.getItem(ACTIVE_RESEARCH_KEY));
      const selectedId = completed.some((item) => item.id === savedId)
        ? savedId
        : completed[0]?.id;
      setResearchId(selectedId);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Исследования недоступны"));
  }, []);
  useEffect(() => {
    if (!researchId) return;
    let active = true;
    sessionStorage.setItem(ACTIVE_RESEARCH_KEY, String(researchId));
    api.graph(researchId)
      .then((snapshot) => { if (active) setGraph(snapshot); })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "Граф недоступен"); });
    return () => { active = false; };
  }, [researchId]);
  if (!researches.length) return <main className="analytics-page graph-page"><header className="analytics-hero"><div><span className="eyebrow">СВЯЗИ И ИСТОЧНИКИ</span><h1>Граф знаний</h1><p>Здесь появятся реальные связи выбранного бренда с продуктами, организациями и источниками.</p></div></header><div className="analytics-card empty-state"><h2>Граф появится после исследования</h2><p>Создайте и завершите исследование бренда. Система извлечёт сущности, источники и связи из реальных ответов ИИ.</p></div></main>;
  const selectedResearch = researches.find((item) => item.id === researchId);
  const selectedBrand = researchBrand(selectedResearch);
  const selector = <label className="research-selector">Бренд и исследование<select aria-label="Бренд для графа знаний" value={researchId} onChange={(event) => { setGraph(undefined); setSelected(undefined); setError(""); setResearchId(Number(event.target.value)); }}>{researches.map((item) => <option value={item.id} key={item.id}>{researchBrand(item)} · исследование #{item.id}</option>)}</select></label>;
  if (error) return <main className="analytics-page graph-page"><header className="analytics-hero"><div><span className="eyebrow">{selectedBrand || "ВЫБРАННЫЙ БРЕНД"}</span><h1>Граф знаний</h1><p>Для выбранного исследования граф не построен.</p></div>{selector}</header><div className="analytics-card empty-state" role="alert"><h2>Связи ещё не извлечены</h2><p>{error}</p><p>Выберите другое завершённое исследование или запустите новое — после обработки ответов граф будет создан автоматически.</p></div></main>;
  if (!graph) return <DashboardSkeleton />;
  const types = [...new Set(graph.nodes.map((node) => node.node_type))];
  const visible = graph.nodes.filter((node) => (nodeType === "ALL" || node.node_type === nodeType) && (!query || `${node.name} ${node.aliases.join(" ")}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())));
  const visibleIds = new Set(visible.map((node) => node.id));
  const edges = graph.edges.filter((edge) => visibleIds.has(edge.source_node_id) && visibleIds.has(edge.target_node_id));
  const positions = new Map(visible.map((node, index) => { const angle = index * Math.PI * 2 / Math.max(visible.length, 1) - Math.PI / 2; return [node.id, { x: 310 + Math.cos(angle) * 215, y: 230 + Math.sin(angle) * 165 }]; }));
  const selectedNode = graph.nodes.find((node) => node.id === selected);
  const connected = selected == null ? [] : graph.edges.filter((edge) => edge.source_node_id === selected || edge.target_node_id === selected);
  return <main className="analytics-page graph-page"><header className="analytics-hero"><div><span className="eyebrow">{selectedBrand} · СНИМОК #{graph.id} · v{graph.structure_version}</span><h1>Граф знаний</h1><p>Что ИИ связывает с брендом <strong>{selectedBrand}</strong> в исследовании #{researchId}. Линия означает зафиксированную связь в ответе ИИ, а не доказанное влияние.</p></div>{selector}</header>
    <section className="analytics-card graph-explainer"><div><b>{graph.node_count}</b><span>обнаруженных сущностей</span></div><div><b>{graph.edge_count}</b><span>подтверждённых связей</span></div><p><strong>Как читать:</strong> нажмите на круг, чтобы увидеть тип сущности, уверенность извлечения и связи. Если связь отсутствует, это означает, что в сохранённых ответах ИИ она не была обнаружена.</p></section>
    <section className="analytics-card graph-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск по имени или алиасу"/><select value={nodeType} onChange={(event) => setNodeType(event.target.value)}><option value="ALL">Все типы</option>{types.map((type) => <option key={type}>{type}</option>)}</select></section>
    {!visible.length ? <div className="analytics-card empty-state">Сущности по выбранным условиям не найдены.</div> : <section className="graph-real-layout"><article className="analytics-card"><svg viewBox="0 0 620 460" className="network" aria-label="Реальный граф знаний"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#607899"/></marker></defs>{edges.map((edge) => { const source = positions.get(edge.source_node_id); const target = positions.get(edge.target_node_id); if (!source || !target) return null; return <g key={edge.id}><line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#607899" markerEnd="url(#arrow)"/><title>{edge.edge_type} · уверенность {(edge.confidence * 100).toFixed(0)}%</title></g>; })}{visible.map((node) => { const point = positions.get(node.id)!; return <g key={node.id} className="graph-node" onClick={() => setSelected(node.id)}><circle cx={point.x} cy={point.y} r={selected === node.id ? 25 : 19} fill={selected === node.id ? "#3b82f6" : "#263d62"}/><text x={point.x} y={point.y + 34} textAnchor="middle" fill="#c8d4e6" fontSize="11">{node.name}</text><title>{node.node_type} · уверенность {(node.confidence * 100).toFixed(0)}%</title></g>; })}</svg>{!edges.length && <p className="empty-state">Связи пока не обнаружены. Показаны только реальные узлы снимка.</p>}</article><aside className="analytics-card graph-detail">{selectedNode ? <><span className="eyebrow">{selectedNode.node_type}</span><h2>{selectedNode.name}</h2><p>Уверенность {(selectedNode.confidence * 100).toFixed(1)}%</p><p>Алиасы: {selectedNode.aliases.join(", ") || "нет"}</p><h3>Связи ({connected.length})</h3>{connected.map((edge) => <div className="graph-edge-detail" key={edge.id}><div className="setting-row"><span>{edge.edge_type}</span><b>{(edge.confidence * 100).toFixed(0)}%</b></div><small>{Object.keys(edge.properties ?? {}).length ? `Доказательства: ${JSON.stringify(edge.properties)}` : "Контекст и источник связи не были записаны при построении графа."}</small></div>)}</> : <p className="empty-state">Выберите узел, чтобы увидеть уверенность, алиасы и связи.</p>}</aside></section>}
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
    graph: ["Граф знаний", "Реальные сущности и связи последнего снимка"],
    competitors: ["Конкуренты", "Конкуренты из проектов рабочего пространства"],
    history: ["История", "Хронология исследований от новых к старым"],
    feedback: ["Обратная связь", "Ваши обращения и их текущий статус"],
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
        const metricLabels: Record<string, string> = { mention_score: "Упоминания", recommendation_score: "Рекомендации бренда", citation_score: "Независимые источники", coverage_score: "Покрытие моделей", confidence_score: "Достоверность данных" };
        const thresholds: Record<string, number> = { mention_score: 60, recommendation_score: 60, citation_score: 50, coverage_score: 70 };
        const actions: Record<string, string> = {
          mention_score: "Расширить присутствие бренда по покупательским запросам",
          recommendation_score: "Усилить доказательства, отзывы и сигналы доверия",
          citation_score: "Получить публикации в независимых авторитетных источниках",
          coverage_score: "Проверить бренд в большем числе подключённых AI-моделей",
          confidence_score: "Собрать больше успешно обработанных ответов",
        };
        return (await api.recommendations(latest.id)).recommendations.map((item: RecommendationItem) => ({
          id: String(item.id),
          title: actions[item.metric] ?? "Улучшить измеряемый сигнал бренда",
          status: item.priority,
          detail: `${metricLabels[item.metric] ?? item.metric}: ${item.metric_value.toFixed(1)} из 100; целевой порог v1.0 — ${thresholds[item.metric] ?? "не задан"}. Разрыв: ${typeof thresholds[item.metric] === "number" ? Math.max(0, thresholds[item.metric] - item.metric_value).toFixed(1) : "—"} балла.`,
          meta: `Исследование #${latest.id} · ожидаемый эффект проверяется только повторным исследованием`,
        }));
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
  return <main className="analytics-page records-page"><header className="analytics-hero"><div><span className="eyebrow">РЕАЛЬНЫЕ ДАННЫЕ</span><h1>{titles[kind][0]}</h1><p>{titles[kind][1]}</p></div>{kind === "research" && <button className="primary-action" onClick={onNewResearch}>Новое исследование</button>}</header>
    {error ? <div className="error" role="alert">{error}</div> : loading ? <DashboardSkeleton /> : <section className="records-list">{records.length ? records.map((item) => <article className="analytics-card record-card" key={item.id}><div><small>{item.meta}</small><h2>{item.title}</h2><p>{item.detail}</p></div><Badge tone={item.status === "COMPLETED" || item.status === "ACTIVE" ? "success" : item.status === "FAILED" || item.status === "CRITICAL" ? "danger" : "warning"}>{item.status}</Badge></article>) : <div className="analytics-card empty-state">Данных пока нет. Они появятся после первого действия в этом разделе.</div>}</section>}
  </main>;
}

function RecommendationsScreen({ onNewResearch }: { onNewResearch: () => void }) {
  const [researches, setResearches] = useState<ResearchItem[]>([]);
  const [researchId, setResearchId] = useState<number>();
  const [report, setReport] = useState<ReportShape>();
  const [platforms, setPlatforms] = useState<GeoPlatform[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.listResearch(), api.geoPlatforms().catch(() => [])]).then(([items, rows]) => {
      const completed = [...items].filter((item) => item.status === "COMPLETED").sort((a, b) => b.id - a.id);
      setResearches(completed);
      setPlatforms(rows.filter((item) => item.active));
      const remembered = Number(sessionStorage.getItem(ACTIVE_RESEARCH_KEY));
      const selected = completed.some((item) => item.id === remembered) ? remembered : completed[0]?.id;
      setResearchId(selected);
      if (!selected) setLoading(false);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить исследования"));
  }, []);
  useEffect(() => {
    if (!researchId) return;
    sessionStorage.setItem(ACTIVE_RESEARCH_KEY, String(researchId));
    api.finalReport(researchId).then((value) => setReport(value as ReportShape)).catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить план действий")).finally(() => setLoading(false));
  }, [researchId]);
  const brand = researchBrand(researches.find((item) => item.id === researchId));
  const resourceEntries: Array<[string, { name: string; url: string; evidence: string }]> = [
    ...(report?.sources ?? []).filter((item) => item.url).map((item): [string, { name: string; url: string; evidence: string }] => [item.url!, { name: item.title || item.source || item.url!.replace(/^https?:\/\//, "").split("/")[0], url: item.url!, evidence: "Этот источник действительно встретился в ответе ИИ" }]),
    ...(report?.research_patterns?.source_patterns ?? []).filter((item) => /^https?:\/\//.test(item.resource)).map((item): [string, { name: string; url: string; evidence: string }] => [item.resource, { name: item.resource, url: item.resource, evidence: `Встретился в ${item.response_count} ответах исследуемой выборки` }]),
  ];
  const observedResources = [...new Map(resourceEntries).values()];
  const categoryPlatforms = platforms.filter((item) => item.category === "UNIVERSAL" || item.category === String(researches.find((row) => row.id === researchId)?.metadata?.research_profile ?? "UNIVERSAL"));
  return <main className="analytics-page recommendations-page">
    <header className="analytics-hero"><div><span className="eyebrow">ПЛАН УЛУЧШЕНИЙ</span><h1>Что поможет бренду чаще появляться в ответах ИИ</h1><p>Только действия, связанные с данными выбранного исследования. Прогнозы не являются гарантией попадания в выдачу.</p></div>{researches.length ? <label className="research-selector">Бренд и исследование<select value={researchId ?? ""} onChange={(event) => { setLoading(true); setError(""); setReport(undefined); setResearchId(Number(event.target.value)); }}>{researches.map((item) => <option value={item.id} key={item.id}>{researchBrand(item)} · исследование #{item.id}</option>)}</select></label> : null}</header>
    {error ? <div className="error" role="alert">{error}</div> : null}
    {!researches.length && !loading ? <section className="analytics-card empty-state"><h2>Сначала проведите исследование</h2><p>Без ответов моделей нельзя честно определить проблему и назвать площадки.</p><button className="primary-action" onClick={onNewResearch}>Новое исследование</button></section> : loading ? <DashboardSkeleton /> : <>
      <section className="analytics-card recommendation-summary"><div><span>Сейчас анализируется</span><strong>{brand}</strong><small>Исследование #{researchId}</small></div><div><span>Найдено действий</span><strong>{report?.geo_opportunities?.length ?? report?.recommendations?.length ?? 0}</strong><small>отсортированы по доказательности</small></div><div><span>Названо реальных источников</span><strong>{observedResources.length}</strong><small>{observedResources.length ? "из ответов моделей" : "источники не обнаружены"}</small></div></section>
      {(report?.geo_opportunities?.length ? report.geo_opportunities : []).map((item, index) => <article className="analytics-card recommendation-detail" key={item.id}>
        <header><div><span className="recommendation-number">{index + 1}</span><div><small>{metricNames[item.affected_metric] ?? item.affected_metric}</small><h2>{item.resource}</h2></div></div><Badge tone={item.confidence >= .7 ? "success" : item.confidence >= .45 ? "warning" : "neutral"}>Уверенность {Math.round(item.confidence * 100)}%</Badge></header>
        <div className="recommendation-logic"><div><b>Почему это предлагается</b><p>{item.reason}</p></div><div><b>Что именно подготовить</b><p>{item.deliverable}</p></div><div><b>Как проверить результат</b><p>{item.verification}</p></div></div>
        <div className="recommendation-meta"><span>Оценочный диапазон: <b>+{item.expected_effect_range[0]}…{item.expected_effect_range[1]}</b></span><span>Срок: <b>{item.estimated_days} дней</b></span><span>Сложность: <b>{({ LOW: "низкая", MEDIUM: "средняя", HIGH: "высокая" } as Record<string, string>)[item.effort] ?? item.effort}</b></span></div>
        {item.affected_metric === "citation_score" ? <div className="resource-proof"><h3>Где публиковаться</h3>{observedResources.length ? <><p>Эти ресурсы уже встречались в ответах ИИ по выбранному исследованию:</p>{observedResources.slice(0, 8).map((source) => <a href={source.url} target="_blank" rel="noreferrer" key={source.url}><b>{source.name}</b><small>{source.evidence}</small></a>)}</> : categoryPlatforms.length ? <><p>ИИ не назвали источники. Ниже — площадки из реестра, которые ещё нужно проверить перед размещением:</p>{categoryPlatforms.slice(0, 8).map((platform) => <a href={`https://${platform.domain}`} target="_blank" rel="noreferrer" key={platform.id}><b>{platform.name}</b><small>{platform.category} · {platform.domain} · не подтверждено как источник текущей выдачи</small></a>)}</> : <div className="honest-empty"><b>Конкретные издания пока нельзя назвать доказательно</b><p>В ответах этого исследования нет ссылок, а в реестре площадок нет проверенных кандидатов категории. Следующий корректный шаг — собрать источники конкурентов и повторить исследование с моделями, возвращающими ссылки.</p></div>}</div> : null}
        <p className="method-note">{item.causality_notice}</p>
      </article>)}
      {!report?.geo_opportunities?.length ? <section className="analytics-card empty-state"><h2>Доказательный план ещё не рассчитан</h2><p>Общие фразы вроде «улучшите контент» не показываются. Нужны обработанные ответы, карта запросов и источники.</p></section> : null}
    </>}
  </main>;
}

function CompetitorSocialPanel({ projectId, competitorId, competitorName }: { projectId: number; competitorId: number; competitorName: string }) {
  const [dashboard, setDashboard] = useState<SocialDashboard>();
  const [platform, setPlatform] = useState("TELEGRAM");
  const [profileUrl, setProfileUrl] = useState("");
  const [externalId, setExternalId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [telegram, setTelegram] = useState<TelegramConnection>();
  const [apiId, setApiId] = useState("");
  const [apiHash, setApiHash] = useState("");
  const [phone, setPhone] = useState("");
  const [telegramCode, setTelegramCode] = useState("");
  const [telegramPassword, setTelegramPassword] = useState("");
  const [telegramQuery, setTelegramQuery] = useState("");
  const [proxyProtocol, setProxyProtocol] = useState<"SOCKS5" | "HTTP" | "MTPROXY">("MTPROXY");
  const [proxyHost, setProxyHost] = useState("");
  const [proxyPort, setProxyPort] = useState("443");
  const [proxyUsername, setProxyUsername] = useState("");
  const [proxyPassword, setProxyPassword] = useState("");
  const [proxySecret, setProxySecret] = useState("");
  const autoDiscoveryStarted = useRef(false);
  const load = useCallback(async () => { const result = await api.competitorSocial(projectId, competitorId); setDashboard(result); return result; }, [projectId, competitorId]);
  useEffect(() => {
    let active = true;
    api.competitorSocial(projectId, competitorId).then((result) => {
      if (!active) return;
      setDashboard(result);
      if (!result.sources.length && !autoDiscoveryStarted.current) {
        autoDiscoveryStarted.current = true; setBusy(true);
        api.discoverCompetitorSocial(projectId, competitorId).then((discovered) => { if (active) setDashboard(discovered); }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "Автопоиск соцсетей недоступен"); }).finally(() => { if (active) setBusy(false); });
      }
    }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "Не удалось загрузить соцсети"); });
    return () => { active = false; };
  }, [projectId, competitorId]);
  useEffect(() => { api.telegramConnection().then(setTelegram).catch(() => setTelegram({ configured: false, status: "NOT_CONFIGURED", proxy_configured: false })); }, []);
  const add = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await api.addCompetitorSocial(projectId, competitorId, { platform, profile_url: profileUrl.trim(), external_id: externalId.trim(), access_token: accessToken.trim() || undefined });
      setProfileUrl(""); setExternalId(""); setAccessToken(""); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось подключить канал"); }
    finally { setBusy(false); }
  };
  const discover = async () => { setBusy(true); setError(""); try { setDashboard(await api.discoverCompetitorSocial(projectId, competitorId)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Автопоиск соцсетей недоступен"); } finally { setBusy(false); } };
  const sendTelegramCode = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(""); try { setTelegram(await api.telegramSendCode({ api_id: Number(apiId), api_hash: apiHash, phone_number: phone })); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось запросить код Telegram"); } finally { setApiHash(""); setBusy(false); } };
  const verifyTelegram = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(""); try { setTelegram(await api.telegramVerify({ code: telegramCode, password: telegramPassword || undefined })); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось подтвердить Telegram"); } finally { setTelegramCode(""); setTelegramPassword(""); setBusy(false); } };
  const searchTelegram = async () => { setBusy(true); setError(""); try { setDashboard(await api.searchCompetitorTelegram(projectId, competitorId, telegramQuery)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Поиск Telegram не выполнен"); } finally { setBusy(false); } };
  const saveTelegramProxy = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(""); try { setTelegram(await api.telegramSetProxy({ protocol: proxyProtocol, host: proxyHost.trim(), port: Number(proxyPort), username: proxyUsername.trim() || undefined, password: proxyPassword || undefined, secret: proxySecret.trim() || undefined })); setProxyHost(""); setProxyUsername(""); setProxyPassword(""); setProxySecret(""); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось подключить прокси"); } finally { setBusy(false); } };
  const clearTelegramProxy = async () => { setBusy(true); setError(""); try { setTelegram(await api.telegramClearProxy()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось отключить SOCKS5-прокси"); } finally { setBusy(false); } };
  const deleteSource = async (sourceId: number) => { if (!window.confirm("Удалить источник и все найденные в нём публикации?")) return; setBusy(true); setError(""); try { await api.deleteCompetitorSocial(projectId, competitorId, sourceId); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось удалить источник"); } finally { setBusy(false); } };
  const deletePost = async (sourceId: number, postId: number) => { if (!window.confirm("Удалить эту публикацию из отчёта?")) return; setBusy(true); setError(""); try { await api.deleteCompetitorSocialPost(projectId, competitorId, sourceId, postId); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось удалить публикацию"); } finally { setBusy(false); } };
  const createLinkedReport = () => {
    if (!dashboard) return;
    const escape = (value: unknown) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
    const rows = dashboard.sources.flatMap((source) => source.posts.map((post) => `<tr><td>${escape(source.platform)}</td><td><a href="${escape(post.url)}">${escape(post.title || post.content.slice(0, 120) || "Публикация")}</a></td><td>${escape(new Date(post.published_at).toLocaleDateString("ru-RU"))}</td><td>${escape(post.views ?? "нет данных")}</td><td>${escape(post.likes ?? "нет данных")}</td><td>${escape(post.significance_score.toFixed(0))}</td></tr>`)).join("");
    const html = `<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Отчёт — ${escape(competitorName)}</title><style>body{font:15px Arial,sans-serif;color:#172033;max-width:1100px;margin:40px auto;padding:0 24px}h1{font-size:32px}p{color:#526078}table{width:100%;border-collapse:collapse;margin-top:24px}th,td{padding:11px;border:1px solid #d9e0ea;text-align:left;vertical-align:top}th{background:#eef4fb}a{color:#1457b8}small{display:block;margin-top:28px;color:#6b7280}@media print{body{margin:0}.no-print{display:none}}</style></head><body><button class="no-print" onclick="window.print()">Печать / сохранить PDF</button><h1>Упоминания: ${escape(competitorName)}</h1><p>Сформировано ${escape(new Date().toLocaleString("ru-RU"))}. Источников: ${dashboard.sources.length}. Публикаций: ${dashboard.total_posts}.</p><table><thead><tr><th>Площадка</th><th>Публикация и ссылка</th><th>Дата</th><th>Просмотры</th><th>Реакции</th><th>Значимость</th></tr></thead><tbody>${rows || '<tr><td colspan="6">Публикации не найдены.</td></tr>'}</tbody></table><small>${escape(dashboard.limitation)}</small></body></html>`;
    const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
    const reportWindow = window.open(url, "_blank", "noopener,noreferrer");
    if (!reportWindow) setError("Браузер заблокировал окно отчёта. Разрешите всплывающие окна для сайта.");
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  };
  return <details className="competitor-social"><summary>Соцсети и ежедневные публикации · {dashboard?.total_posts ?? 0}</summary>
    <section className="telegram-connection"><div className="telegram-connection__header"><div><span className="eyebrow">ПОИСК В ПУБЛИКАЦИЯХ</span><h3>Telegram</h3><p>Подключите служебный аккаунт один раз. API Hash, номер, сессия и 2FA не отображаются и не записываются в логи.</p></div><Badge tone={telegram?.configured ? "success" : telegram?.status === "PENDING_CODE" ? "warning" : "neutral"}>{telegram?.configured ? "ПОДКЛЮЧЕНО" : telegram?.status === "PENDING_CODE" ? "ОЖИДАЕТ КОД" : "НЕ ПОДКЛЮЧЕНО"}</Badge></div>
      {!telegram?.configured && telegram?.status !== "PENDING_CODE" ? <form className="telegram-connect-form" onSubmit={sendTelegramCode}><input inputMode="numeric" aria-label="Telegram API ID" placeholder="API ID" value={apiId} onChange={(event) => setApiId(event.target.value.replace(/\D/g, ""))} required /><input type="password" autoComplete="off" aria-label="Telegram API Hash" placeholder="API Hash" value={apiHash} onChange={(event) => setApiHash(event.target.value)} required /><input type="tel" aria-label="Номер Telegram" placeholder="+79991234567" value={phone} onChange={(event) => setPhone(event.target.value)} required /><button className="secondary" disabled={busy}>Получить код</button></form> : null}
      {!telegram?.configured && telegram?.status === "PENDING_CODE" ? <form className="telegram-connect-form" onSubmit={verifyTelegram}><p>Код отправлен на {telegram.phone_hint}. Введите его и пароль 2FA, если он включён.</p><input inputMode="numeric" aria-label="Код Telegram" placeholder="Код из Telegram" value={telegramCode} onChange={(event) => setTelegramCode(event.target.value.replace(/\D/g, ""))} required /><input type="password" autoComplete="one-time-code" aria-label="Пароль 2FA Telegram" placeholder="Пароль 2FA — если требуется" value={telegramPassword} onChange={(event) => setTelegramPassword(event.target.value)} /><button className="secondary" disabled={busy}>Подтвердить</button></form> : null}
      {telegram?.configured ? <form className="telegram-proxy-form" onSubmit={saveTelegramProxy}><div className="telegram-proxy-form__title"><b>Прокси для Telegram</b><Badge tone={telegram.proxy_configured ? "success" : "warning"}>{telegram.proxy_configured ? "АКТИВЕН" : "НЕ НАСТРОЕН"}</Badge></div><select aria-label="Тип прокси" value={proxyProtocol} onChange={(event) => { const protocol = event.target.value as "SOCKS5" | "HTTP" | "MTPROXY"; setProxyProtocol(protocol); setProxyPort(protocol === "HTTP" ? "80" : protocol === "MTPROXY" ? "443" : "1080"); }}><option value="MTPROXY">Telegram MTProxy — рекомендуется</option><option value="HTTP">HTTP — Webshare</option><option value="SOCKS5">SOCKS5</option></select><input aria-label="Адрес прокси" placeholder="Сервер или IP" value={proxyHost} onChange={(event) => setProxyHost(event.target.value)} required /><input inputMode="numeric" aria-label="Порт прокси" placeholder="Порт" value={proxyPort} onChange={(event) => setProxyPort(event.target.value.replace(/\D/g, ""))} required />{proxyProtocol === "MTPROXY" ? <input type="password" autoComplete="off" aria-label="Secret MTProxy" placeholder="Secret из ссылки MTProxy" value={proxySecret} onChange={(event) => setProxySecret(event.target.value)} required /> : <><input aria-label="Логин прокси" placeholder="Логин — если требуется" value={proxyUsername} onChange={(event) => setProxyUsername(event.target.value)} /><input type="password" autoComplete="off" aria-label="Пароль прокси" placeholder="Пароль — если требуется" value={proxyPassword} onChange={(event) => setProxyPassword(event.target.value)} /></>}<button className="secondary" disabled={busy}>{busy ? "Проверяем подключение…" : "Проверить и подключить"}</button>{telegram.proxy_configured ? <button type="button" className="ghost" onClick={clearTelegramProxy} disabled={busy}>Отключить прокси</button> : null}<small>{proxyProtocol === "MTPROXY" ? "Перенесите server, port и secret из ссылки tg://proxy или t.me/proxy. Secret хранится зашифрованным." : "Для Webshare система автоматически проверит HTTP и SOCKS5 и сохранит рабочий вариант."}</small></form> : null}
      {telegram?.configured ? <div className="telegram-search"><input aria-label="Поиск Telegram" placeholder="Оставьте пустым для поиска по бренду и алиасам" value={telegramQuery} onChange={(event) => setTelegramQuery(event.target.value)} /><button className="secondary" type="button" onClick={searchTelegram} disabled={busy}>{busy ? "Ищем…" : "Найти упоминания"}</button><small>Глобальный поиск по публикациям всех публичных каналов, включая каналы вне ваших подписок. Приватные каналы недоступны.</small></div> : null}
      {telegram?.last_error ? <p className="social-error">{telegram.last_error}</p> : null}
    </section>
    <div className="social-discovery"><div><b>{busy ? "Ищем профили и публикации…" : "Автоматический поиск по бренду"}</b><p>Система находит официальные соцсети на подтверждённом сайте конкурента, исключает дубли и ежедневно читает новые публичные публикации.</p></div><div className="social-actions"><button className="secondary" onClick={discover} disabled={busy}>{busy ? "Поиск…" : "Найти автоматически"}</button><button className="secondary" type="button" onClick={createLinkedReport} disabled={!dashboard}>Отчёт со ссылками</button></div></div>
    <p>Telegram ищет упоминания во всём глобальном индексе публичных каналов после подключения MTProto. Для данных VK/Instagram нужны их официальные API-доступы; приложение не имитирует их работу.</p>
    {error ? <div className="error" role="alert">{error}</div> : null}
    <form onSubmit={add} className="social-source-form"><select aria-label="Социальная сеть" value={platform} onChange={(event) => setPlatform(event.target.value)}><option value="TELEGRAM">Telegram</option><option value="YOUTUBE">YouTube</option><option value="VK">VK</option><option value="INSTAGRAM">Instagram</option></select><input aria-label="URL профиля" type="url" placeholder="https://..." value={profileUrl} onChange={(event) => setProfileUrl(event.target.value)} required /><input aria-label="Идентификатор канала" placeholder={platform === "YOUTUBE" ? "Channel ID" : "username / profile ID"} value={externalId} onChange={(event) => setExternalId(event.target.value)} required />{["VK", "INSTAGRAM"].includes(platform) ? <input aria-label="API-токен соцсети" type="password" placeholder="Официальный API-токен" value={accessToken} onChange={(event) => setAccessToken(event.target.value)} required /> : null}<button className="secondary" disabled={busy}>{busy ? "Подключаем…" : "Добавить канал"}</button></form>
    {dashboard?.sources.length ? <div className="social-source-list">{dashboard.sources.map((source) => <article key={source.id}><header><div><b>{source.platform}</b><a href={source.profile_url} target="_blank" rel="noreferrer">{source.external_id}</a></div><div className="social-actions"><Badge tone={source.status === "CONNECTED" ? "success" : source.status === "ERROR" ? "danger" : "warning"}>{source.status}</Badge><button className="danger-link" type="button" onClick={() => deleteSource(source.id)} disabled={busy}>Удалить источник</button></div></header>{source.last_error ? <p className="social-error">{source.last_error}</p> : null}<small>Последняя проверка: {source.last_scanned_at ? new Date(source.last_scanned_at).toLocaleString("ru-RU") : "ещё не выполнялась"}</small>{source.posts.map((post) => <div className="social-post" key={post.id}><div><a href={post.url} target="_blank" rel="noreferrer">{post.title || post.content.slice(0, 90) || "Публикация"}</a><small>{new Date(post.published_at).toLocaleDateString("ru-RU")} · просмотры {post.views ?? "нет данных"} · реакции {post.likes ?? "нет данных"}</small></div><div className="social-post__actions"><strong>{post.significance_score.toFixed(0)}<span>значимость</span></strong><button className="danger-link" type="button" onClick={() => deletePost(source.id, post.id)} disabled={busy}>Удалить</button></div></div>)}</article>)}</div> : <p className="empty-state">Каналы конкурента ещё не подключены.</p>}
    {dashboard ? <p className="method-note">{dashboard.limitation}</p> : null}
  </details>;
}

function CompetitorsScreen() {
  const [projects, setProjects] = useState<WorkspaceProjectItem[]>([]);
  const [projectId, setProjectId] = useState<number>();
  const [dashboard, setDashboard] = useState<CompetitorDashboard>();
  const [name, setName] = useState("");
  const [projectName, setProjectName] = useState("");
  const [domain, setDomain] = useState("");
  const [aliases, setAliases] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [showNewProject, setShowNewProject] = useState(false);
  const [error, setError] = useState("");
  const dashboardRequest = useRef(0);
  const projectsRequest = useRef(0);

  const loadDashboard = useCallback(async (id: number, refresh = false) => {
    const requestNumber = ++dashboardRequest.current;
    setLoading(true);
    setError("");
    try {
      const result = refresh
        ? await api.refreshCompetitorDashboard(id)
        : await api.competitorDashboard(id);
      if (requestNumber === dashboardRequest.current) setDashboard(result);
    } catch (reason) {
      if (requestNumber === dashboardRequest.current) {
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить конкурентов");
      }
    } finally {
      if (requestNumber === dashboardRequest.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const requestNumber = ++projectsRequest.current;
    api.workspaceProjects()
      .then((items) => {
        if (requestNumber !== projectsRequest.current) return;
        setProjects(items);
        setProjectId((current) => current ?? items[0]?.id);
        if (!items.length) setLoading(false);
      })
      .catch((reason) => {
        if (requestNumber !== projectsRequest.current) return;
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить проекты");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!projectId) return undefined;
    let active = true;
    const requestNumber = ++dashboardRequest.current;
    api.competitorDashboard(projectId)
      .then((result) => {
        if (active && requestNumber === dashboardRequest.current) setDashboard(result);
      })
      .catch((reason) => {
        if (active && requestNumber === dashboardRequest.current) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить конкурентов");
        }
      })
      .finally(() => {
        if (active && requestNumber === dashboardRequest.current) setLoading(false);
      });
    return () => { active = false; };
  }, [projectId]);

  const addCompetitor = async (event: FormEvent) => {
    event.preventDefault();
    if (!projectId || !name.trim()) return;
    const requestNumber = ++dashboardRequest.current;
    setSaving(true);
    setLoading(true);
    setError("");
    try {
      await api.createProjectCompetitor(projectId, {
        name: name.trim(),
        domains: domain.trim() ? [domain.trim()] : [],
        brands: aliases.split(",").map((value) => value.trim()).filter(Boolean),
      });
      setName("");
      setDomain("");
      setAliases("");
      const refreshed = await api.refreshCompetitorDashboard(projectId);
      if (requestNumber === dashboardRequest.current) setDashboard(refreshed);
    } catch (reason) {
      if (requestNumber === dashboardRequest.current) {
        setError(reason instanceof Error ? reason.message : "Не удалось добавить конкурента");
      }
    } finally {
      if (requestNumber === dashboardRequest.current) setLoading(false);
      setSaving(false);
    }
  };

  const createProject = async (event: FormEvent) => {
    event.preventDefault();
    if (!projectName.trim()) return;
    ++projectsRequest.current;
    setCreatingProject(true);
    setError("");
    try {
      const project = await api.createWorkspaceProject({ name: projectName.trim() });
      setProjects((current) => [...current, project]);
      setProjectId(project.id);
      setProjectName("");
      setShowNewProject(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось создать проект");
    } finally {
      setCreatingProject(false);
    }
  };

  const removeCompetitor = async (competitor: CompetitorItem | { competitor_id: number }) => {
    if (!projectId || !window.confirm("Удалить конкурента и его настройки наблюдения?")) return;
    await api.deleteProjectCompetitor(projectId, "id" in competitor ? competitor.id : competitor.competitor_id);
    await loadDashboard(projectId);
  };

  const toggleMonitoring = async () => {
    if (!projectId || !dashboard) return;
    setSaving(true);
    setError("");
    try {
      setDashboard(await api.setCompetitorDailyMonitoring(projectId, !dashboard.monitoring_enabled));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось изменить расписание");
    } finally {
      setSaving(false);
    }
  };

  return <main className="analytics-page competitor-page">
    <header className="analytics-hero"><div><span className="eyebrow">КОНКУРЕНТНАЯ РАЗВЕДКА</span><h1>Конкуренты</h1><p>Ежедневно отслеживайте видимость конкурентов и источники, которые встречаются рядом с их рекомендациями.</p></div>
      {projects.length > 0 && <div className="brand-switcher"><label>Какой бренд анализируем<select value={projectId ?? ""} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label><button className="secondary" onClick={() => setShowNewProject((value) => !value)}>+ Добавить другой бренд</button></div>}
    </header>
    {error && <div className="error" role="alert">{error}</div>}
    {projects.length > 0 && showNewProject ? <section className="analytics-card competitor-first-project compact-project"><div><span className="eyebrow">НОВЫЙ БРЕНД</span><h2>Создать отдельное наблюдение</h2><p>Конкуренты и результаты разных брендов не будут смешиваться.</p></div><form onSubmit={createProject}><label htmlFor="competitor-add-project-name">Название бренда</label><div><input id="competitor-add-project-name" value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Например, Skillbox" required autoFocus /><button className="primary-action" disabled={creatingProject}>{creatingProject ? "Создаём…" : "Создать бренд"}</button></div></form></section> : null}
    {!projects.length ? <section className="analytics-card competitor-first-project"><div><span className="eyebrow">ПЕРВЫЙ ШАГ</span><h2>Создайте проект для вашего бренда</h2><p>Проект объединяет ваш бренд, исследования и конкурентов. Например: «Skinjestique».</p></div><form onSubmit={createProject}><label htmlFor="competitor-project-name">Название проекта</label><div><input id="competitor-project-name" value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Название вашего бренда" required autoFocus /><button className="primary-action" disabled={creatingProject}>{creatingProject ? "Создаём…" : "Создать и продолжить"}</button></div></form></section> : <>
      <section className="competitor-controls">
        <form className="analytics-card competitor-form" onSubmit={addCompetitor}><div><span className="eyebrow">НОВЫЙ КОНКУРЕНТ</span><h2>Добавить в наблюдение</h2></div><label>Название<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Например, Librederm" required /></label><label>Сайт<input value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="librederm.ru" /></label><label>Другие названия<input value={aliases} onChange={(event) => setAliases(event.target.value)} placeholder="Алиасы через запятую" /></label><button className="primary-action" disabled={saving}>{saving ? "Сохраняем…" : "Добавить конкурента"}</button></form>
        <article className="analytics-card monitoring-card"><span className="eyebrow">ЕЖЕДНЕВНЫЙ КОНТРОЛЬ</span><h2>{dashboard?.monitoring_enabled ? "Мониторинг включён" : "Мониторинг выключен"}</h2><p>{dashboard?.monitoring_enabled ? `Следующий запуск: ${dashboard.next_run_at ? new Date(dashboard.next_run_at).toLocaleString("ru-RU") : "рассчитывается"}` : "Используется последнее завершённое исследование проекта и те же подключённые модели."}</p><button className={dashboard?.monitoring_enabled ? "secondary" : "primary-action"} onClick={toggleMonitoring} disabled={saving || !dashboard}>{dashboard?.monitoring_enabled ? "Выключить" : "Включить ежедневно"}</button><button className="secondary" onClick={() => projectId && loadDashboard(projectId, true)} disabled={loading}>Пересчитать по реальным данным</button></article>
      </section>
      {loading ? <DashboardSkeleton /> : dashboard?.competitors.length ? <section className="competitor-stack">{dashboard.competitors.map((competitor) => {
        const latest = competitor.snapshots.at(-1);
        return <article className="analytics-card competitor-analysis" key={competitor.competitor_id}><header><div><small>{competitor.domains.join(", ") || "Сайт не указан"}</small><h2>{competitor.name}</h2></div><div className="competitor-score"><strong>{competitor.latest_visibility_score?.toFixed(1) ?? "—"}</strong><span>наблюдаемая видимость</span>{competitor.visibility_delta != null && <b className={competitor.visibility_delta >= 0 ? "up" : "down"}>{competitor.visibility_delta >= 0 ? "+" : ""}{competitor.visibility_delta.toFixed(1)}</b>}</div><button className="danger-link" onClick={() => removeCompetitor(competitor)}>Удалить</button></header>
          <div className="competitor-metrics"><div><span>Ответы</span><b>{latest?.response_count ?? 0}</b></div><div><span>Упоминания</span><b>{latest?.mention_count ?? 0}</b></div><div><span>Рекомендации</span><b>{latest?.recommendation_count ?? 0}</b></div><div><span>Источники</span><b>{latest?.source_count ?? 0}</b></div></div>
          <div className="competitor-trend"><h3>Динамика по дням</h3>{competitor.snapshots.length ? <div className="trend-bars">{competitor.snapshots.slice(-14).map((snapshot) => <div key={snapshot.snapshot_date} title={`${snapshot.snapshot_date}: ${snapshot.observed_visibility_score}`}><i style={{ height: `${Math.max(snapshot.observed_visibility_score, 3)}%` }} /><span>{new Date(snapshot.snapshot_date).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" })}</span></div>)}</div> : <p className="empty-state">Снимки появятся после завершённого исследования проекта.</p>}</div>
          <div className="publication-list"><h3>Публикации и площадки</h3>{competitor.publications.length ? competitor.publications.map((publication) => <div className="publication-row" key={publication.url}><div><a href={publication.url} target="_blank" rel="noreferrer">{publication.title || publication.domain}</a><small>{publication.domain} · {publication.explanation}</small></div><div><strong>{publication.significance_score.toFixed(0)}</strong><span>{publication.significance_label} связь</span></div></div>) : <p className="empty-state">В ответах моделей пока не найдено источников, связанных с этим конкурентом. Это честное отсутствие данных, а не нулевая оценка влияния.</p>}</div>
          <CompetitorSocialPanel projectId={dashboard.project_id} competitorId={competitor.competitor_id} competitorName={competitor.name} />
        </article>;
      })}<p className="method-note">{dashboard.limitation}</p></section> : <section className="analytics-card empty-state"><h2>Конкурентов пока нет</h2><p>Добавьте бренд выше. После исследования система найдёт его упоминания, рекомендации и связанные источники.</p></section>}
    </>}
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

function ExpertGuideScreen({ onNavigate }: { onNavigate: (screen: Screen) => void }) {
  const tools = [
    { icon: "▤", title: "Разобраться в оценке", text: "Посмотрите, из каких ответов, упоминаний и источников сложилась видимость бренда.", action: "Открыть результаты", target: "reports" as Screen },
    { icon: "◈", title: "Понять, где публиковаться", text: "Сравните площадки по найденным доказательствам и получите приоритеты для размещений.", action: "Открыть площадки", target: "geo" as Screen },
    { icon: "◇", title: "Понять успех конкурентов", text: "Узнайте, где конкурентов упоминают, какие публикации совпадают с ростом их видимости.", action: "Открыть конкурентов", target: "competitors" as Screen },
    { icon: "⌘", title: "Проверить связи и источники", text: "Граф показывает реальные сущности, сайты и связи, найденные в ответах моделей.", action: "Открыть связи", target: "graph" as Screen },
    { icon: "↗", title: "Увидеть изменения", text: "Сравните повторные исследования и проверьте, дали ли выполненные действия результат.", action: "Открыть историю", target: "history" as Screen },
    { icon: "✦", title: "Подключить модели", text: "Проверьте доступность своих API-подключений. Исследования используют только реально подключённые модели.", action: "Открыть подключения", target: "providers" as Screen },
  ];
  return <main className="analytics-page expert-guide-page">
    <header className="analytics-hero"><div><span className="eyebrow">ПУТЕВОДИТЕЛЬ</span><h1>Инструменты для глубокого анализа</h1><p>Не нужно изучать всю платформу. Выберите задачу — мы покажем только нужный инструмент и ожидаемый результат.</p></div><button className="primary-action" onClick={() => onNavigate("wizard")}>Начать исследование</button></header>
    <section className="expert-route analytics-card"><div><span>1</span><b>Проведите исследование</b><small>Одинаковый набор запросов</small></div><i>→</i><div><span>2</span><b>Изучите доказательства</b><small>Ответы, источники, конкуренты</small></div><i>→</i><div><span>3</span><b>Выполните план</b><small>Публикации и улучшения</small></div><i>→</i><div><span>4</span><b>Повторите проверку</b><small>Подтвердите изменение</small></div></section>
    <section className="expert-tool-grid">{tools.map((tool) => <article className="analytics-card expert-tool" key={tool.title}><span className="expert-tool-icon">{tool.icon}</span><div><h2>{tool.title}</h2><p>{tool.text}</p></div><button onClick={() => onNavigate(tool.target)}>{tool.action} →</button></article>)}</section>
    <section className="analytics-card expert-language"><div><span className="eyebrow">БЕЗ ТЕХНИЧЕСКИХ ТЕРМИНОВ</span><h2>Как читать данные</h2></div><dl><div><dt>Видимость</dt><dd>Как часто и насколько заметно модели называют и рекомендуют бренд.</dd></div><div><dt>Цитирование</dt><dd>Есть ли в ответах внешние ссылки, подтверждающие информацию о бренде.</dd></div><div><dt>Влияние площадки</dt><dd>Наблюдаемая связь между публикациями на ресурсе и изменением выдачи. Не гарантия результата.</dd></div><div><dt>Граф знаний</dt><dd>Карта брендов, продуктов, людей, сайтов и найденных между ними связей.</dd></div></dl></section>
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
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [providerHint, setProviderHint] = useState("");
  const [folderId, setFolderId] = useState("");
  const [showHint, setShowHint] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const reloadConnections = () => api.providerConnections().then(setConnections);
  useEffect(() => {
    Promise.all([api.listProviders(), api.routerStatus(), api.systemProviders(), api.routerHistory(), api.listResearch(), api.providerConnections()])
      .then(async ([items, status, system, routerHistory, research, connectionItems]) => {
        setProviders(items); setCosts(status.costs); setRuntime(system.providers); setHistory(routerHistory.items);
        setConnections(connectionItems);
        const latest = [...research].sort((a, b) => b.id - a.id)[0];
        if (latest) {
          const report = await api.finalReport(latest.id) as ReportShape;
          setProviderStats((report.provider_statistics ?? {}) as Record<string, Record<string, number>>);
        }
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Ошибка загрузки"));
  }, []);
  const connect = async (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setNotice(""); setConnecting(true);
    try {
      const connection = await api.connectProvider(apiKey.trim(), providerHint, folderId.trim());
      setApiKey(""); setProviderHint(""); setFolderId(""); setShowHint(false);
      setNotice(`${connection.display_name} подключён и проверен. Платные модели отключены.`);
      await reloadConnections();
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Не удалось подключить API";
      setError(message); if (message.includes("неоднозначен")) setShowHint(true);
    } finally { setConnecting(false); }
  };
  const disconnect = async (connection: ProviderConnection) => {
    setError(""); setNotice("");
    try { await api.disconnectProvider(connection.id); await reloadConnections(); setNotice(`${connection.display_name} отключён.`); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось отключить API"); }
  };
  const available = providers.filter((item) => item.availability === "READY").length;
  return (
    <main className="page providers-page">
      <div className="page-heading">
        <div><span className="eyebrow">ИНТЕЛЛЕКТУАЛЬНАЯ МАРШРУТИЗАЦИЯ</span><h1>Провайдеры ИИ</h1>
          <p>Модели, политики, маршрутизация, стоимость и состояние инфраструктуры.</p></div>
        <Badge tone="success">● {available}/{providers.length || "—"} доступны</Badge>
      </div>
      <section className="provider-connect panel">
        <div><span className="eyebrow">ВАШИ API-ПОДКЛЮЧЕНИЯ</span><h2>Добавить универсальный слот</h2><p>Вставьте ключ — система распознает провайдера, проверит доступ и покажет его имя. Ключ шифруется и больше не отображается.</p></div>
        <form onSubmit={connect} autoComplete="off">
          <label>API-ключ<input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Вставьте новый ключ" minLength={8} required autoComplete="new-password" /></label>
          {showHint && <label>Уточните провайдера<select value={providerHint} onChange={(event) => setProviderHint(event.target.value)} required><option value="">Выберите безопасно</option><option value="openrouter">OpenRouter</option><option value="groq">Groq</option><option value="github">GitHub Models</option><option value="huggingface">Hugging Face</option><option value="cerebras">Cerebras</option><option value="mistral">Mistral</option><option value="yandex">YandexGPT</option></select></label>}
          {providerHint === "yandex" && <label>Folder ID каталога<input value={folderId} onChange={(event) => setFolderId(event.target.value)} placeholder="Например: b1g…" minLength={8} required autoComplete="off" /></label>}
          <button disabled={connecting || apiKey.trim().length < 8 || (providerHint === "yandex" && folderId.trim().length < 8)}>{connecting ? "Проверяем…" : "Определить и подключить"}</button>
        </form>
        <small className="provider-safety">Ключ не отправляется разным компаниям: если формат неоднозначен, приложение попросит выбрать провайдера.</small>
      </section>
      {notice && <div className="success-message" role="status">{notice}</div>}
      {error && <div className="error" role="alert">{error}</div>}
      <section className="connection-slots" aria-label="Подключённые API">
        {connections.map((connection) => <article className="panel connection-slot" key={connection.id}><span className="provider-logo">{connection.display_name.slice(0,2).toUpperCase()}</span><div><small>API-СЛОТ #{connection.id}</small><h3>{connection.display_name}</h3><p>{connection.masked_key} · только бесплатные модели</p></div><Badge tone={connection.status === "CONNECTED" ? "success" : "warning"}>{connection.status === "CONNECTED" ? "ПОДКЛЮЧЕН" : "НЕДОСТУПЕН"}</Badge><button className="secondary" onClick={() => void disconnect(connection)}>Отключить</button></article>)}
        {!connections.length && <div className="empty-slot"><b>Свободный API-слот</b><span>Подключённых внешних провайдеров пока нет.</span></div>}
      </section>
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

function GeoOpportunitiesScreen() {
  const aliceFeatureLabels: Record<string, string> = {
    search_visibility: "Видимость в Яндекс Поиске",
    landing_page_match: "Страница под конкретный запрос",
    independent_source_support: "Независимые подтверждения",
    content_completeness: "Полнота содержания",
    expertise_evidence: "Доказательства экспертности",
    freshness: "Актуальность информации",
    availability_clarity: "Цена, наличие и регион",
    technical_health: "Техническое состояние сайта",
  };
  const [platforms, setPlatforms] = useState<GeoPlatform[]>([]);
  const [promptSets, setPromptSets] = useState<FrozenPromptSet[]>([]);
  const [priorities, setPriorities] = useState<EisPriorityResult>();
  const [learnedInfluence, setLearnedInfluence] = useState<PublicationInfluenceEstimate[]>([]);
  const [siteAudit, setSiteAudit] = useState<GeoSiteAudit>();
  const [yandexIntelligence, setYandexIntelligence] = useState<YandexIntelligence>();
  const [aliceLearning, setAliceLearning] = useState<AliceLearningDashboard>();
  const [aliceAutomation, setAliceAutomation] = useState<AliceAutomationDashboard>();
  const [researches, setResearches] = useState<ResearchItem[]>([]);
  const [selectedResearchId, setSelectedResearchId] = useState<number>();
  const [auditForm, setAuditForm] = useState({ brand: "", website: "" });
  const [engine, setEngine] = useState("YandexGPT");
  const [form, setForm] = useState({ name: "", domain: "", category: "UNIVERSAL", country: "RU", language: "ru", trust: "", authority: "", citations: "", cost: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [operationResult, setOperationResult] = useState("");
  const load = useCallback(() => Promise.all([
    api.geoPlatforms(), api.frozenPromptSets(), api.publicationInfluence(), api.geoSiteAudits(),
    api.yandexIntelligence().catch(() => undefined),
    api.aliceLearningDashboard().catch(() => undefined),
    api.aliceAutomationDashboard().catch(() => undefined),
    api.listResearch(),
  ]).then(([items, sets, estimates, audits, intelligence, learning, automation, researchItems]) => {
    setPlatforms(items); setPromptSets(sets); setLearnedInfluence(estimates); setSiteAudit(audits[0]);
    const completed = [...researchItems]
      .filter((item) => item.status === "COMPLETED")
      .sort((left, right) => right.id - left.id);
    setResearches(completed);
    setSelectedResearchId((current) => {
      if (current && completed.some((item) => item.id === current)) return current;
      const savedId = Number(sessionStorage.getItem(ACTIVE_RESEARCH_KEY));
      return completed.some((item) => item.id === savedId) ? savedId : completed[0]?.id;
    });
    setYandexIntelligence(Array.isArray(intelligence?.query_map) ? intelligence : undefined);
    setAliceLearning(
      learning
      && typeof learning.observation_count === "number"
      && Array.isArray(learning.top_factors)
      && Array.isArray(learning.recommended_actions)
      && Array.isArray(learning.limitations)
        ? learning
        : undefined,
    );
    setAliceAutomation(
      automation && Array.isArray(automation.plans) && Array.isArray(automation.latest_runs)
        ? automation
        : undefined,
    );
  }), []);
  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить GEO-данные")); }, [load]);
  const selectedResearch = researches.find((item) => item.id === selectedResearchId);
  const selectedBrand = researchBrand(selectedResearch);
  useEffect(() => {
    if (!selectedResearchId || !selectedBrand) return;
    sessionStorage.setItem(ACTIVE_RESEARCH_KEY, String(selectedResearchId));
    api.aliceLearningDashboard(selectedBrand).then(setAliceLearning).catch(() => undefined);
  }, [selectedBrand, selectedResearchId]);
  const numericField = (value: string) => value.trim() === "" ? undefined : Number(value);
  const auditSite = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try { setSiteAudit(await api.runGeoSiteAudit({ brand: auditForm.brand.trim(), website_url: auditForm.website.trim() })); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось проверить сайт"); }
    finally { setBusy(false); }
  };
  const create = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await api.createGeoPlatform({
        name: form.name.trim(), domain: form.domain.trim(), category: form.category,
        country: form.country.trim().toUpperCase(), language: form.language.trim().toLowerCase(),
        domain_trust: numericField(form.trust), topical_authority_score: numericField(form.authority),
        ai_citation_history: numericField(form.citations), cost_per_placement: numericField(form.cost),
        evidence: { source: "USER_INPUT", recorded_at: new Date().toISOString() },
      });
      setForm((current) => ({ ...current, name: "", domain: "", trust: "", authority: "", citations: "", cost: "" }));
      setPriorities(undefined); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось добавить площадку"); }
    finally { setBusy(false); }
  };
  const calculate = async () => {
    if (!platforms.length) return;
    setBusy(true); setError("");
    try { setPriorities(await api.prioritizeGeoPlatforms(platforms.map((item) => item.id), engine)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось рассчитать приоритеты"); }
    finally { setBusy(false); }
  };
  const remove = async (item: GeoPlatform) => {
    setBusy(true); setError("");
    try { await api.deleteGeoPlatform(item.id); setPriorities(undefined); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось удалить площадку"); }
    finally { setBusy(false); }
  };
  const syncYandex = async () => {
    setBusy(true); setError(""); setOperationResult("");
    try {
      const status = await api.yandexWebmasterStatus();
      if (!status.connected || !status.selected_host_id) {
        window.location.assign("/settings?tab=integrations");
        return;
      }
      const result = await api.syncYandexIntelligence();
      setYandexIntelligence(result);
      setOperationResult(`Синхронизация завершена: ${result.query_map.length} поисковых запросов, ${result.yandex_ai.length} ответов YandexGPT, ${result.opportunities.length} точек роста.`);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось синхронизировать Яндекс Intelligence"); }
    finally { setBusy(false); }
  };
  const rebuildAlice = async () => {
    setBusy(true); setError(""); setOperationResult("");
    try {
      const result = await api.rebuildAliceLearning(selectedBrand || undefined);
      setAliceLearning(result);
      const missing = result.recommendation_count === 0 || result.recommendation_count === result.observation_count;
      setOperationResult(missing
        ? `Пересчёт завершён: ${result.observation_count} наблюдений, но выборка однородна (${result.recommendation_count} рекомендаций). Для обучения нужны и рекомендации, и отказы.`
        : `Пересчёт завершён: ${result.observation_count} наблюдений, ${result.recommendation_count} рекомендаций. Статус модели: ${result.status}.`);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось обучить модель Алисы"); }
    finally { setBusy(false); }
  };
  const latestAutomationTemplate = selectedResearch && (
    selectedResearch.status === "COMPLETED"
    && typeof selectedResearch.metadata?.website_url === "string"
    && Array.isArray(selectedResearch.metadata?.query_catalog)
  ) ? selectedResearch : undefined;
  const enableAliceAutomation = async () => {
    if (!latestAutomationTemplate) return;
    const metadata = latestAutomationTemplate.metadata ?? {};
    setBusy(true); setError(""); setOperationResult("");
    try {
      await api.createAliceAutomationPlan({
        template_research_id: latestAutomationTemplate.id,
        brand: String(metadata.brand ?? latestAutomationTemplate.title),
        website_url: String(metadata.website_url),
        language: String((metadata.languages as string[] | undefined)?.[0] ?? "ru"),
        region: String((metadata.regions as string[] | undefined)?.[0] ?? "RU"),
        research_profile: String(metadata.research_profile ?? "UNIVERSAL"),
        routing_profile: String(metadata.routing_profile ?? "BALANCED"),
        models: Array.isArray(metadata.selected_models)
          ? metadata.selected_models as Array<{ provider: string; model: string }>
          : [],
        repetitions: 3,
      });
      const dashboard = await api.aliceAutomationDashboard();
      setAliceAutomation(dashboard);
      const plan = dashboard.plans.find((item) => item.brand.toLocaleLowerCase() === String(metadata.brand ?? latestAutomationTemplate.title).toLocaleLowerCase());
      setOperationResult(plan ? `Мониторинг включён. Следующая проверка: ${new Date(plan.next_run_at).toLocaleString("ru-RU")}.` : "Мониторинг создан; расписание появится после обновления данных.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось включить автоматизацию"); }
    finally { setBusy(false); }
  };
  const toggleAliceAutomation = async (id: number, enabled: boolean) => {
    setBusy(true); setError("");
    try { await api.updateAliceAutomationPlan(id, { is_enabled: enabled }); setAliceAutomation(await api.aliceAutomationDashboard()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось изменить автоматизацию"); }
    finally { setBusy(false); }
  };
  const runAliceAutomation = async (id: number) => {
    setBusy(true); setError("");
    try { await api.runAliceAutomationPlan(id); setAliceAutomation(await api.aliceAutomationDashboard()); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось запустить автоматическую проверку"); }
    finally { setBusy(false); }
  };
  const platformById = new Map(platforms.map((item) => [item.id, item]));
  const activeSets = promptSets.filter((item) => item.active);
  const selectedPlans = (aliceAutomation?.plans ?? []).filter(
    (plan) => !selectedBrand || plan.brand.toLocaleLowerCase() === selectedBrand.toLocaleLowerCase(),
  );
  const aliceStatusLabel = aliceLearning?.status === "READY"
    ? "ДОСТАТОЧНО ДАННЫХ"
    : aliceLearning?.status === "INSUFFICIENT_SAMPLE"
      ? "НЕДОСТАТОЧНО РАЗНООБРАЗИЯ"
      : "НЕТ ОБУЧЕННОЙ МОДЕЛИ";
  return (
    <main className="analytics-page geo-page">
      <header className="analytics-hero">
        <div><span className="eyebrow">GEO OPPORTUNITY ENGINE</span><h1>Где публиковаться, чтобы вас рекомендовали ИИ</h1><p>Сравните площадки по авторитетности, тематической близости, истории цитирования и стоимости. Оценка EIS показывает потенциал влияния, а не выдаёт корреляцию за доказанную причинность.</p></div>
        <div className="geo-hero-controls"><label className="research-selector">Анализируемый бренд<select aria-label="Бренд для экспертного анализа" value={selectedResearchId ?? ""} onChange={(event) => setSelectedResearchId(Number(event.target.value))}><option value="" disabled>Выберите исследование</option>{researches.map((item) => <option value={item.id} key={item.id}>{researchBrand(item)} · исследование #{item.id}</option>)}</select></label><div className="geo-method"><span>Методология</span><b>{priorities?.methodology_version ?? "heuristic_v1.0"}</b><small>Версионированный расчёт</small></div></div>
      </header>
      {error && <div className="error" role="alert">{error}</div>}
      {operationResult && <div className="operation-result" role="status">{operationResult}</div>}
      <section className="geo-summary">
        <article className="analytics-card metric"><span>Площадки</span><strong>{platforms.length}</strong><small>реальные записи реестра</small></article>
        <article className="analytics-card metric"><span>Активные наборы запросов</span><strong>{activeSets.length}</strong><small>frozen prompt set</small></article>
        <article className="analytics-card metric"><span>Обученные наблюдения</span><strong>{learnedInfluence.filter((item) => item.metric === "visibility_score" && item.provider === "ALL").reduce((total, item) => total + item.sample_size, 0)}</strong><small>подтверждены обнаружением публикации</small></article>
      </section>
      <section className="analytics-card geo-site-audit">
        <div className="geo-audit-intro"><span className="eyebrow">GEO-АУДИТ САЙТА</span><h2>Готов ли сайт стать источником для ИИ</h2><p>100-балльная проверка доступности для краулеров, сущности бренда, контента, доказательности и технических сигналов. Каждый балл подтверждается наблюдаемым признаком.</p><form onSubmit={auditSite}><input aria-label="Бренд для GEO-аудита" placeholder="Название бренда" value={auditForm.brand} onChange={(event) => setAuditForm({ ...auditForm, brand: event.target.value })} required /><input aria-label="Сайт для GEO-аудита" type="url" placeholder="https://example.ru" value={auditForm.website} onChange={(event) => setAuditForm({ ...auditForm, website: event.target.value })} required /><Button type="submit" disabled={busy}>{busy ? "Проверяем сайт…" : "Провести GEO-аудит"}</Button></form></div>
        {siteAudit ? <div className="geo-audit-result"><header><div><strong>{siteAudit.score.toFixed(1)}</strong><span>из 100 · {siteAudit.grade}</span></div><Badge tone={siteAudit.score >= 70 ? "success" : siteAudit.score >= 45 ? "warning" : "danger"}>v{siteAudit.algorithm_version}</Badge></header><p className="method-note"><b>Как получена оценка:</b> сервис заново загрузил {siteAudit.final_url}, robots.txt и sitemap. За каждый реально обнаруженный признак начислены указанные ниже баллы; итог — простая сумма без скрытой AI-оценки. Это готовность сайта быть понятным источником, а не вероятность рекомендации бренда.</p><div className="geo-audit-categories">{Object.entries(siteAudit.category_scores).map(([name, value]) => <div key={name}><span>{name}</span><b>{value.toFixed(0)}</b></div>)}</div><h3>Главные действия</h3>{siteAudit.opportunities.slice(0, 5).map((item) => <article className="geo-audit-action" key={`${item.problem}:${item.affected_metric}`}><Badge tone={item.priority === "P0" ? "danger" : "warning"}>{item.priority}</Badge><div><b>{item.problem}</b><p>{item.action}</p><small>{item.expected_effect} · Проверка: {item.verification}</small></div></article>)}<details><summary>Показать все доказательства расчёта</summary>{siteAudit.checks.map((check) => <div className="geo-audit-check" key={check.code}><span>{check.passed ? "✓" : "×"}</span><div><b>{check.title}</b><small>{check.evidence}</small>{check.recommendation ? <p>{check.recommendation}</p> : null}</div><strong>{check.points}/{check.max_points}</strong></div>)}</details><p className="method-note">{siteAudit.limitation}</p></div> : <div className="geo-empty"><strong>Аудит ещё не выполнялся</strong><p>Введите официальный сайт. Система не подставит оценку без фактического чтения страницы, robots.txt и sitemap.</p></div>}
      </section>
      <section className="geo-value-flow" aria-labelledby="alice-workflow-title">
        <header>
          <span className="eyebrow">КАК ЭТО ПОМОГАЕТ БРЕНДУ</span>
          <h2 id="alice-workflow-title">От реального спроса — к плану роста в Алисе</h2>
          <p>Система не пытается угадать закрытый алгоритм Яндекса. Она регулярно измеряет доступные сигналы и показывает, какие изменения совпадают с появлением бренда в рекомендациях.</p>
        </header>
        <div>
          <article><span>1</span><b>Находим спрос</b><p>Берём реальные запросы и страницы из Яндекс Вебмастера.</p></article>
          <article><span>2</span><b>Проверяем Алису</b><p>Задаём одинаковые покупательские вопросы и сохраняем ответы.</p></article>
          <article><span>3</span><b>Сравниваем изменения</b><p>Отслеживаем рекомендации, источники, позиции и публикации во времени.</p></article>
          <article><span>4</span><b>Предлагаем действие</b><p>Показываем, какую страницу или источник улучшить и как проверить результат.</p></article>
        </div>
      </section>
      <section className="analytics-card geo-site-audit yandex-intelligence">
        <div className="geo-audit-intro"><span className="eyebrow">ШАГ 1 · РЕАЛЬНЫЙ СПРОС</span><h2>По каким запросам вас находят — и где вы теряете возможность</h2><p>Яндекс Вебмастер показывает реальные запросы покупателей, показы, позиции и целевые страницы. Мы соединяем их с ответами YandexGPT, чтобы найти запросы, где сайт уже виден в Поиске, но бренд ещё не попадает в рекомендации Алисы.</p><div className="geo-user-value"><b>Ценность для вас</b><p>Понятный приоритет: какой запрос развивать, какую страницу улучшить и чем подтвердить бренд.</p></div><Button onClick={() => void syncYandex()} disabled={busy}>{busy ? "Синхронизируем…" : yandexIntelligence ? "Обновить реальные данные" : "Подключить реальные данные"}</Button></div>
        {yandexIntelligence ? <div className="geo-audit-result"><header><div><strong>{yandexIntelligence.query_map.length}</strong><span>измеренных связок запрос → страница</span></div><Badge tone={yandexIntelligence.evidence_status === "MEASURED" ? "success" : "warning"}>{yandexIntelligence.evidence_status}</Badge></header>
          <div className="geo-audit-categories"><div><span>Ответы YandexGPT</span><b>{yandexIntelligence.yandex_ai.length}</b></div><div><span>Упоминания бренда</span><b>{yandexIntelligence.yandex_ai.filter((item) => item.mentioned).length}</b></div><div><span>Внешние ссылки</span><b>{yandexIntelligence.webmaster.external_links?.count ?? "—"}</b></div><div><span>Проблемы сайта</span><b>{Object.values(yandexIntelligence.webmaster.diagnostics?.problems ?? {}).filter((item) => item.state === "PRESENT").length}</b></div></div>
          <h3>Приоритетные запросы</h3>{yandexIntelligence.opportunities.slice(0, 8).map((item) => <article className="geo-audit-action" key={item.query}><Badge tone={item.priority === "P0" ? "danger" : "warning"}>{item.priority}</Badge><div><b>{item.query} · {item.priority_score.toFixed(1)}</b><p>{item.problem}</p><small>{item.action}</small><details><summary>Доказательства и проверка</summary><p>{item.evidence}</p><p>{item.verification}</p><p>{item.expected_range} · Уверенность {item.confidence}</p></details></div></article>)}
          <details><summary>Карта запросов Яндекса</summary>{yandexIntelligence.query_map.slice(0, 30).map((item) => <div className="geo-audit-check" key={`${item.query}:${item.url ?? ""}`}><span>{item.brand_mentioned === true ? "✓" : item.brand_mentioned === false ? "×" : "?"}</span><div><b>{item.query}</b><small>{item.url || "Целевая страница не определена"}</small></div><strong>{item.position !== undefined ? `позиция ${item.position.toFixed(1)}` : "нет позиции"}</strong></div>)}</details>
          {yandexIntelligence.limitations.length ? <details><summary>Ограничения данных</summary>{yandexIntelligence.limitations.map((item) => <p className="method-note" key={item}>{item}</p>)}</details> : null}</div> : <div className="geo-empty"><strong>Начните с подключения реального спроса</strong><p>Подключите подтверждённый сайт в Яндекс Вебмастере. После синхронизации здесь появятся запросы покупателей, страницы сайта и точки роста.</p><ol className="geo-empty-steps"><li>Откройте «Настройки» → «Интеграции».</li><li>Подключите Яндекс Вебмастер и выберите сайт.</li><li>Вернитесь сюда и обновите данные.</li></ol></div>}
      </section>
      <section className="analytics-card geo-site-audit alice-learning">
        <div className="geo-audit-intro"><span className="eyebrow">ШАГ 2 · НАБЛЮДАЕМЫЕ ЗАКОНОМЕРНОСТИ</span><h2>Что чаще встречается рядом с рекомендацией бренда</h2><p>Система сравнивает случаи, когда Алиса рекомендовала бренд и когда не рекомендовала. Она проверяет наличие подходящей страницы, независимых источников, поисковую позицию и другие измеримые признаки.</p><div className="geo-user-value"><b>Ценность для вас</b><p>Не общий совет «улучшайте контент», а проверяемая гипотеза: какой сигнал усилить и каким повторным исследованием измерить результат.</p></div><Button onClick={() => void rebuildAlice()} disabled={busy}>{busy ? "Пересчитываем…" : "Обновить выводы по истории"}</Button></div>
        {aliceLearning ? <div className="geo-audit-result"><header><div><strong>{aliceLearning.observation_count}</strong><span>наблюдений · {aliceLearning.recommendation_count} рекомендаций</span></div><Badge tone={aliceLearning.status === "READY" ? "success" : "warning"}>{aliceStatusLabel}</Badge></header>
          {aliceLearning.model ? <><div className="geo-audit-categories"><div><span>Бренд</span><b>{aliceLearning.brand ?? "—"}</b></div><div><span>Проверено ответов</span><b>{aliceLearning.observation_count}</b></div><div><span>Рекомендаций</span><b>{aliceLearning.recommendation_count}</b></div><div><span>Доля рекомендаций</span><b>{aliceLearning.observation_count ? `${(aliceLearning.recommendation_count / aliceLearning.observation_count * 100).toFixed(1)}%` : "—"}</b></div></div><h3>Что проверить в первую очередь</h3>{aliceLearning.recommended_actions.length ? aliceLearning.recommended_actions.slice(0, 5).map((item) => <article className="geo-audit-action" key={item.feature}><Badge tone="warning">ГИПОТЕЗА</Badge><div><b>{item.action}</b><p>{aliceFeatureLabels[item.feature] ?? item.feature}: сейчас {Math.round(item.current_value * 100)}%</p><small>Ожидаемое изменение вероятности рекомендации: +{(item.predicted_delta * 100).toFixed(1)} п.п. · Подтвердите повторным исследованием</small></div></article>) : <div className="geo-empty"><strong>Пока нельзя честно рекомендовать действие</strong><p>Наблюдения собраны, но системе не хватает разнообразия успешных и неуспешных ответов либо устойчивого измеримого сигнала. Продолжайте одинаковые проверки — действие появится только при достаточных данных.</p></div>}<details><summary>Для эксперта: как рассчитан вывод</summary>{aliceLearning.top_factors.filter((item) => item.feature).slice(0, 8).map((item) => <div className="geo-audit-check" key={item.feature}><span>{item.direction === "POSITIVE" ? "↑" : item.direction === "NEGATIVE" ? "↓" : "?"}</span><div><b>{aliceFeatureLabels[item.feature ?? ""] ?? item.feature}</b><small>Наблюдаемая связь, а не доказанная причина</small></div><strong>{item.coefficient?.toFixed(3) ?? "—"}</strong></div>)}</details></> : <div className="geo-empty"><strong>Выводы ещё не рассчитаны</strong><p>Сначала нужны одинаковые вопросы с сохранёнными ответами YandexGPT. После нескольких исследований система сможет сравнить рекомендации и отказы.</p></div>}
          {aliceLearning.limitations.length ? <details><summary>Что важно учитывать</summary>{aliceLearning.limitations.map((item) => <p className="method-note" key={item}>{item}</p>)}</details> : null}</div> : <div className="geo-empty"><strong>Пока нет истории для сравнения</strong><p>Завершите первое исследование через YandexGPT. Каждый сохранённый ответ станет наблюдением для будущего сравнения.</p></div>}
      </section>
      <section className="analytics-card geo-site-audit alice-automation">
        <div className="geo-audit-intro"><span className="eyebrow">ШАГ 3 · КОНТРОЛЬ ИЗМЕНЕНИЙ</span><h2>Следим, помогли ли ваши действия</h2><p>Система регулярно повторяет один и тот же набор вопросов. Благодаря неизменной контрольной группе видно, когда бренд начал или перестал появляться в рекомендациях и что изменилось перед этим.</p><div className="geo-user-value"><b>Сейчас выбран</b><p>{selectedBrand || "Выберите завершённое исследование выше"}. Мониторинг создаётся отдельно для каждого бренда и не смешивает результаты.</p></div>{selectedPlans.length ? null : <Button onClick={() => void enableAliceAutomation()} disabled={busy || !latestAutomationTemplate}>{busy ? "Настраиваем…" : `Включить проверку ${selectedBrand || "бренда"}`}</Button>}{!latestAutomationTemplate && !selectedPlans.length ? <small>Сначала завершите исследование этого бренда — оно станет контрольной точкой.</small> : null}</div>
        {selectedPlans.length ? <div className="geo-audit-result">{selectedPlans.map((plan) => { const latestRun = aliceAutomation?.latest_runs.find((item) => item.plan_id === plan.id); return <article className="geo-audit-action" key={plan.id}><Badge tone={plan.is_enabled ? "success" : "neutral"}>{plan.is_enabled ? "АКТИВЕН" : "ПАУЗА"}</Badge><div><b>{plan.brand} · {plan.repetitions} прогона каждого вопроса</b><p>Следующая проверка: {new Date(plan.next_run_at).toLocaleString("ru-RU")} · дневной лимит ${plan.daily_budget_usd.toFixed(2)} · месячный ${plan.monthly_budget_usd.toFixed(2)}</p><small>{latestRun ? `Последний запуск: ${latestRun.status}, ${latestRun.task_count} проверок, $${(latestRun.actual_cost_usd ?? 0).toFixed(4)}` : "Автоматических запусков ещё не было"}</small><div className="button-row"><Button onClick={() => void runAliceAutomation(plan.id)} disabled={busy || !plan.is_enabled}>Проверить сейчас</Button><button className="secondary" onClick={() => void toggleAliceAutomation(plan.id, !plan.is_enabled)} disabled={busy}>{plan.is_enabled ? "Поставить на паузу" : "Возобновить"}</button></div></div></article>; })}<p className="method-note">Закономерности считаются гипотезами. Причинный эффект публикации подтверждается только отдельным зафиксированным экспериментом до/после или с контрольной группой.</p></div> : <div className="geo-empty"><strong>Для {selectedBrand || "этого бренда"} мониторинг ещё не включён</strong><p>Нажмите кнопку выше — система возьмёт выбранное исследование как шаблон и будет повторять именно его вопросы.</p></div>}
      </section>
      <section className="geo-layout">
        <form className="analytics-card geo-form" onSubmit={create}>
          <div><span className="eyebrow">ДОБАВИТЬ ПЛОЩАДКУ</span><h2>Источник для проверки</h2><p>Укажите только измеренные значения. Пустое поле будет отмечено как «нет данных», а не как ноль.</p></div>
          <label>Название площадки<input aria-label="Название площадки" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Например, отраслевое СМИ" required /></label>
          <label>Домен<input aria-label="Домен площадки" value={form.domain} onChange={(event) => setForm({ ...form, domain: event.target.value })} placeholder="example.ru" required /></label>
          <div className="geo-form-grid">
            <label>Категория<input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} /></label>
            <label>Страна<input value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value })} /></label>
            <label>Язык<input value={form.language} onChange={(event) => setForm({ ...form, language: event.target.value })} /></label>
            <label>Domain Trust, 0–100<input type="number" min="0" max="100" value={form.trust} onChange={(event) => setForm({ ...form, trust: event.target.value })} /></label>
            <label>Тематический авторитет, 0–100<input type="number" min="0" max="100" value={form.authority} onChange={(event) => setForm({ ...form, authority: event.target.value })} /></label>
            <label>Цитирования ИИ<input type="number" min="0" value={form.citations} onChange={(event) => setForm({ ...form, citations: event.target.value })} /></label>
            <label>Стоимость размещения<input type="number" min="0" value={form.cost} onChange={(event) => setForm({ ...form, cost: event.target.value })} /></label>
          </div>
          <Button type="submit" disabled={busy}>{busy ? "Сохраняем…" : "Добавить в реестр"}</Button>
        </form>
        <article className="analytics-card geo-prompts">
          <span className="eyebrow">КАРТА ЗАПРОСОВ</span><h2>Зафиксированные наборы</h2>
          {activeSets.length ? activeSets.map((set) => <div className="prompt-set-row" key={set.id}><div><b>{set.name}</b><span>{set.category} · {set.language}/{set.region}</span></div><Badge tone="success">v{set.version} · АКТИВЕН</Badge><small>{set.templates.length} шаблонов · fingerprint {set.fingerprint.slice(0, 10)}…</small></div>) : <div className="empty-state"><b>Активных наборов пока нет</b><p>Создайте и активируйте Frozen Prompt Set через API. Здесь появится его версия и контрольный fingerprint.</p></div>}
        </article>
      </section>
      <section className="geo-learning-section">
        <div className="geo-ranking-head compact">
          <div><span className="eyebrow">ОБУЧЕНИЕ НА ПУБЛИКАЦИЯХ</span><h2>Что уже повлияло на ответы ИИ</h2><p>Здесь показаны только площадки, публикации которых были обнаружены в ответах и сопоставлены с одинаковым набором запросов до и после размещения.</p></div>
        </div>
        {learnedInfluence.some((item) => item.metric === "visibility_score" && item.provider === "ALL") ? <div className="geo-learned-grid">{learnedInfluence.filter((item) => item.metric === "visibility_score" && item.provider === "ALL").map((item) => <article className="analytics-card geo-learned" key={item.id}><header><div><small>{item.channel} · {item.content_type}</small><h3>{item.resource_domain}</h3></div><Badge tone={item.controlled_experiments > 0 || item.evidence_level === "CORRELATION" ? "success" : "warning"}>{item.controlled_experiments > 0 ? "С КОНТРОЛЬНОЙ ГРУППОЙ" : item.evidence_level === "CORRELATION" ? "ПОВТОРЯЕМАЯ КОРРЕЛЯЦИЯ" : "НАБЛЮДЕНИЕ"}</Badge></header><div className="geo-learned-metrics"><div><span>Изменение Visibility</span><strong>{item.expected_delta >= 0 ? "+" : ""}{item.expected_delta.toFixed(1)}</strong></div><div><span>Диапазон</span><b>{item.confidence_min.toFixed(1)}…{item.confidence_max.toFixed(1)}</b></div><div><span>Наблюдения</span><b>{item.sample_size}</b></div><div><span>Контрольные</span><b>{item.controlled_experiments}</b></div><div><span>Уверенность</span><b>{Math.round(item.confidence_score * 100)}%</b></div></div><p>Алгоритм {item.algorithm_version}. Это наблюдаемая связь, а не гарантия причинного эффекта.</p></article>)}</div> : <div className="analytics-card geo-empty"><strong>Подтверждённых наблюдений пока нет</strong><p>Добавьте вышедшую публикацию в отчёте и повторите тот же Frozen Prompt Set. Площадка появится здесь только после обнаружения URL в ответах ИИ.</p></div>}
      </section>
      <section className="geo-ranking-head">
        <div><span className="eyebrow">EIS — ВЛИЯНИЕ ИСТОЧНИКА</span><h2>Приоритет площадок</h2><p>Чем выше EIS, тем сильнее совокупные сигналы площадки для выбранной AI-системы.</p></div>
        <div className="geo-calculate"><label>ИИ для оценки<select value={engine} onChange={(event) => setEngine(event.target.value)}><option>YandexGPT</option><option>ChatGPT</option><option>Gemini</option><option>GigaChat</option><option>Perplexity</option><option>Claude</option></select></label><Button onClick={() => void calculate()} disabled={busy || !platforms.length}>{busy ? "Считаем…" : "Рассчитать приоритет"}</Button></div>
      </section>
      {!platforms.length ? <section className="analytics-card geo-empty"><strong>Площадки ещё не добавлены</strong><p>Добавьте реальный ресурс выше. Система не подставляет демонстрационные сайты и не выдумывает показатели.</p></section> : priorities ? <section className="geo-ranking">
        {priorities.items.map(({ score, cost_efficiency }, index) => { const platform = platformById.get(score.platform_id); const measured = score.eis_value !== undefined && score.eis_value !== null; return <article className="analytics-card geo-rank-card" key={score.id}><div className="geo-rank-number">#{index + 1}</div><div className="geo-rank-main"><div><h3>{platform?.name ?? score.platform_id}</h3><a href={`https://${platform?.domain}`} target="_blank" rel="noreferrer">{platform?.domain}</a></div><Badge tone={score.priority === "P0" ? "danger" : score.priority === "P1" ? "warning" : "neutral"}>{score.priority ?? "НЕТ ПРИОРИТЕТА"}</Badge></div><div className="geo-score"><strong>{measured ? score.eis_value?.toFixed(1) : "—"}</strong><span>из 100</span></div><div className="geo-components">{Object.entries(score.components).map(([name, component]) => <div key={name}><span>{name === "authority" ? "Авторитет" : name === "match" ? "Соответствие запросу" : name === "content" ? "Качество контента" : name}</span><b>{component.value === null || component.value === undefined ? "Нет данных" : component.value.toFixed(1)}</b><div className="track"><i style={{ width: `${component.value ?? 0}%` }} /></div>{component.exclusions.length > 0 && <small>Не учтено: {component.exclusions.join(", ")}</small>}</div>)}</div><footer><span>Доказательства: <b>{score.evidence_status === "MEASURED" ? "измерено" : score.evidence_status === "PARTIAL" ? "частичные данные" : "не измерено"}</b></span><span>Эффективность затрат: <b>{cost_efficiency === undefined || cost_efficiency === null ? "нет данных" : cost_efficiency.toFixed(4)}</b></span><button className="secondary" onClick={() => void remove(platform!)} disabled={busy}>Удалить</button></footer></article>; })}
        <p className="geo-limitation">Важно: {priorities.limitations.join(" ")} Перед размещением подтвердите эффект повторным исследованием с неизменным набором запросов.</p>
      </section> : <section className="geo-platform-list">{platforms.map((item) => <article className="analytics-card record-card" key={item.id}><div><small>{item.category} · {item.country}/{item.language}</small><h2>{item.name}</h2><p>{item.domain} · Domain Trust: {item.domain_trust ?? "нет данных"} · Тематический авторитет: {item.topical_authority_score ?? "нет данных"}</p></div><Badge tone={item.active ? "success" : "neutral"}>{item.active ? "В РЕЕСТРЕ" : "ОТКЛЮЧЕНА"}</Badge></article>)}</section>}
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
      <section className="decision-strip" aria-label="Что важно сейчас">
        <div><span>Текущий результат</span><strong>{healthLabel(visibility)}</strong><small>Видимость {visibility.toFixed(1)} из 100</small></div>
        <div><span>Главное ограничение</span><strong>{weakest.label}</strong><small>Оценка {weakest.value.toFixed(1)} из 100</small></div>
        <button onClick={() => onNavigate("recommendations")}><span>Следующий шаг</span><strong>Открыть план улучшений</strong><small>Конкретные действия и ожидаемый эффект →</small></button>
      </section>
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
      <ActionCenter recommendations={data.recommendations ?? []} />
      <details className="dashboard-details">
        <summary><span>Подробная аналитика</span><small>Тренды, баланс сигналов, pipeline и benchmark</small></summary>
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
      </details>
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
  const titles: Record<string, string> = {
    recommendation_score: "Добиться рекомендаций бренда в покупательских запросах",
    citation_score: "Получить независимые публикации и проверяемые ссылки",
    mention_score: "Расширить присутствие бренда по целевым запросам",
    coverage_score: "Проверить бренд в большем числе подключённых моделей",
    confidence_score: "Увеличить доказательную выборку исследования",
  };
  const priorityLabels: Record<string, string> = { CRITICAL: "КРИТИЧНО", HIGH: "ВАЖНО", MEDIUM: "СРЕДНИЙ ПРИОРИТЕТ", LOW: "НИЗКИЙ ПРИОРИТЕТ" };
  return (
    <section className="action-center">
      <div className="section-head">
        <div>
          <span className="eyebrow">ПЛАН ДЕЙСТВИЙ</span>
          <h2>Что делать дальше</h2>
          <p>Рекомендации, рассчитанные для последнего исследования.</p>
        </div>
      </div>
      <div className="action-list">
        {recommendations.length ? recommendations.map((action, index) => (
          <article className="action-item" key={`${action.explanation}-${index}`}>
            <div>
              <span className="priority">{priorityLabels[action.priority ?? ""] ?? "ПРИОРИТЕТ НЕ УКАЗАН"}</span>
              <h3>{titles[action.metric ?? ""] ?? "Улучшить измеряемый сигнал бренда"}</h3>
              <p>{metricNames[action.metric ?? ""] ?? "Метрика"}: сейчас {action.metric_value?.toFixed(1) ?? "нет данных"} из 100.</p>
              <div className="action-facts">
                <b>Основание: правило методологии v1.0 сработало на фактах последнего исследования</b>
                <span>Конкретные площадки и способ проверки — в подробном плане</span>
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
  const researchRegions = [
    ["RU", "Вся Россия"],
    ["RU-MOW", "Москва"],
    ["RU-SPE", "Санкт-Петербург"],
    ["RU-NVS", "Новосибирск"],
    ["RU-SVE", "Екатеринбург"],
    ["RU-TA", "Казань"],
    ["RU-KYA", "Красноярск"],
    ["RU-NIZ", "Нижний Новгород"],
    ["RU-CHE", "Челябинск"],
    ["RU-BA", "Уфа"],
    ["RU-SAM", "Самара"],
    ["RU-ROS", "Ростов-на-Дону"],
    ["RU-KDA", "Краснодар"],
    ["RU-OMS", "Омск"],
    ["RU-VOR", "Воронеж"],
    ["RU-PER", "Пермь"],
    ["RU-VGG", "Волгоград"],
  ] as const;
  const saved = useMemo(() => { try { return JSON.parse(sessionStorage.getItem("research-wizard-v3") ?? "{}") as Partial<{ step: number; brand: string; websiteUrl: string; brandProfile: BrandProfile; region: string; language: string; profile: WizardPayload["routing_profile"]; scope: WizardPayload["research_scope"]; researchProfile: WizardPayload["research_profile"]; selectedModels: string[]; customQueries: string[] }>; } catch { return {}; } }, []);
  const [step, setStep] = useState(saved.step && saved.step >= 1 && saved.step <= 8 ? saved.step : 1);
  const [brand, setBrand] = useState(saved.brand ?? "");
  const [websiteUrl, setWebsiteUrl] = useState(saved.websiteUrl ?? "");
  const [brandProfile, setBrandProfile] = useState<BrandProfile | undefined>(saved.brandProfile);
  const [competitorName, setCompetitorName] = useState("");
  const [competitorWebsite, setCompetitorWebsite] = useState("");
  const [competitors, setCompetitors] = useState<Array<{ name: string; website_url?: string }>>([]);
  const [region, setRegion] = useState(
    researchRegions.some(([value]) => value === saved.region) ? saved.region ?? "RU" : "RU",
  );
  const [language, setLanguage] = useState(saved.language ?? "ru");
  const [profile, setProfile] = useState<WizardPayload["routing_profile"]>(saved.profile ?? "BALANCED");
  const [scope, setScope] = useState<NonNullable<WizardPayload["research_scope"]>>(saved.scope ?? "SELECTED");
  const [researchProfile, setResearchProfile] = useState<NonNullable<WizardPayload["research_profile"]>>(saved.researchProfile ?? "UNIVERSAL");
  const [models, setModels] = useState<RouterModel[]>([]);
  const [runtimeProviders, setRuntimeProviders] = useState<SystemProviderItem[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>(saved.selectedModels ?? []);
  const [customQueries, setCustomQueries] = useState<string[]>(saved.customQueries ?? []);
  const [review, setReview] = useState<WizardReview>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.routerModels(), api.systemProviders()])
      .then(([registry, runtime]) => {
        setModels(registry.items);
        setRuntimeProviders(runtime.providers);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось проверить подключение моделей"));
  }, []);
  useEffect(() => { sessionStorage.setItem("research-wizard-v3", JSON.stringify({ step, brand, websiteUrl, brandProfile, region, language, profile, scope, researchProfile, selectedModels, customQueries })); }, [step, brand, websiteUrl, brandProfile, region, language, profile, scope, researchProfile, selectedModels, customQueries]);
  const scopedModels = () => {
    const ready = models.filter((item) => modelIsReady(item));
    if (scope === "ALL") return ready;
    if (scope === "RUSSIAN") return ready.filter((item) => ["yandex", "yandexgpt", "gigachat", "sber"].includes(item.provider.toLowerCase()));
    if (scope === "FREE") return ready.filter((item) => item.tier === "FREE" || item.tier === "LOCAL" || (item.pricing.input_per_million === 0 && item.pricing.output_per_million === 0));
    if (scope === "COMMERCIAL") return ready.filter((item) => item.tier !== "FREE" && item.tier !== "LOCAL" && (item.pricing.input_per_million > 0 || item.pricing.output_per_million > 0));
    return ready.filter((item) => selectedModels.includes(item.id));
  };
  const runtimeFor = (model: RouterModel) => runtimeProviders.find((item) => item.model_id === model.id)
    ?? runtimeProviders.find((item) => item.provider === model.provider);
  const modelIsReady = (model: RouterModel) => runtimeFor(model)?.interface.available === true;
  const modelTitle = (model: RouterModel) => model.provider === "ollama" ? "Ollama · Qwen 2.5 3B" : model.display_name;
  const payload = (): WizardPayload => ({
    brand,
    website_url: websiteUrl,
    brand_profile: brandProfile,
    competitors,
    routing_profile: profile,
    models: scopedModels().map((model) => ({ provider: model.provider, model: model.id })),
    research_scope: scope,
    research_profile: researchProfile,
    languages: [language],
    regions: [region],
    prompt_code: "ai-visibility",
    research_template_code: "ai-visibility",
    custom_queries: customQueries,
  });
  async function next() {
    if (step === 1) {
      if (!brand.trim() || !websiteUrl.trim()) {
        setError("Укажите название бренда и официальный сайт.");
        return;
      }
      setBusy(true);
      setError("");
      try {
        setBrandProfile(await api.brandProfile(brand, websiteUrl));
        setStep(2);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Не удалось изучить сайт бренда");
      } finally {
        setBusy(false);
      }
      return;
    }
    if (step < 7) return setStep(step + 1);
    setBusy(true);
    setError("");
    try {
      const generatedReview = await api.review({ ...payload(), custom_queries: [] });
      setReview(generatedReview);
      setCustomQueries(generatedReview.query_catalog.map((item) => item.text));
      setStep(8);
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
      const knownResearchIds = new Set((await api.listResearch()).map((item) => item.id));
      let result: ReportResult;
      try {
        result = await api.run(payload());
      } catch (reason) {
        const message = reason instanceof Error ? reason.message : String(reason);
        const connectionLost = reason instanceof TypeError
          || /failed to fetch|network|connection|load failed/i.test(message);
        if (!connectionLost) throw reason;
        result = await recoverResearchResult(knownResearchIds, brand);
      }
      if (result.research.status !== "COMPLETED") throw new Error("Исследование завершилось с ошибкой. Подробности доступны в разделе Research.");
      sessionStorage.removeItem("research-wizard-v3");
      onComplete(result);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Не удалось запустить исследование",
      );
    } finally {
      setBusy(false);
    }
  }
  async function recoverResearchResult(knownIds: Set<number>, expectedBrand: string): Promise<ReportResult> {
    for (let attempt = 0; attempt < 300; attempt += 1) {
      const researches = await api.listResearch();
      const candidate = researches
        .filter((item) => !knownIds.has(item.id))
        .filter((item) => item.title.toLocaleLowerCase().includes(expectedBrand.trim().toLocaleLowerCase()))
        .sort((left, right) => right.id - left.id)[0];
      if (candidate?.status === "COMPLETED") {
        return {
          research: { id: candidate.id, title: candidate.title, status: candidate.status },
          report_url: `/research/${candidate.id}/final-report`,
          report: await api.finalReport(candidate.id),
        };
      }
      if (candidate?.status === "FAILED") {
        throw new Error("Исследование завершилось с ошибкой. Подробности доступны в разделе «Исследования».");
      }
      await new Promise((resolve) => window.setTimeout(resolve, 3000));
    }
    throw new Error("Исследование продолжает выполняться. Его статус доступен в разделе «Исследования».");
  }
  const titles = [
    "Как называется бренд?",
    "Где вы работаете?",
    "На каком языке искать?",
    "Какие ИИ проверить?",
    "Как исследовать?",
    "Какой профиль использовать?",
    "Как выполнить исследование?",
    "Всё готово к исследованию",
  ];
  return (
    <main className="wizard-page">
      <button
        className="back-link"
        onClick={step === 1 ? () => { sessionStorage.removeItem("research-wizard-v3"); onCancel(); } : () => setStep(step - 1)}
      >
        ← {step === 1 ? "На главную" : "Назад"}
      </button>
      <div className="stepper">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
          <span key={n} className={n <= step ? "active" : ""}>
            {n < step ? "✓" : n}
          </span>
        ))}
      </div>
      <section className="wizard-focus">
        <span className="eyebrow">ШАГ {step} ИЗ 8</span>
        <h1>{titles[step - 1]}</h1>
        <p>
          {step === 1
            ? "Укажите официальный сайт — сначала мы изучим категории, товары и характеристики бренда."
            : step === 4
              ? "Выберите конкретные модели из активного реестра платформы."
              : "Это поможет сделать исследование точнее."}
        </p>
        {step === 1 && (
          <>
          <label className="hero-field">
            Название бренда
            <input
              autoFocus
              value={brand}
              onChange={(e) => { setBrand(e.target.value); setBrandProfile(undefined); setCustomQueries([]); setReview(undefined); }}
              placeholder="Например, Skinjestique"
            />
          </label>
          <label className="hero-field">
            Официальный сайт
            <input
              value={websiteUrl}
              onChange={(e) => { setWebsiteUrl(e.target.value); setBrandProfile(undefined); }}
              placeholder="https://brand.example"
              inputMode="url"
            />
          </label>
          </>
        )}
        {step === 2 && brandProfile && (
          <div className="panel brand-profile-preview">
            <span className="section-label">ПРОФИЛЬ БРЕНДА ПО ОФИЦИАЛЬНОМУ САЙТУ</span>
            <p>Изучено страниц: <b>{brandProfile.pages_analyzed}</b> · уверенность профиля: <b>{Math.round(brandProfile.confidence * 100)}%</b></p>
            <p><b>Категории:</b> {brandProfile.categories.join(", ") || "не извлечены"}</p>
            <p><b>Товары:</b> {brandProfile.products.slice(0, 8).map((item) => item.name).join(", ") || "не извлечены"}</p>
            <p><b>Характеристики:</b> {brandProfile.attributes.join(", ") || "не извлечены"}</p>
            <h3>Известные конкуренты</h3>
            <p className="muted">Добавьте известных конкурентов. Других система найдёт в ответах ИИ автоматически.</p>
            <input value={competitorName} onChange={(event) => setCompetitorName(event.target.value)} placeholder="Название конкурента" />
            <input value={competitorWebsite} onChange={(event) => setCompetitorWebsite(event.target.value)} placeholder="Официальный сайт конкурента" />
            <button type="button" onClick={() => { if (!competitorName.trim()) return; setCompetitors((items) => [...items, { name: competitorName.trim(), website_url: competitorWebsite.trim() || undefined }]); setCompetitorName(""); setCompetitorWebsite(""); }}>Добавить конкурента</button>
            {competitors.map((item) => <p key={item.name}>{item.name} · {item.website_url || "сайт не указан"}</p>)}
          </div>
        )}
        {step === 2 && (
          <div className="panel">
            <label className="hero-field">
              География анализа
              <select
                aria-label="Регион исследования"
                value={region}
                onChange={(event) => setRegion(event.target.value)}
              >
                {researchRegions.map(([value, label]) => (
                  <option value={value} key={value}>{label}</option>
                ))}
              </select>
            </label>
            <p className="muted">
              «Вся Россия» измеряет федеральную выдачу. Город добавляется в каждый
              покупательский запрос и показывает локальные рекомендации ИИ.
            </p>
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
          <div><div className="wizard-inline-actions"><button type="button" onClick={() => setSelectedModels(models.filter(modelIsReady).map((item) => item.id))}>Выбрать подключённые</button><button type="button" onClick={() => setSelectedModels([])}>Очистить</button><button type="button" onClick={() => localStorage.setItem("research-model-preset", JSON.stringify(selectedModels))}>Сохранить набор</button><button type="button" onClick={() => { try { const savedPreset = JSON.parse(localStorage.getItem("research-model-preset") ?? "[]") as string[]; setSelectedModels(savedPreset.filter((id) => models.some((model) => model.id === id && modelIsReady(model)))); } catch { setSelectedModels([]); } }}>Загрузить набор</button></div><div className="model-grid">
            {models.length ? models.map((model) => { const ready = modelIsReady(model); const runtime = runtimeFor(model); return <button type="button" disabled={!ready} aria-disabled={!ready} className={`model ${selectedModels.includes(model.id) ? "active" : ""} ${ready ? "ready" : "not-ready"}`} key={model.id} onClick={() => setSelectedModels((current) => current.includes(model.id) ? current.filter((id) => id !== model.id) : [...current, model.id])}><span className="provider-icon">{selectedModels.includes(model.id) ? "✓" : ready ? "○" : "×"}</span><b>{modelTitle(model)}</b><small>{model.provider === "ollama" ? "Локальная бесплатная модель" : `${model.provider} · ${model.version}`}</small><i className={ready ? "provider-ready" : "provider-offline"}>{ready ? "Подключена" : runtime?.interface.error ? "Ошибка подключения" : "Не подключена"}</i></button>; }) : <p className="empty-state">Активные модели не найдены в реестре. Проверьте настройки провайдеров.</p>}
          </div></div>
        )}
        {step === 5 && (
          <div className="option-list">{[["ALL", "Все модели"], ["SELECTED", "Только выбранные"], ["RUSSIAN", "Только российские"], ["COMMERCIAL", "Только коммерческие"], ["FREE", "Только бесплатные"], ["CONSENSUS", "Консенсус"], ["COMPARE", "Сравнить модели"]].map(([value, label]) => <button type="button" className={scope === value ? "selected" : ""} onClick={() => setScope(value as typeof scope)} key={value}><span>{label}</span><small>{value}</small></button>)}</div>
        )}
        {step === 6 && (
          <div className="option-list">{[["GEO", "GEO"], ["ECOMMERCE", "Электронная коммерция"], ["MEDICAL", "Медицина"], ["BEAUTY", "Красота"], ["ENTERPRISE", "Корпоративный"], ["UNIVERSAL", "Универсальный"]].map(([value, label]) => <button type="button" className={researchProfile === value ? "selected" : ""} onClick={() => setResearchProfile(value as typeof researchProfile)} key={value}><span>{label}</span><small>Профиль сохраняется в методологии</small></button>)}</div>
        )}
        {step === 7 && (
          <div className="model-grid routing-profile-grid">
            {routingProfiles.map(([value, title, description, icon]) => {
              if (!["FAST", "BALANCED", "HIGH_QUALITY"].includes(value)) return null;
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
        {step === 8 && (
          <div className="review-card">
            <div>
              <span>Бренд</span>
              <b>{brand}</b>
            </div>
            <div>
              <span>Регион</span>
              <b>{researchRegions.find(([value]) => value === region)?.[1] ?? region}</b>
            </div>
            <div>
              <span>Язык</span>
              <b>{language.toUpperCase()}</b>
            </div>
            <div>
              <span>Режим</span>
              <b>{routingProfiles.find(([value]) => value === profile)?.[1]}</b>
            </div>
            <div><span>Охват</span><b>{scope}</b></div>
            <div><span>Профиль исследования</span><b>{researchProfile}</b></div>
            <p>{review?.prompt}</p>
            <div><span>Выбранные модели</span><b>{review?.selected_models?.join(", ") || review?.provider_models?.join(", ") || "Router не вернул план"}</b></div>
            <div><span>Покупательских запросов</span><b>{customQueries.length}</b></div>
            <div><span>Всего проверок</span><b>{customQueries.length * Math.max(scopedModels().length, 1)}</b></div>
            <div><span>Оценка времени</span><b>{review?.estimated_time_ms ? `${review.estimated_time_ms} ms` : "Не рассчитана"}</b></div>
            <div><span>Оценка стоимости</span><b>{review?.estimated_cost_usd != null ? `$${review.estimated_cost_usd.toFixed(6)}` : "Не рассчитана"}</b></div>
            {customQueries.length ? <details open><summary>Проверить и изменить вопросы покупателей</summary><p className="muted">Матрица: 70% естественных запросов без бренда, 20% сравнений и 10% контрольных брендовых вопросов.</p>{customQueries.map((query, index) => { const scenario = review?.query_catalog[index]; return <div className="query-editor" key={`${index}-${query.slice(0, 24)}`}><small>{scenario?.brand_mode === "branded" ? "БРЕНДОВЫЙ КОНТРОЛЬ" : scenario?.brand_mode === "comparative" ? "СРАВНЕНИЕ" : "ЕСТЕСТВЕННЫЙ СПРОС"} · {scenario?.rationale ?? "Пользовательский запрос"}</small><textarea aria-label={`Запрос ${index + 1}`} value={query} onChange={(event) => setCustomQueries((items) => items.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /><button type="button" onClick={() => setCustomQueries((items) => items.filter((_, itemIndex) => itemIndex !== index))}>Удалить</button></div>; })}<button type="button" onClick={() => setCustomQueries((items) => [...items, ""])}>Добавить свой вопрос</button></details> : null}
          </div>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        <div className="wizard-actions">
          {step < 8 ? (
            <button
              onClick={next}
              disabled={busy || !brand || (step === 4 && selectedModels.length === 0) || (step === 7 && scopedModels().length === 0)}
            >
              {busy ? "Проверяем…" : step === 7 ? "Проверить" : "Продолжить"} →
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
  const laboratory = result.laboratory;
  const previousPoint = visibilityMetric?.points.at(-2);
  const currentPoint = visibilityMetric?.points.at(-1);
  const evidenceResearch = (report.research ?? result.research) as ResearchItem;
  const visibilityEvidence = metricEvidence("visibility_score", report, evidenceResearch);
  const successfulResponses = report.explainability?.sample_scope?.successful_response_count ?? responses.filter((item) => !item.error_type).length;
  const recommendedResponses = report.explainability?.responses.filter((item) => item.recommendation_ids.length > 0).length ?? 0;
  const citedResponses = report.explainability?.responses.filter((item) => item.citation_ids.length > 0).length ?? 0;
  const planFor = (recommendation: NonNullable<ReportShape["recommendations"]>[number]) => result.actionPlan?.items.find((item) => item.recommendation.metric === recommendation.metric);
  const simulationFor = (recommendation: NonNullable<ReportShape["recommendations"]>[number]) => result.simulation?.simulations.find((item) => item.metric === recommendation.metric);
  const [selectedActions, setSelectedActions] = useState<number[]>([]);
  const [publicationUrl, setPublicationUrl] = useState("");
  const [publicationTitle, setPublicationTitle] = useState("");
  const [publicationStatus, setPublicationStatus] = useState("");
  const [publicationTargetQueries, setPublicationTargetQueries] = useState<string[]>([]);
  const selectedForecasts = result.simulation?.simulations.filter((item) => selectedActions.includes(item.recommendation_id)) ?? [];
  const simulatedVisibility = Math.min(100, visibility + selectedForecasts.reduce((sum, item) => sum + item.predicted_delta, 0));
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
          <p>AI-видимость бренда составляет {visibility.toFixed(1)} из 100 в исследованной выборке. Главная точка роста — «{weakest.label}» ({weakest.value.toFixed(1)}). Это не оценка видимости во всех ИИ.</p>
        </div>
        <div className="report-score">
          <span>AI-видимость</span>
          <strong>{visibility.toFixed(1)}</strong>
          <em className={latestDelta == null ? "" : latestDelta >= 0 ? "good" : "critical"}>{latestDelta == null ? "Нет сравнения" : `${latestDelta >= 0 ? "↑" : "↓"} ${Math.abs(latestDelta).toFixed(1)}%`}</em>
        </div>
      </section>
      <section className="report-plain-summary" aria-label="Краткий вывод"><article><span>Что означает {visibility.toFixed(1)}</span><h2>{visibility >= 75 ? "Бренд заметен в этой выборке, но результат не универсален" : visibility >= 50 ? "Бренд упоминается, но не всегда становится рекомендацией" : "Бренд редко появляется в исследованных ответах"}</h2><p>Проверено {successfulResponses} успешных ответов по {report.explainability?.sample_scope?.query_count ?? report.query_catalog?.length ?? 0} запросам и {models.length} моделям. Оценка относится только к этой матрице.</p></article><article><span>Главное ограничение</span><h2>{weakest.label}: {weakest.value.toFixed(1)} из 100</h2><p>{weakest.label === "Цитирование" ? `Ссылки найдены в ${citedResponses} из ${successfulResponses} ответов. Без внешних источников ИИ не подтверждает выводы о бренде.` : weakest.label === "Рекомендации" ? `Бренд рекомендован в ${recommendedResponses} из ${successfulResponses} ответов. Простого упоминания недостаточно.` : "Подробное основание и ответы перечислены ниже."}</p></article><article><span>Что делать сначала</span><h2>Открыть раздел «Где публиковаться»</h2><p>Там показаны найденные источники, дефицитные запросы, конкретный материал и способ повторной проверки результата.</p><a href="#actions">Перейти к плану действий ↓</a></article></section>
      <nav className="report-nav" aria-label="Разделы отчёта"><a href="#summary">Сводка</a><a href="#demand-map">Запросы</a><a href="#patterns">Закономерности</a><a href="#models">Модели</a><a href="#entities">Сущности</a><a href="#sources">Источники</a><a href="#actions">Где публиковаться</a></nav>
      <section id="summary" className="panel report-proof"><div><span>Как сформирована оценка</span><strong>{visibility.toFixed(1)}</strong></div><dl><div><dt>Запросов</dt><dd>{report.explainability?.sample_scope?.query_count ?? report.query_catalog?.length ?? 0}</dd></div><div><dt>Моделей</dt><dd>{models.length}</dd></div><div><dt>Ответов</dt><dd>{responses.length}</dd></div><div><dt>Успешных</dt><dd>{report.explainability?.sample_scope?.successful_response_count ?? responses.length}</dd></div><div><dt>Исследование</dt><dd>#{result.research.id}</dd></div><div><dt>Алгоритм</dt><dd>{String(score.version ?? "не указан")}</dd></div></dl><p className="method-note">{report.explainability?.sample_scope?.limitation ?? "Результат относится только к исследованной выборке и не означает видимость во всех ИИ."}</p><details><summary>Показать расчёт</summary>{visibilityEvidence.lines.map((line) => <p key={line}>{line}</p>)}<code>{visibilityEvidence.formula}</code></details></section>
      <section id="demand-map" className="panel research-lab-section"><span className="section-label">КАРТА СПРОСА</span><h2>По каким запросам проверялся бренд</h2>{report.query_catalog?.length ? report.query_catalog.map((item) => <details className="evidence-details" key={item.id}><summary>{item.cluster} · {item.intent}</summary><p>{item.text}</p></details>) : <p className="empty-state">Для старого исследования карта смежных запросов не сохранена.</p>}</section>
      <section id="patterns" className="panel research-lab-section"><span className="section-label">НАБЛЮДАЕМЫЕ ЗАКОНОМЕРНОСТИ</span><h2>Где бренд уступает конкурентам</h2><p>Бренд не обнаружен в {report.research_patterns?.deficit_queries.length ?? 0} ответах из {report.research_patterns?.sample.responses ?? responses.length}.</p>{report.research_patterns?.deficit_queries.slice(0, 12).map((item) => <details className="evidence-details" key={item.response_id}><summary>{item.cluster} · {item.provider}/{item.model}</summary><p><b>Запрос:</b> {item.query}</p><p><b>Названы вместо бренда:</b> {item.competitors.join(", ") || "конкуренты не извлечены"}</p><p><b>Источники ответа:</b> {item.sources.join(", ") || "не указаны"}</p></details>)}<h3>Чаще встречающиеся конкуренты</h3>{report.research_patterns?.competitors.length ? report.research_patterns.competitors.map((item) => <p key={item.name}>{item.name} — {item.response_count} ответов</p>) : <p className="empty-state">Повторяющиеся конкуренты не извлечены.</p>}</section>
      <section className="panel research-lab-section"><span className="section-label">КОНКУРЕНТНОЕ ВЛИЯНИЕ</span><h2>Почему конкуренты могут быть заметнее</h2><p>{report.competitive_influence?.verification ?? "Для вывода нужны профили конкурентов и повторное измерение."}</p>{report.competitive_influence?.competitors.map((item) => <details className="evidence-details" key={item.competitor}><summary>{item.competitor} · назван в {item.response_count} ответах</summary>{item.matched_products.length ? item.matched_products.map((match) => <p key={`${match.target_product}-${match.competitor_product}`}><b>{match.target_product}</b> ↔ {match.competitor_product}; сходство характеристик {Math.round(match.feature_similarity * 100)}%; цена {String(match.target_price ?? "нет данных")} / {String(match.competitor_price ?? "нет данных")} {match.currency ?? ""}</p>) : <p>Сопоставимые товары не подтверждены.</p>}</details>)}{report.competitive_influence?.source_influence.map((item) => <p key={item.resource}><b>{item.resource}</b> — встречается в {item.response_count} ответах. {item.explanation}</p>)}</section>
      <section className="panel research-lab-section"><span className="section-label">ПОЧЕМУ ПОЛУЧИЛИСЬ ТАКИЕ ОЦЕНКИ</span><h2>Наблюдаемые причины по каждой метрике</h2>{laboratory?.provenance?.metric_explanations ? Object.entries(laboratory.provenance.metric_explanations).map(([key, explanation]) => <details className="evidence-details" key={key}><summary>{metricNames[key] ?? key} · {valueOf(score, key).toFixed(1)}</summary><p>{explanation.observed}</p><p><b>Подтверждают:</b> {explanation.positive_models.length ? explanation.positive_models.join(", ") : "ни одна модель"}</p><p><b>Дефицит сигнала:</b> {explanation.deficit_models.length ? explanation.deficit_models.join(", ") : "не обнаружен"}</p>{explanation.unknown_causes ? <p className="method-note">{explanation.unknown_causes}</p> : null}</details>) : <p className="empty-state">Детализация появится после обработки ответов исследования.</p>}</section>
      <section className="explainability-stack" aria-label="Первичные доказательства">
        <article className="panel"><span className="section-label">МЕТОДОЛОГИЯ · v{report.explainability?.methodology_version ?? score.version ?? "—"}</span><h2>Расчёт каждой метрики</h2>{report.explainability ? Object.entries(report.explainability.metrics).map(([key, metric]) => <details className="evidence-details" key={key}><summary>{metricNames[key] ?? key} · {metric.status ? "не рассчитывается" : valueOf(score, key).toFixed(1)}</summary>{metric.status ? <p>Эта метрика не входит в production Scoring v1.0 и не влияет на AI-видимость.</p> : <><p><b>Формула:</b> {metric.formula}</p><p><b>Нормализация:</b> {metric.normalization}</p><p><b>Вес:</b> {metric.weight == null ? "не применяется" : `${metric.weight * 100}%`}</p><pre>{JSON.stringify(metric.inputs, null, 2)}</pre></>}</details>) : <p className="empty-state">Для старого исследования методология не сохранена в report payload.</p>}</article>
        <article className="panel"><span className="section-label">КАТАЛОГ ЗАПРОСОВ</span><h2>На основании каких запросов рассчитан рейтинг</h2>{report.explainability?.prompts.length ? report.explainability.prompts.map((prompt) => <details className="evidence-details" key={prompt.uuid}><summary>{prompt.provider}/{prompt.model} · ответ #{prompt.response_id}</summary><p><b>UUID:</b> {prompt.uuid}</p><p><b>Язык:</b> {String(prompt.language ?? "не записан")} · <b>Страна:</b> {String(prompt.country ?? "не записана")}</p><pre className="raw-evidence">{prompt.text || "Текст запроса не был записан"}</pre></details>) : <p className="empty-state">Запросы не были записаны для этого исследования.</p>}</article>
        <article className="panel"><span className="section-label">ИСХОДНЫЕ ОТВЕТЫ МОДЕЛЕЙ</span><h2>Ответы без сокращений</h2>{report.explainability?.responses.length ? report.explainability.responses.map((response) => <details className="evidence-details" key={response.response_id}><summary>{response.provider}/{response.model} · {response.tokens} токенов · {response.latency_ms ?? "—"} ms</summary><p>Стоимость ${Number(response.cost).toFixed(6)} · завершён {new Date(response.finished_at).toLocaleString("ru-RU")}</p>{response.error_type ? <div className="error">{response.error_type}: {response.error_message}</div> : null}<p>Сущности: {response.entity_ids.length} · источники: {response.citation_ids.length} · рекомендации: {response.recommendation_ids.length}</p><h3>Исходный ответ</h3><pre className="raw-evidence">{JSON.stringify(response.raw_response, null, 2)}</pre><h3>Нормализованный ответ</h3><pre className="raw-evidence">{JSON.stringify(response.normalized_response, null, 2)}</pre></details>) : <p className="empty-state">Ответы моделей отсутствуют.</p>}</article>
        <article className="panel"><span className="section-label">АНАЛИЗ ЦИТИРОВАНИЯ</span><h2>Источники по моделям и доменам</h2>{responses.map((response) => { const citations = report.explainability?.citations.filter((item) => item.response_id === response.id) ?? []; return <div className="citation-model-row" key={response.id}><b>{response.provider}/{response.model}</b><span>{citations.length ? `${citations.length} источников: ${[...new Set(citations.map((item) => item.domain ?? item.source ?? "без домена"))].join(", ")}` : "внешние источники не обнаружены"}</span></div>; })}</article>
      </section>
      <section id="models" className="panel research-lab-section">
        <span className="section-label">ИССЛЕДОВАНИЕ МОДЕЛЕЙ</span>
        <h2>Вклад наблюдаемых сигналов</h2>
        <p>Scoring v1.0 считает общий рейтинг по ответам. Отдельный AI Visibility для модели не рассчитывается — ниже показан её точный вклад в числители агрегатных метрик.</p>
        {laboratory?.models?.length ? laboratory.models.map((item) => <details className="evidence-details" key={item.response_id}><summary>{item.provider}/{item.model} · ответ #{item.response_id}</summary><dl className="lab-facts"><div><dt>Упоминание</dt><dd>{item.signals.mentioned ? "да" : "нет"}</dd></div><div><dt>Рекомендация</dt><dd>{item.signals.recommended ? "да" : "нет"}</dd></div><div><dt>Цитаты</dt><dd>{item.signals.citation_count}</dd></div><div><dt>Язык / регион</dt><dd>{String(item.language ?? "не записан")} / {String(item.region ?? "не записан")}</dd></div><div><dt>Latency</dt><dd>{item.latency_ms ?? "—"} ms</dd></div><div><dt>Токены / стоимость</dt><dd>{item.tokens} / ${Number(item.cost).toFixed(6)}</dd></div></dl><h3>Prompt</h3><pre className="raw-evidence">{item.prompt}</pre><h3>Ответ модели</h3><pre className="raw-evidence">{item.content}</pre><p>Извлечено сущностей: {item.entities?.length ?? 0} · источников: {item.citations?.length ?? 0}</p></details>) : <p className="empty-state">Сохранённые ответы моделей отсутствуют.</p>}
      </section>
      <section id="entities" className="panel research-lab-section">
        <span className="section-label">КАТАЛОГ СУЩНОСТЕЙ</span><h2>Где обнаружена каждая сущность</h2>
        {laboratory?.entities?.length ? laboratory.entities.map((entity) => <details className="evidence-details" key={`${entity.type}:${entity.canonical_name}`}><summary>{entity.canonical_name} · {entity.type} · {entity.occurrences.length} наблюдений</summary><p><b>Алиасы:</b> {entity.aliases.join(", ") || "не записаны"}</p><p><b>Источники:</b> {entity.source_ids.length ? entity.source_ids.map((id) => `#${id}`).join(", ") : "не связаны"}</p><p><b>Knowledge Graph ID:</b> {entity.knowledge_graph_ids.join(", ") || "не назначен"}</p>{entity.occurrences.map((occurrence) => <p key={`${occurrence.response_id}:${occurrence.provider}`}>{occurrence.provider}/{occurrence.model} · ответ #{occurrence.response_id} · confidence {occurrence.confidence.toFixed(2)}</p>)}</details>) : <p className="empty-state">Сущности не были извлечены.</p>}
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
          {laboratory?.sources?.map((source) => <details className="evidence-details" key={source.identity}><summary>{source.domain ?? source.title ?? source.identity} · {source.citation_count} цитирований</summary><p><b>Модели:</b> {source.providers.join(", ")} · {source.models.join(", ")}</p><p><b>Вклад до ограничения 100:</b> {source.citation_score_points_before_cap.toFixed(2)} пункта Citation Score</p><p><b>Domain Authority:</b> не рассчитывается в Scoring v1.0; выдуманное значение не подставляется.</p></details>)}
        </article>
      </section>
      <section id="graph" className="panel report-graph"><span className="section-label">ГРАФ ЗНАНИЙ</span><h2>{graph?.node_count ?? 0} узлов · {graph?.edge_count ?? 0} связей</h2>{(graph?.edge_count ?? 0) > 0 ? <p>Связи построены из извлечённых сущностей и доказательств текущего исследования. Подробности доступны в разделе «Граф знаний».</p> : <p className="empty-state"><b>Связи не найдены.</b> Извлечённых сущностей недостаточно либо ответы не содержат подтверждённых отношений между ними.</p>}</section>
      <section id="timeline" className="panel research-lab-section"><span className="section-label">ВОСПРОИЗВОДИМАЯ ХРОНОЛОГИЯ</span><h2>События по реальным временным меткам</h2>{laboratory?.timeline?.length ? <ol className="lab-timeline">{laboratory.timeline.map((event) => <li key={`${event.type}:${event.id}:${event.at}`}><time>{new Date(event.at).toLocaleString("ru-RU")}</time><b>{event.type}</b><span>{event.label}</span></li>)}</ol> : <p className="empty-state">Хронология недоступна для этого исследования.</p>}<h3>Публикации и первое наблюдение</h3>{laboratory?.publications?.length ? laboratory.publications.map((publication) => <details className="evidence-details" key={publication.id}><summary>{publication.title} · опубликовано {new Date(publication.published_at).toLocaleDateString("ru-RU")}</summary><a href={publication.url} target="_blank" rel="noreferrer">Открыть публикацию</a>{publication.observations.length ? publication.observations.map((observation) => <p key={observation.id}>{observation.provider}/{observation.model}: впервые подтверждено {new Date(observation.first_observed_at).toLocaleString("ru-RU")} — {observation.evidence_excerpt}</p>) : <p>Ни одна модель пока не имеет сохранённого факта наблюдения. Это не доказывает отсутствие индексации.</p>}</details>) : <p className="empty-state">Публикационные вмешательства для объекта не зарегистрированы.</p>}<p className="method-note">Изменения до/после являются наблюдаемой корреляцией. Причинное влияние публикации не заявляется без контролируемого эксперимента.</p></section>
      <section className="panel research-lab-section"><span className="section-label">ОБУЧЕНИЕ НА ПУБЛИКАЦИЯХ</span><h2>Что влияет на рекомендации ИИ</h2><p>{report.publication_learning?.explanation ?? "Для обучения нужны публикации и повторные исследования с одинаковой матрицей."}</p>
        <div className="publication-form"><h3>Зарегистрировать новый материал</h3><p>Укажите запросы, на которые должен повлиять материал. Остальные запросы останутся контрольной группой и помогут отделить эффект публикации от общего изменения модели.</p><input aria-label="Название публикации" placeholder="Название материала" value={publicationTitle} onChange={(event) => setPublicationTitle(event.target.value)} /><input aria-label="URL публикации" placeholder="https://..." value={publicationUrl} onChange={(event) => setPublicationUrl(event.target.value)} /><fieldset className="publication-query-picker"><legend>Целевые запросы публикации</legend>{report.query_catalog?.map((item) => <label key={item.id}><input type="checkbox" checked={publicationTargetQueries.includes(item.text)} onChange={() => setPublicationTargetQueries((current) => current.includes(item.text) ? current.filter((query) => query !== item.text) : [...current, item.text])} /><span>{item.text}</span></label>)}</fieldset><p className="method-note">Целевых: {publicationTargetQueries.length}. Контрольных: {Math.max(0, (report.query_catalog?.length ?? 0) - publicationTargetQueries.length)}.</p><button type="button" disabled={!publicationTitle.trim() || !publicationUrl.trim() || !publicationTargetQueries.length || ((report.query_catalog?.length ?? 0) > 1 && publicationTargetQueries.length === report.query_catalog?.length)} onClick={async () => { try { const entityId = String((report.research as Record<string, unknown> | undefined)?.entity_id ?? ""); if (!entityId) throw new Error("У исследования отсутствует entity_id"); const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(publicationUrl.trim())); const contentHash = Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join(""); await api.createResearchPublication({ entity_id: entityId, research_id: result.research.id, url: publicationUrl.trim(), content_hash: contentHash, title: publicationTitle.trim(), channel: "EARNED", content_type: "ARTICLE", target_queries: publicationTargetQueries, published_at: new Date().toISOString() }); setPublicationStatus("Публикация сохранена. Повторите исследование с той же матрицей: система сравнит целевые и контрольные запросы."); setPublicationTitle(""); setPublicationUrl(""); setPublicationTargetQueries([]); } catch (error) { setPublicationStatus(error instanceof Error ? error.message : "Не удалось сохранить публикацию"); } }}>Сохранить эксперимент</button>{publicationStatus ? <p>{publicationStatus}</p> : null}</div>
        {report.publication_learning?.influence_estimates.length ? report.publication_learning.influence_estimates.slice(0, 12).map((item) => <article className="influence-estimate" key={item.id}><h3>{item.resource_domain} · {metricNames[item.metric] ?? item.metric}</h3><p>{item.provider === "ALL" ? "Все модели" : `${item.provider}/${item.model}`} · {item.channel} · {item.content_type}</p><div className="action-meta"><div><span>Наблюдаемый эффект</span><b>{item.expected_delta >= 0 ? "+" : ""}{item.expected_delta.toFixed(1)}</b></div><div><span>Диапазон</span><b>{item.confidence_min.toFixed(1)}…{item.confidence_max.toFixed(1)}</b></div><div><span>Наблюдений</span><b>{item.sample_size}</b></div><div><span>С контролем</span><b>{item.controlled_experiments}</b></div><div><span>Уверенность</span><b>{Math.round(item.confidence_score * 100)}%</b></div></div><small>{item.evidence_grade} · {item.effect_method === "QUERY_LEVEL_DIFFERENCE_IN_DIFFERENCES_V1" ? "эффект скорректирован по контрольным запросам" : "простое сравнение до/после"}; результат не является гарантией причинного влияния.</small></article>) : <p className="empty-state">Пока недостаточно сопоставимых исследований. После публикации повторите тот же набор запросов и моделей.</p>}
      </section>
      <section id="actions" className="plan-section">
        <div className="section-head">
          <div>
            <span className="eyebrow">ПЛАН ДЕЙСТВИЙ</span>
            <h2>Где и что публиковать</h2>
          </div>
        </div>
        {report.geo_opportunities?.length ? report.geo_opportunities.map((item) => <article className="action-card" key={item.id}><div className="action-top"><span className="priority">{item.channel}</span><span>{metricNames[item.affected_metric] ?? item.affected_metric}</span></div><h3>{item.resource}</h3><p><b>Почему:</b> {item.reason}</p><p><b>Что подготовить:</b> {item.deliverable}</p><div className="action-meta"><div><span>Ожидаемый диапазон</span><b>+{item.expected_effect_range[0]}…{item.expected_effect_range[1]}</b></div><div><span>Уверенность</span><b>{Math.round(item.confidence * 100)}%</b></div><div><span>Срок</span><b>{item.estimated_days} дней</b></div></div><p><b>Проверка:</b> {item.verification}</p><small>{item.causality_notice}</small></article>) : report.recommendations?.length ? report.recommendations.map((recommendation, index) => <RecommendationCard recommendation={recommendation} plan={planFor(recommendation)} simulation={simulationFor(recommendation)} key={`${recommendation.explanation}-${index}`} />) : <div className="empty-state">Недостаточно данных для доказательного плана публикаций.</div>}
      </section>
      <section className="panel research-lab-section"><span className="section-label">СИМУЛЯТОР ДЕЙСТВИЙ</span><h2>Прогноз при выполнении выбранных рекомендаций</h2><p>Детерминированный прогноз версии {result.simulation?.model_version ?? "не рассчитан"}. Это ожидаемый эффект, а не обещание результата.</p>{result.simulation?.simulations.length ? <><div className="simulator-list">{result.simulation.simulations.map((item) => { const recommendation = report.recommendations?.find((candidate) => candidate.id === item.recommendation_id); return <label key={item.recommendation_id}><input type="checkbox" checked={selectedActions.includes(item.recommendation_id)} onChange={() => setSelectedActions((current) => current.includes(item.recommendation_id) ? current.filter((id) => id !== item.recommendation_id) : [...current, item.recommendation_id])} /><span>{recommendation?.explanation ?? `Рекомендация #${item.recommendation_id}`}</span><b>прогноз +{item.predicted_delta.toFixed(1)}</b></label>; })}</div><div className="simulation-total"><span>AI-видимость</span><strong>{visibility.toFixed(1)} → {simulatedVisibility.toFixed(1)}</strong><small>Выбрано действий: {selectedActions.length}</small></div></> : <p className="empty-state">Прогнозы не рассчитаны. Сначала сформируйте рекомендации и симуляцию.</p>}</section>
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
    const [data, tasks, actionPlan, simulation, laboratory] = await Promise.all([
      api.finalReport(research.id), api.researchTasks(research.id).catch(() => []),
      api.actionPlan(research.id).catch(() => undefined), api.simulation(research.id).catch(() => undefined),
      api.researchLaboratory(research.id).catch(() => undefined),
    ]);
    setReport({ research, report_url: `/research/${research.id}/final-report`, report: data, tasks, actionPlan, simulation, laboratory });
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
        <RecommendationsScreen key="recommendations" onNewResearch={() => navigate("wizard")} />
      ) : screen === "graph" ? (
        <GraphScreen />
      ) : screen === "geo" ? (
        <GeoOpportunitiesScreen />
      ) : screen === "competitors" ? (
        <CompetitorsScreen />
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
      ) : screen === "expert" ? (
        <ExpertGuideScreen onNavigate={navigate} />
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
