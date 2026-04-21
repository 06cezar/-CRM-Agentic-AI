const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Attach token from localStorage if present
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  register: (email: string, full_name: string, password: string) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, full_name, password }),
    }),

  login: (email: string, password: string) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  createLead: (lead: any) =>
    request("/api/v1/leads", {
      method: "POST",
      body: JSON.stringify(lead),
    }),

  logout: () => request("/auth/logout", { method: "POST" }),

  me: () =>
    request<{ id: number; email: string; full_name: string; role: string }>(
      "/auth/me",
    ),
};
