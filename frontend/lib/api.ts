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

export const api = {
  register: (email: string, full_name: string, password: string) =>
    request("/auth/register", { method: "POST", body: JSON.stringify({ email, full_name, password }) }),

  login: (email: string, password: string) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  logout: () => request("/auth/logout", { method: "POST" }),

  me: () => request<{ id: number; email: string; full_name: string; role: string }>("/auth/me"),
}
