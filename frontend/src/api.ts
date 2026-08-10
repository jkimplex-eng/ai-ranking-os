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
export type ResearchItem = { id: number; title: string; status: string };
export type ProviderItem = {
  id: string; display_name: string; capabilities: string[];
  pricing: Record<string, unknown>; context_window: number;
  availability: string; free_tier: boolean; priority: number;
  streaming: boolean; reasoning: boolean; vision: boolean;
};
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

export class ApiClient {
  private token?: string;

  setToken(token: string) { this.token = token; }

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
    });
  }
  me() { return this.request<{ display_name: string; email: string }>("/auth/me"); }
  workspace() { return this.request<WorkspaceSettings>("/workspace"); }
  updateWorkspace(settings: Record<string, unknown>) { return this.request<WorkspaceSettings>("/workspace", { method: "PATCH", body: JSON.stringify({ settings }) }); }
  apiKeys() { return this.request<ApiKeyItem[]>("/api-keys"); }
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
    sessionStorage.removeItem("refresh_token");
  }
}
