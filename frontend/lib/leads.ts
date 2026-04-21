import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getAuthToken(): string | null {
  // Try localStorage first. If you use a hook, replace this with a call to it.
  try {
    // login stores the token under key 'token'
    return typeof window !== "undefined" ? localStorage.getItem("token") : null;
  } catch {
    return null;
  }
}

export interface Lead {
  id: string;
  name: string;
  company?: string;
  score?: number;
  status?: string;
  intent_score?: number;
  value?: string;
  email?: string;
  phone?: string;
}

export async function getLeads(): Promise<Lead[]> {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Not authenticated: missing token");
  }

  const res = await axios.get<any[]>(`${API_URL}/api/v1/leads`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    withCredentials: true,
  });

  const mappedLeads: Lead[] = (res.data ?? []).map((lead: any) => {
    const dealNum = Number(lead.deal_value ?? 0);
    return {
      ...lead,
      score: Number(lead.intent_score),
      intent_score: Number(lead.intent_score),
      status: (lead.status ?? "").toLowerCase(),
      value: `€${Number.isFinite(dealNum) ? dealNum.toLocaleString() : 0}`,
    } as Lead;
  });

  return mappedLeads;
}

export default { getLeads };
