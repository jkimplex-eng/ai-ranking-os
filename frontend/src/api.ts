export type TokenPair = { access_token: string; refresh_token: string };
export type ModelSelection = { provider: string; model: string };
export type WizardPayload = {
  brand: string;
  models?: ModelSelection[];
  routing_profile: "FAST" | "BALANCED" | "HIGH_QUALITY" | "FREE" | "PRIVATE" | "ENTERPRISE";
  languages: string[];
  regions: string[];
  prompt_code: string;
  research_template_code: string;
};
export type WizardReview = {
  valid: boolean;
  title: string;
  prompt: string;
  provider_models: string[];
  languages: string[];
  regions: string[];
  pipeline: string[];
};
export type ReportResult = {
  research: { id: number; title: string; status: string };
  report_url: string;
  report: Record<string, unknown>;
};
export type ResearchItem = { id: number; title: string; status: string; progress_percent?: number; total_tasks?: number; completed_tasks?: number; failed_tasks?: number; created_at?: string };
export type WorkspaceProjectItem = { id: number; name: string; description: string; research_count: number };
export type CompetitorItem = { id: number; project_id: number; name: string; domains: string[]; active: boolean };
export type ReportCatalogItem = { research_id: number; title: string; status: string; visibility_score?: number; created_at: string };
export type RecommendationItem = { id: number; recommendation_type: string; priority: string; explanation: string; metric: string; metric_value: number; expected_effect: string };
export type GraphSnapshot = { id: number; structure_version: string; node_count: number; edge_count: number; created_at: string; nodes: Array<{ id: number; name: string; node_type: string; confidence: number }>; edges: unknown[] };
export type FeedbackItem = { id: number; title: string; feedback_type: string; priority: string; status: string; created_at: string };
export type ProviderItem = {
  id: string; display_name: string; capabilities: string[];
  pricing: Record<string, unknown>; context_window: number;
  availability: string; free_tier: boolean; priority: number;
  streaming: boolean; reasoning: boolean; vision: boolean;
};
export type SystemProviderItem = { model_id: string; provider: string; latency_ms: number; circuit_state: string; interface: { available?: boolean; mock?: boolean; checked_at?: string; models?: number | string[] } };
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

  setToken(token: string) {
    this.token = token;
    sessionStorage.setItem("access_token", token);
  }

  private saveTokens(tokens: TokenPair) {
    this.setToken(tokens.access_token);
    sessionStorage.setItem("refresh_token", tokens.refresh_token);
    return tokens;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`/api${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
        ...init.headers,
      },
    });
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
  me() { return this.request<{ display_name: string; email: string }>("/auth/me"); }
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
  reports() { return this.request<{ items: ReportCatalogItem[]; total: number }>("/reports?limit=100"); }
  recommendations(researchId: number) { return this.request<{ recommendations: RecommendationItem[] }>(`/research/${researchId}/recommendations`); }
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
    this.token = undefined;
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
  }
}
