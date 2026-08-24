export type TokenPair = { access_token: string; refresh_token: string };
export type AuthProfile = { id: number; display_name: string; email: string; roles: string[] };
export type ModelSelection = { provider: string; model: string };
export type WizardPayload = {
  brand: string;
  website_url: string;
  brand_profile?: BrandProfile;
  competitors?: Array<{ name: string; website_url?: string }>;
  models?: ModelSelection[];
  routing_profile: "FAST" | "BALANCED" | "HIGH_QUALITY" | "FREE" | "PRIVATE" | "ENTERPRISE";
  languages: string[];
  regions: string[];
  prompt_code: string;
  research_template_code: string;
  research_scope?: "ALL" | "SELECTED" | "RUSSIAN" | "COMMERCIAL" | "FREE" | "CONSENSUS" | "COMPARE";
  research_profile?: "GEO" | "ECOMMERCE" | "MEDICAL" | "BEAUTY" | "ENTERPRISE" | "UNIVERSAL";
  custom_queries?: string[];
};
export type BrandProfile = { version: string; brand: string; website_url: string; pages_analyzed: number; evidence_urls: string[]; description: string; categories: string[]; products: Array<{ name: string; category?: string; description?: string; price?: string | number; currency?: string; url?: string; evidence_url?: string }>; attributes: string[]; confidence: number; limitations: string[] };
export type RouterModel = { id: string; provider: string; display_name: string; version: string; status: string; tier: string; capabilities: string[]; availability: number; pricing: { input_per_million: number; output_per_million: number } };
export type WizardReview = {
  valid: boolean;
  title: string;
  prompt: string;
  provider_models: string[];
  languages: string[];
  regions: string[];
  pipeline: string[];
  estimated_cost_usd: number;
  estimated_time_ms: number;
  selected_models: string[];
  query_catalog: Array<{ id: string; cluster: string; intent: string; text: string; buyer_stage?: string; brand_mode?: string; rationale?: string }>;
  task_count: number;
  brand_profile: BrandProfile;
  competitor_profiles: BrandProfile[];
};
export type ReportResult = {
  research: { id: number; title: string; status: string };
  report_url: string;
  report: Record<string, unknown>;
  tasks?: ResearchTaskItem[];
  executions?: ExecutionItem[];
  actionPlan?: ActionPlan;
  simulation?: SimulationResult;
  laboratory?: ResearchLaboratory;
};
export type ResearchLaboratory = {
  provenance: { metric_explanations?: Record<string, { observed: string; positive_models: string[]; deficit_models: string[]; cause_status: string; unknown_causes?: string; source_count?: number }> } & Record<string, unknown>;
  models: Array<Record<string, unknown> & {
    response_id: number; provider: string; model: string; prompt: string;
    content: string; language?: string | string[]; region?: string | string[];
    tokens: number; cost: number; latency_ms?: number; finished_at: string;
    signals: { mentioned: boolean; recommended: boolean; citation_count: number; visibility_score: null; visibility_status: string };
    entities: Array<Record<string, unknown>>; citations: Array<Record<string, unknown>>;
  }>;
  sources: Array<{ identity: string; url?: string; domain?: string; title?: string; citation_count: number; providers: string[]; models: string[]; citation_score_points_before_cap: number; authority: null; authority_status: string }>;
  entities: Array<{ canonical_name: string; type: string; aliases: string[]; occurrences: Array<{ response_id: number; provider: string; model: string; confidence: number }>; source_ids: number[]; knowledge_graph_ids: string[] }>;
  graph: { status: string; reason?: string; snapshot_id?: number; version?: string; nodes: Array<Record<string, unknown>>; edges: Array<Record<string, unknown> & { id: number; source?: string; target?: string; type: string; confidence: number; evidence_status: string }> };
  timeline: Array<{ type: string; at: string; id: number; label: string }>;
  publications: Array<{ id: number; title: string; url: string; channel: string; content_type: string; topic?: string; target_queries: string[]; published_at: string; observations: Array<{ id: number; provider: string; model: string; first_observed_at: string; evidence_excerpt: string }> }>;
};
export type PublicationCreatePayload = { entity_id: string; research_id?: number; url: string; content_hash: string; title: string; channel: string; content_type: string; topic?: string; target_queries: string[]; published_at: string };
export type ActionPlanItem = { recommendation: RecommendationItem; template?: { title: string; description: string; steps: string[]; expected_result: string; estimated_time: string; version: string }; steps: string[]; expected_effect: string; estimated_time?: string };
export type ActionPlan = { research_id: number; engine_version: string; generated_at: string; items: ActionPlanItem[] };
export type SimulationItem = { recommendation_id: number; metric: string; current_metric: number; expected_metric_change: number; predicted_visibility: number; predicted_delta: number; confidence_min: number; confidence_expected: number; confidence_max: number; estimated_duration_days: number; model_version: string };
export type SimulationResult = { research_id: number; model_version: string; simulated_at: string; simulations: SimulationItem[] };
export type ResearchItem = { id: number; title: string; status: string; progress_percent?: number; total_tasks?: number; completed_tasks?: number; failed_tasks?: number; created_at?: string; updated_at?: string; metadata?: Record<string, unknown> };
export type ResearchTaskItem = { id: number; research_id: number; status: string; provider?: string; model?: string; execution_id?: number; created_at: string; updated_at: string; error?: string };
export type ExecutionItem = { id: number; state: string; started_at?: string; finished_at?: string; duration_ms?: number; attempt_count: number; error?: string };
export type WorkspaceProjectItem = { id: number; name: string; description: string; research_count: number };
export type CompetitorItem = { id: number; project_id: number; name: string; domains: string[]; brands: string[]; notes: string; active: boolean };
export type CompetitorSnapshot = {
  snapshot_date: string; research_count: number; response_count: number;
  mention_count: number; recommendation_count: number; citation_count: number;
  source_count: number; observed_visibility_score: number; algorithm_version: string;
};
export type CompetitorPublication = {
  url: string; domain: string; title?: string; observation_count: number;
  provider_count: number; research_count: number; mention_observations: number;
  recommendation_observations: number; significance_score: number;
  significance_label: string; first_seen_at: string; last_seen_at: string;
  evidence_level: string; explanation: string;
};
export type CompetitorAnalytics = {
  competitor_id: number; name: string; domains: string[]; active: boolean;
  latest_visibility_score?: number; visibility_delta?: number;
  snapshots: CompetitorSnapshot[]; publications: CompetitorPublication[];
};
export type CompetitorDashboard = {
  project_id: number; monitoring_enabled: boolean; next_run_at?: string;
  methodology: string; limitation: string; competitors: CompetitorAnalytics[];
};
export type SocialPost = { id: number; external_post_id: string; url: string; title?: string; content: string; published_at: string; views?: number; likes?: number; comments?: number; shares?: number; engagement_rate?: number; significance_score: number };
export type SocialSource = { id: number; competitor_id: number; platform: "TELEGRAM" | "INSTAGRAM" | "YOUTUBE" | "VK"; profile_url: string; external_id: string; configured: boolean; active: boolean; status: string; last_scanned_at?: string; next_scan_at?: string; last_error?: string; posts: SocialPost[] };
export type SocialDashboard = { competitor_id: number; sources: SocialSource[]; total_posts: number; limitation: string };
export type TelegramConnection = { configured: boolean; status: string; phone_hint?: string; last_connected_at?: string; last_error?: string };
export type GeoAuditCheck = { code: string; category: string; title: string; passed: boolean; points: number; max_points: number; evidence: string; recommendation?: string };
export type GeoSiteAudit = { id: number; project_id?: number; brand: string; website_url: string; final_url: string; score: number; grade: string; category_scores: Record<string, number>; checks: GeoAuditCheck[]; opportunities: Array<{ priority: string; problem: string; affected_metric: string; action: string; expected_effect: string; confidence: string; effort: string; verification: string }>; evidence: Record<string, unknown>; algorithm_version: string; limitation: string; created_at: string };
export type ReportCatalogItem = { research_id: number; title: string; status: string; visibility_score?: number; created_at: string };
export type RecommendationItem = { id: number; recommendation_type: string; priority: string; explanation: string; metric: string; metric_value: number; expected_effect: string };
export type GraphNode = { id: number; external_id: string; name: string; canonical_name: string; node_type: string; confidence: number; aliases: string[]; properties: Record<string, unknown> };
export type GraphEdge = { id: number; source_node_id: number; target_node_id: number; edge_type: string; confidence: number; properties: Record<string, unknown> };
export type GraphSnapshot = { id: number; structure_version: string; node_count: number; edge_count: number; build_metadata: Record<string, unknown>; created_at: string; nodes: GraphNode[]; edges: GraphEdge[] };
export type FeedbackItem = { id: number; title: string; feedback_type: string; priority: string; status: string; created_at: string };
export type ProviderItem = {
  id: string; display_name: string; capabilities: string[];
  pricing: Record<string, unknown>; context_window: number;
  availability: string; free_tier: boolean; priority: number;
  streaming: boolean; reasoning: boolean; vision: boolean;
};
export type SystemProviderItem = { model_id: string; provider: string; latency_ms: number; circuit_state: string; interface: { available?: boolean; mock?: boolean; checked_at?: string; models?: number | string[]; error?: string } };
export type ProviderConnection = {
  id: number; organization_id: number; provider: string; display_name: string;
  masked_key: string; status: string; free_only: boolean; paid_fallback: boolean;
  last_checked_at?: string; last_success_at?: string; last_error?: string; created_at: string;
};
export type ProviderConnectionTest = { provider: string; status: string; latency_ms: number; models: string[]; free_models: string[]; checked_at: string };
export type YandexWebmasterStatus = { connected: boolean; status: string; selected_host_id?: string; selected_host_url?: string; last_checked_at?: string; last_success_at?: string; last_error?: string };
export type YandexWebmasterHost = { host_id: string; ascii_host_url: string; unicode_host_url?: string; verified: boolean };
export type YandexIntelligence = {
  id: number; organization_id: number; host_id: string; host_url: string;
  status: string; evidence_status: string; algorithm_version: string; created_at: string;
  webmaster: { diagnostics?: { problems?: Record<string, { severity: string; state: string }> }; indexing?: { indicators?: Record<string, Array<{ date: string; value: number }>> }; external_links?: { count?: number; links?: Array<{ source_url: string; destination_url: string }> }; sitemaps?: { sitemaps?: Array<{ sitemap_url: string; errors_count: number; urls_count: number }> }; partial_errors?: Record<string, string> };
  yandex_ai: Array<{ research_id: number; response_id: number; query: string; brand: string; mentioned: boolean; recommended: boolean; citation_domains: string[]; observed_at: string }>;
  query_map: Array<{ query: string; url?: string; impressions?: number; clicks?: number; ctr?: number; position?: number; demand?: number; yandex_ai_checked: boolean; brand_mentioned?: boolean; evidence_status: string }>;
  opportunities: Array<{ priority: string; priority_score: number; query: string; problem: string; evidence: string; affected_metric: string; action: string; target_url?: string; expected_range: string; confidence: string; effort: string; duration: string; verification: string }>;
  limitations: string[];
};
export type AliceLearningDashboard = {
  status: string;
  brand?: string;
  observation_count: number;
  recommendation_count: number;
  baseline_probability?: number;
  model?: {
    id: number; status: string; model_type: string; sample_size: number;
    positive_samples: number; negative_samples: number; coefficients: Record<string, number>;
    validation: Record<string, number | string | null>; limitations: string[];
    algorithm_version: string; trained_at: string;
  };
  top_factors: Array<{
    feature?: string; coefficient?: number; direction?: string; evidence_level: string;
    resource_domain?: string; expected_delta?: number; confidence_score?: number;
    sample_size?: number; controlled_experiments?: number;
  }>;
  recommended_actions: Array<{
    feature: string; current_value: number; target_value: number;
    current_probability: number; predicted_probability: number; predicted_delta: number;
    action: string; evidence_level: string;
  }>;
  recent_predictions: Array<Record<string, unknown>>;
  limitations: string[];
};
export type AliceAutomationPlan = {
  id: number; organization_id: number; owner_user_id: number; template_research_id: number;
  brand: string; website_url: string; language: string; region: string;
  research_profile: string; routing_profile: string; models: ModelSelection[];
  repetitions: number; daily_query_limit: number; weekly_query_limit: number;
  daily_budget_usd: number; monthly_budget_usd: number; is_enabled: boolean;
  next_run_at: string; last_run_at?: string; created_at: string; updated_at: string;
};
export type AliceAutomationRun = {
  id: number; plan_id: number; query_set_id: number; run_kind: string; status: string;
  research_id?: number; task_count: number; estimated_cost_usd: number;
  actual_cost_usd?: number; result: Record<string, unknown>; error?: string;
  scheduled_for: string; started_at: string; finished_at?: string;
};
export type AliceAutomationDashboard = {
  plans: AliceAutomationPlan[]; latest_runs: AliceAutomationRun[];
  methodology: Record<string, string>;
};
export type GeoPlatform = {
  id: string; name: string; domain: string; platform_type: string; category: string;
  country: string; language: string; ai_engines: string[]; domain_trust?: number;
  topical_authority_score?: number; ai_citation_history?: number;
  allows_ai_crawlers?: boolean; in_knowledge_graph?: boolean;
  cost_per_placement?: number; evidence: Record<string, unknown>; active: boolean;
  created_at: string; updated_at: string;
};
export type FrozenPromptSet = {
  id: string; code: string; version: number; name: string; category: string;
  language: string; region: string; fingerprint: string; frozen: boolean;
  active: boolean; templates: Array<{ key: string; query_type: string; template: string }>;
  instances: Array<{ id: string; stable_key: string; text: string; query_type: string; position: number }>;
  created_at: string;
};
export type EisComponent = {
  value?: number; numerator: number; denominator: number;
  inputs: Record<string, number | boolean | null>; weights: Record<string, number>; exclusions: string[];
};
export type EisScore = {
  id: string; platform_id: string; ai_engine: string; eis_value?: number; priority?: string;
  components: Record<string, EisComponent>; evidence_status: string;
  methodology_version: string; weight_set_version: string; explanation: Record<string, unknown>;
  calculated_at: string;
};
export type EisPriorityResult = {
  items: Array<{ score: EisScore; cost_efficiency?: number }>;
  methodology_version: string; limitations: string[];
};
export type PublicationInfluenceEstimate = {
  id: number; resource_domain: string; channel: string; content_type: string;
  metric: string; provider: string; model: string; category: string;
  language: string; region: string; sample_size: number; expected_delta: number;
  confidence_min: number; confidence_max: number; confidence_score: number;
  evidence_grade: string; evidence_level: string; positive_experiments: number;
  negative_experiments: number; neutral_experiments: number;
  controlled_experiments: number; effect_method: string;
  last_observed_at?: string; limitations: string[]; algorithm_version: string;
};
export type RouterHistoryItem = { id: number; selected_models: string[]; latency_ms: number; estimated_cost_usd: number; error?: string | null; created_at: string };
export type ProductAnalyticsDashboard = {
  period: "HOURLY" | "DAILY" | "WEEKLY" | "MONTHLY";
  overview: Record<string, number>;
  users: Record<string, unknown>;
  organizations: Record<string, unknown>;
  sessions: Record<string, unknown>;
  research: Record<string, unknown>;
  reports: Record<string, unknown>;
  providers: Record<string, unknown>;
  feedback: Record<string, unknown>;
  errors: Record<string, unknown>;
  trends: Array<Record<string, number | string>>;
  cached: boolean;
};
export type NotificationItem = {
  id: number;
  event_type: string;
  category: string;
  priority: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
};
export type OrganizationItem = {
  id: number; name: string; slug: string; description: string; role: string;
  is_default: boolean; country?: string; timezone: string;
  limits: Record<string, number>; settings: Record<string, unknown>;
};
export type OrganizationMember = {
  id: number; user_id: number; role: string; is_default: boolean; joined_at: string;
};
export type WorkspaceSettings = { id: number; name: string; settings: Record<string, unknown> };
export type ApiKeyItem = { id: number; name: string; prefix: string; scopes: string[]; revoked_at?: string };
export type AdminUser = { user_id: number; email: string; display_name: string; status: string; is_active: boolean; research_count: number; last_seen_at?: string };
export type AdminFeedback = { id: number; title: string; feedback_type: string; priority: string; status: string; user_id: number; created_at: string };
export type AdminAudit = { id: number; actor_id: string; action: string; category: string; resource: string; created_at: string };

export class ApiClient {
  private token = sessionStorage.getItem("access_token") ?? undefined;
  private refreshPromise?: Promise<TokenPair>;

  setToken(token: string) {
    this.token = token;
    sessionStorage.setItem("access_token", token);
  }

  private saveTokens(tokens: TokenPair) {
    this.setToken(tokens.access_token);
    sessionStorage.setItem("refresh_token", tokens.refresh_token);
    return tokens;
  }

  private clearTokens() {
    this.token = undefined;
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
  }

  private async refreshAccessToken() {
    const refreshToken = sessionStorage.getItem("refresh_token");
    if (!refreshToken) throw new Error("Сессия истекла. Войдите снова.");
    if (!this.refreshPromise) {
      this.refreshPromise = fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).then(async (response) => {
        if (!response.ok) {
          this.clearTokens();
          throw new Error("Сессия истекла. Войдите снова.");
        }
        return this.saveTokens(await response.json() as TokenPair);
      }).finally(() => { this.refreshPromise = undefined; });
    }
    return this.refreshPromise;
  }

  private async request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
    let response = await fetch(`/api${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
        ...init.headers,
      },
    });
    if (response.status === 401 && retry && !path.startsWith("/auth/")) {
      await this.refreshAccessToken();
      response = await fetch(`/api${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
          ...init.headers,
        },
      });
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
    }
    return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
  }

  login(email: string, password: string) {
    return this.request<TokenPair>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }).then((tokens) => this.saveTokens(tokens));
  }
  restoreSession() {
    const refreshToken = sessionStorage.getItem("refresh_token");
    if (!refreshToken) return Promise.reject(new Error("No active session"));
    return this.request<TokenPair>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).then((tokens) => this.saveTokens(tokens));
  }
  me() { return this.request<AuthProfile>("/auth/me"); }
  workspace() { return this.request<WorkspaceSettings>("/workspace"); }
  updateWorkspace(settings: Record<string, unknown>) { return this.request<WorkspaceSettings>("/workspace", { method: "PATCH", body: JSON.stringify({ settings }) }); }
  apiKeys() { return this.request<ApiKeyItem[]>("/api-keys"); }
  adminUsers(search = "") { return this.request<AdminUser[]>(`/admin/beta/users${search ? `?search=${encodeURIComponent(search)}` : ""}`); }
  adminFeedback() { return this.request<AdminFeedback[]>("/admin/feedback"); }
  adminAudit() { return this.request<{ items: AdminAudit[]; total: number }>("/audit/events?page_size=20"); }
  adminReports() { return this.request<{ items: Array<{ research_id: number; title: string; status: string; visibility_score?: number }>; total: number }>("/reports?limit=20"); }
  adminJobs() { return this.request<Array<{ id: number; state: string; agent_id?: number; attempts: number }>>("/execution/history"); }
  systemHealth() { return this.request<Record<string, unknown>>("/system/health"); }
  systemProviders() { return this.request<{ providers: SystemProviderItem[] }>("/system/providers"); }
  systemCosts() { return this.request<Record<string, number>>("/system/costs"); }
  routerHistory(limit = 100) { return this.request<{ items: RouterHistoryItem[] }>(`/router/history?limit=${limit}`); }
  review(payload: WizardPayload) {
    return this.request<WizardReview>("/research/wizard/review", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
  run(payload: WizardPayload) {
    return this.request<ReportResult>("/research/wizard/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
  listResearch() { return this.request<ResearchItem[]>("/research"); }
  routerModels() { return this.request<{ items: RouterModel[]; total: number }>("/router/models?page_size=100&status=ACTIVE&capability=chat"); }
  researchTasks(researchId: number) { return this.request<ResearchTaskItem[]>(`/research-tasks?research_id=${researchId}`); }
  researchLaboratory(researchId: number) { return this.request<ResearchLaboratory>(`/research/${researchId}/laboratory`); }
  createResearchPublication(payload: PublicationCreatePayload) { return this.request("/research-publications", { method: "POST", body: JSON.stringify(payload) }); }
  execution(id: number) { return this.request<ExecutionItem>(`/execution/${id}`); }
  reports() { return this.request<{ items: ReportCatalogItem[]; total: number }>("/reports?limit=100"); }
  recommendations(researchId: number) { return this.request<{ recommendations: RecommendationItem[] }>(`/research/${researchId}/recommendations`); }
  actionPlan(researchId: number) { return this.request<ActionPlan>(`/research/${researchId}/action-plan`); }
  simulation(researchId: number) { return this.request<SimulationResult>(`/research/${researchId}/simulation`); }
  graph() { return this.request<GraphSnapshot>("/graph"); }
  workspaceProjects() { return this.request<WorkspaceProjectItem[]>("/workspace/projects"); }
  createWorkspaceProject(payload: { name: string; description?: string }) {
    return this.request<WorkspaceProjectItem>("/workspace/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
  projectCompetitors(projectId: number) { return this.request<CompetitorItem[]>(`/workspace/projects/${projectId}/competitors`); }
  createProjectCompetitor(projectId: number, payload: { name: string; domains: string[]; brands?: string[]; notes?: string }) {
    return this.request<CompetitorItem>(`/workspace/projects/${projectId}/competitors`, { method: "POST", body: JSON.stringify(payload) });
  }
  updateProjectCompetitor(projectId: number, competitorId: number, payload: Partial<CompetitorItem>) {
    return this.request<CompetitorItem>(`/workspace/projects/${projectId}/competitors/${competitorId}`, { method: "PATCH", body: JSON.stringify(payload) });
  }
  deleteProjectCompetitor(projectId: number, competitorId: number) {
    return this.request<void>(`/workspace/projects/${projectId}/competitors/${competitorId}`, { method: "DELETE" });
  }
  competitorDashboard(projectId: number) { return this.request<CompetitorDashboard>(`/competitor-intelligence/projects/${projectId}`); }
  refreshCompetitorDashboard(projectId: number) { return this.request<CompetitorDashboard>(`/competitor-intelligence/projects/${projectId}/refresh`, { method: "POST" }); }
  setCompetitorDailyMonitoring(projectId: number, enabled: boolean) {
    return this.request<CompetitorDashboard>(`/competitor-intelligence/projects/${projectId}/daily-monitoring`, { method: "PUT", body: JSON.stringify({ enabled }) });
  }
  competitorSocial(projectId: number, competitorId: number) { return this.request<SocialDashboard>(`/competitor-intelligence/projects/${projectId}/competitors/${competitorId}/social`); }
  addCompetitorSocial(projectId: number, competitorId: number, payload: { platform: string; profile_url: string; external_id: string; access_token?: string }) { return this.request<SocialSource>(`/competitor-intelligence/projects/${projectId}/competitors/${competitorId}/social`, { method: "POST", body: JSON.stringify(payload) }); }
  refreshCompetitorSocial(projectId: number, competitorId: number) { return this.request<SocialDashboard>(`/competitor-intelligence/projects/${projectId}/competitors/${competitorId}/social/refresh`, { method: "POST" }); }
  discoverCompetitorSocial(projectId: number, competitorId: number) { return this.request<SocialDashboard>(`/competitor-intelligence/projects/${projectId}/competitors/${competitorId}/social/discover`, { method: "POST" }); }
  deleteCompetitorSocial(projectId: number, competitorId: number, sourceId: number) { return this.request<void>(`/competitor-intelligence/projects/${projectId}/competitors/${competitorId}/social/${sourceId}`, { method: "DELETE" }); }
  telegramConnection() { return this.request<TelegramConnection>("/competitor-intelligence/telegram/connection"); }
  telegramSendCode(payload: { api_id: number; api_hash: string; phone_number: string; proxy?: { host: string; port: number; username?: string; password?: string } }) { return this.request<TelegramConnection>("/competitor-intelligence/telegram/connection/send-code", { method: "POST", body: JSON.stringify(payload) }); }
  telegramVerify(payload: { code: string; password?: string }) { return this.request<TelegramConnection>("/competitor-intelligence/telegram/connection/verify", { method: "POST", body: JSON.stringify(payload) }); }
  telegramDisconnect() { return this.request<void>("/competitor-intelligence/telegram/connection", { method: "DELETE" }); }
  searchCompetitorTelegram(projectId: number, competitorId: number, query?: string) { return this.request<SocialDashboard>(`/competitor-intelligence/projects/${projectId}/competitors/${competitorId}/telegram/search`, { method: "POST", body: JSON.stringify({ query: query?.trim() || null, limit: 50 }) }); }
  runGeoSiteAudit(payload: { brand: string; website_url: string; project_id?: number }) { return this.request<GeoSiteAudit>("/geo/site-audits", { method: "POST", body: JSON.stringify(payload) }); }
  geoSiteAudits(projectId?: number) { return this.request<GeoSiteAudit[]>(`/geo/site-audits${projectId ? `?project_id=${projectId}` : ""}`); }
  feedback() { return this.request<FeedbackItem[]>("/feedback"); }
  listProviders() { return this.request<ProviderItem[]>("/providers"); }
  providerConnections() { return this.request<ProviderConnection[]>("/provider-connections"); }
  connectProvider(apiKey: string, providerHint?: string, folderId?: string) { return this.request<ProviderConnection>("/provider-connections", { method: "POST", body: JSON.stringify({ api_key: apiKey, provider_hint: providerHint || null, folder_id: folderId || null, free_only: true }) }); }
  testProviderConnection(id: number) { return this.request<ProviderConnectionTest>(`/provider-connections/${id}/test`, { method: "POST" }); }
  yandexWebmasterStatus() { return this.request<YandexWebmasterStatus>("/integrations/yandex-webmaster/status"); }
  authorizeYandexWebmaster() { return this.request<{ authorization_url: string }>("/integrations/yandex-webmaster/authorize", { method: "POST" }); }
  yandexWebmasterHosts() { return this.request<YandexWebmasterHost[]>("/integrations/yandex-webmaster/hosts"); }
  selectYandexWebmasterHost(host_id: string, host_url: string) { return this.request<YandexWebmasterStatus>("/integrations/yandex-webmaster/host", { method: "PUT", body: JSON.stringify({ host_id, host_url }) }); }
  disconnectYandexWebmaster() { return this.request<void>("/integrations/yandex-webmaster", { method: "DELETE" }); }
  yandexIntelligence() { return this.request<YandexIntelligence>("/yandex-intelligence/dashboard"); }
  syncYandexIntelligence() { return this.request<YandexIntelligence>("/yandex-intelligence/sync", { method: "POST" }); }
  aliceLearningDashboard() { return this.request<AliceLearningDashboard>("/alice-learning/dashboard"); }
  rebuildAliceLearning() { return this.request<AliceLearningDashboard>("/alice-learning/rebuild", { method: "POST" }); }
  aliceAutomationDashboard() { return this.request<AliceAutomationDashboard>("/alice-learning/automation/dashboard"); }
  createAliceAutomationPlan(payload: {
    template_research_id: number; brand: string; website_url: string; language?: string;
    region?: string; research_profile?: string; routing_profile?: string;
    models?: ModelSelection[]; repetitions?: number; daily_query_limit?: number;
    weekly_query_limit?: number; daily_budget_usd?: number; monthly_budget_usd?: number;
  }) { return this.request<AliceAutomationPlan>("/alice-learning/automation/plans", { method: "POST", body: JSON.stringify(payload) }); }
  updateAliceAutomationPlan(id: number, payload: { is_enabled?: boolean }) { return this.request<AliceAutomationPlan>(`/alice-learning/automation/plans/${id}`, { method: "PATCH", body: JSON.stringify(payload) }); }
  runAliceAutomationPlan(id: number, kind: "DAILY" | "WEEKLY" | "MONTHLY" = "DAILY") { return this.request<AliceAutomationRun>(`/alice-learning/automation/plans/${id}/run`, { method: "POST", body: JSON.stringify({ kind }) }); }
  geoPlatforms() { return this.request<GeoPlatform[]>("/geo/platforms"); }
  createGeoPlatform(payload: {
    name: string; domain: string; category: string; country: string; language: string;
    domain_trust?: number; topical_authority_score?: number; ai_citation_history?: number;
    cost_per_placement?: number; evidence: Record<string, unknown>;
  }) { return this.request<GeoPlatform>("/geo/platforms", { method: "POST", body: JSON.stringify(payload) }); }
  deleteGeoPlatform(id: string) { return this.request<void>(`/geo/platforms/${id}`, { method: "DELETE" }); }
  frozenPromptSets() { return this.request<FrozenPromptSet[]>("/geo/prompt-sets"); }
  prioritizeGeoPlatforms(platformIds: string[], aiEngine: string) {
    return this.request<EisPriorityResult>("/v1/eis/batch-prioritize", {
      method: "POST",
      body: JSON.stringify({ platform_ids: platformIds, ai_engine: aiEngine, query_evidence: {} }),
    });
  }
  publicationInfluence() {
    return this.request<PublicationInfluenceEstimate[]>("/publication-learning/influence");
  }
  disconnectProvider(id: number) { return this.request<void>(`/provider-connections/${id}`, { method: "DELETE" }); }
  routerStatus() {
    return this.request<{status: string; costs: Record<string, number>}>('/router/status');
  }
  productAnalytics(period = "DAILY", provider = "") {
    const query = new URLSearchParams({ period });
    if (provider) query.set("provider", provider);
    return this.request<ProductAnalyticsDashboard>(
      `/product-analytics/dashboard?${query.toString()}`,
    );
  }
  notifications(category = "") {
    const query = category ? `?category=${encodeURIComponent(category)}` : "";
    return this.request<NotificationItem[]>(`/notifications${query}`);
  }
  notificationSummary() {
    return this.request<{ unread: number; total: number; archived: number }>(
      "/notifications/summary",
    );
  }
  markNotificationRead(id: number) {
    return this.request<NotificationItem>(`/notifications/${id}/read`, { method: "POST" });
  }
  archiveNotification(id: number) {
    return this.request<NotificationItem>(`/notifications/${id}/archive`, { method: "POST" });
  }
  organizations() { return this.request<OrganizationItem[]>("/organizations"); }
  createOrganization(payload: { name: string; slug: string }) {
    return this.request<OrganizationItem>("/organizations", { method: "POST", body: JSON.stringify(payload) });
  }
  switchOrganization(id: number) { return this.request<OrganizationItem>(`/organizations/${id}/switch`, { method: "POST" }); }
  organizationMembers(id: number) { return this.request<OrganizationMember[]>(`/organizations/${id}/members`); }
  organizationActivity(id: number) { return this.request<Array<{ id: number; action: string; actor_id: number; created_at: string }>>(`/organizations/${id}/activity`); }
  inviteOrganizationMember(id: number, email: string) { return this.request(`/organizations/${id}/invitations`, { method: "POST", body: JSON.stringify({ email, role: "MEMBER" }) }); }
  finalReport(id: number) {
    return this.request<Record<string, unknown>>(`/research/${id}/final-report`);
  }
  async logout() {
    const refreshToken = sessionStorage.getItem("refresh_token");
    await this.request<void>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    this.clearTokens();
  }
  brandProfile(brand: string, websiteUrl: string) {
    return this.request<BrandProfile>("/research/wizard/brand-profile", {
      method: "POST", body: JSON.stringify({ brand, website_url: websiteUrl }),
    });
  }
}
