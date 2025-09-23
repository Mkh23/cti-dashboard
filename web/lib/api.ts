const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// --- auth ---
export async function login(username: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<{ access_token: string; token_type: string }>;
}

// --- types ---
export type Role = "admin" | "tech" | "farmer";
export type User = { id: number; email: string; role: Role };
export type Profile = User; // alias for clarity

// --- me ---
export async function me(token: string) {
  return http<Profile>("/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// --- admin helpers ---
export async function adminListUsers(token: string) {
  return http<User[]>("/admin/users", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function adminUpdateUserRole(token: string, userId: number, role: Role) {
  return http<User>(`/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ role }),
  });
}
