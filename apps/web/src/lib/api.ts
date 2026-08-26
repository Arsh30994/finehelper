export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "fh_token";
const ORG_KEY = "fh_org";

function store(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function getToken() {
  const s = store();
  if (!s) return null;
  const sessionTok = s.getItem(TOKEN_KEY);
  if (sessionTok) return sessionTok;
  try {
    const legacy = localStorage.getItem(TOKEN_KEY);
    if (legacy) {
      s.setItem(TOKEN_KEY, legacy);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(ORG_KEY);
      return legacy;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function setSession(token: string, org?: unknown) {
  const s = store();
  if (!s) return;
  s.setItem(TOKEN_KEY, token);
  if (org) s.setItem(ORG_KEY, JSON.stringify(org));
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ORG_KEY);
  } catch {
    /* ignore */
  }
}

export function clearSession() {
  const s = store();
  s?.removeItem(TOKEN_KEY);
  s?.removeItem(ORG_KEY);
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ORG_KEY);
  } catch {
    /* ignore */
  }
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData) && !(init.body instanceof Blob)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "omit",
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    let message = text || `${res.status} ${res.statusText}`;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
      else if (Array.isArray(parsed.detail))
        message = parsed.detail.map((d) => (d as { msg?: string }).msg || String(d)).join(", ");
    } catch {
      /* keep raw text */
    }
    throw new Error(message.slice(0, 400));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
