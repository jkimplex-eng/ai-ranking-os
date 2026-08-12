export type TokenPair = { access_token: string; refresh_token: string };
export type AuthProfile = { id: number; display_name: string; email: string; roles: string[] };
export type ModelSelection = { provider: string; model: string };
export type WizardPayload = {
  brand: string;
  website_url: string;
  brand_profile?: BrandProfile;
  models?: ModelSelection[];
  routing_profile: "FAST" | "BALANCED" | "HIGH_QUALITY" | "FREE" | "PRIVATE" | "ENTERPRISE";
  languages: string[];
  regions: string[];
  prompt_code: string;
  research_template_code: string;
  research_scope?: "ALL" | "SELECTED" | "RUSSIAN" | "COMMERCIAL" | "FREE" | "CONSENSUS" | "COMPARE";
  research_profile?: "GEO" | "ECOMMERCE" | "MEDICAL" | "BEAUTY" | "ENTERPRISE" | "UNIVERSAL";
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
  query_catalog: Array<{ id: string; cluster: string; intent: string; text: string }>;
  task_count: number;
  brand_profile: BrandProfile;
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
  publications: Array<{ id: number; title: string; url: string; published_at: string; observations: Array<{ id: number; provider: string; model: string; first_observed_at: string; evidence_excerpt: string }> }>;
};
export type ActionPlanItem = { recommendation: RecommendationItem; template?: { title: string; description: string; steps: string[]; expected_result: string; estimated_time: string; version: string }; steps: string[]; expected_effect: string; estimated_time?: string };
export type ActionPlan = { research_id: number; engine_version: string; generated_at: string; items: ActionPlanItem[] };
export type SimulationItem = { recommendation_id: number; metric: string; current_metric: number; expected_metric_change: number; predicted_visibility: number; predicted_delta: number; confidence_min: number; confidence_expected: number; confidence_max: number; estimated_duration_days: number; model_version: string };
export type SimulationResult = { research_id: number; model_version: string; simulated_at: string; simulations: SimulationItem[] };
export type ResearchItem = { id: number; title: string; status: string; progress_percent?: number; total_tasks?: number; completed_tasks?: number; failed_tasks?: number; created_at?: string; updated_at?: string; metadata?: Record<string, unknown> };
export type ResearchTaskItem = { id: number; research_id: number; status: string; provider?: string; model?: string; execution_id?: number; created_at: string; updated_at: string; error?: string };
export type ExecutionItem = { id: number; state: string; started_at?: string; finished_at?: string; duration_ms?: number; attempt_count: number; error?: string };
export type WorkspaceProjectItem = { id: number; name: string; description: string; research_count: number };
export type CompetitorItem = { id: number; project_id: number; name: string; domains: string[]; active: boolean };
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
  execution(id: number) { return this.request<ExecutionItem>(`/execution/${id}`); }
  reports() { return this.request<{ items: ReportCatalogItem[]; total: number }>("/reports?limit=100"); }
  recommendations(researchId: number) { return this.request<{ recommendations: RecommendationItem[] }>(`/research/${researchId}/recommendations`); }
  actionPlan(researchId: number) { return this.request<ActionPlan>(`/research/${researchId}/action-plan`); }
  simulation(researchId: number) { return this.request<SimulationResult>(`/research/${researchId}/simulation`); }
  graph() { return this.request<GraphSnapshot>("/graph"); }
  workspaceProjects() { return this.request<WorkspaceProjectItem[]>("/workspace/projects"); }
  projectCompetitors(projectId: number) { return this.request<CompetitorItem[]>(`/workspace/projects/${projectId}/competitors`); }
  feedback() { return this.request<FeedbackItem[]>("/feedback"); }
  listProviders() { return this.request<ProviderItem[]>("/providers"); }
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
