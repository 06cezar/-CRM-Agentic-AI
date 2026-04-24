const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }))
    throw new Error(err.detail ?? "Request failed")
  }
  return res.json()
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface LeadAPI {
  id: number
  name: string
  company: string
  role: string
  email: string
  phone: string | null
  deal_value: string | null
  currency: string
  deal_value_display: string | null
  intent_score: number | null
  score: number | null
  last_researched_at: string | null
  last_activity_description: string | null
  signals: string[]
  assigned_to: number | null
  status: string
  created_at: string
}

export interface ActivityAPI {
  id: number
  type: string
  message: string
  leadName: string
  timestamp: string
  status: string
}

export interface StatsAPI {
  hot_leads: number
  ai_actions_today: number
  pipeline_value: string
  pipeline_value_raw: number
}

// ── API client ────────────────────────────────────────────────────────────────

export const api = {
  register: (email: string, full_name: string, password: string) =>
    request("/auth/register", { method: "POST", body: JSON.stringify({ email, full_name, password }) }),

  login: (email: string, password: string) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  logout: () => request("/auth/logout", { method: "POST" }),

  me: () => request<{ id: number; email: string; full_name: string; role: string }>("/auth/me"),

  // ── Leads ──────────────────────────────────────────────────────────────────
  getLeads: () => request<LeadAPI[]>("/leads"),

  createLead: (body: Omit<LeadAPI, "id" | "intent_score" | "score" | "last_researched_at" | "signals" | "assigned_to" | "created_at" | "deal_value_display">) =>
    request<LeadAPI>("/leads", { method: "POST", body: JSON.stringify(body) }),

  researchLead: (leadId: number) =>
    request<LeadAPI>(`/leads/${leadId}/research`, { method: "POST" }),

  // ── Activity ───────────────────────────────────────────────────────────────
  getActivity: (limit = 10) =>
    request<ActivityAPI[]>(`/activity?limit=${limit}`),

  // ── Stats ──────────────────────────────────────────────────────────────────
  getStats: () => request<StatsAPI>("/stats"),
}
