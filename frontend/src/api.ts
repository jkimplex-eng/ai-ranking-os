export type TokenPair = { access_token: string; refresh_token: string };
export type ModelSelection = { provider: string; model: string };
export type WizardPayload = {
  brand: string;
  models: ModelSelection[];
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
