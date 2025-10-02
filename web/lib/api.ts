// web/lib/api.ts

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type Profile = {
  id: number;
  email: string;
  roles: string[]; // ["admin","technician"] etc.
};

export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Invalid credentials");
  }
  return res.json() as Promise<{ access_token: string; token_type: string }>;
}

export async function me(token: string) {
  const res = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Unauthorized");
  }
  return res.json() as Promise<Profile>;
}

// Scans API

export type ScanStatus = "uploaded" | "ingested" | "graded" | "error";

export type Scan = {
  id: string;
  scan_id?: string;
  capture_id: string;
  ingest_key: string;
  device_id: string;
  farm_id?: string;
  animal_id?: string;
  operator_id?: string;
  captured_at?: string;
  status: ScanStatus;
  image_asset_id?: string;
  mask_asset_id?: string;
  created_at: string;
};

export type ScanDetail = Scan & {
  device_code?: string;
  device_label?: string;
  farm_name?: string;
  image_bucket?: string;
  image_key?: string;
  mask_bucket?: string;
  mask_key?: string;
};

export type PaginatedScans = {
  scans: Scan[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
};

export async function listScans(
  token: string,
  params?: {
    page?: number;
    per_page?: number;
    status?: ScanStatus;
    device_id?: string;
    farm_id?: string;
    sort_by?: "created_at" | "captured_at";
    sort_order?: "asc" | "desc";
  }
) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", params.page.toString());
  if (params?.per_page) query.set("per_page", params.per_page.toString());
  if (params?.status) query.set("status", params.status);
  if (params?.device_id) query.set("device_id", params.device_id);
  if (params?.farm_id) query.set("farm_id", params.farm_id);
  if (params?.sort_by) query.set("sort_by", params.sort_by);
  if (params?.sort_order) query.set("sort_order", params.sort_order);

  const url = `${API_BASE}/scans${query.toString() ? `?${query}` : ""}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch scans");
  }
  return res.json() as Promise<PaginatedScans>;
}

export async function getScan(token: string, scanId: string) {
  const res = await fetch(`${API_BASE}/scans/${scanId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch scan");
  }
  return res.json() as Promise<ScanDetail>;
}

// Admin API

export type Farm = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
};

export type Device = {
  id: string;
  device_code: string;
  label?: string;
  farm_id?: string;
  s3_prefix_hint?: string;
  last_seen_at?: string;
  last_upload_at?: string;
  captures_count: number;
  created_at: string;
  updated_at: string;
};

export async function listFarms(token: string) {
  const res = await fetch(`${API_BASE}/admin/farms`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch farms");
  }
  return res.json() as Promise<Farm[]>;
}

export async function createFarm(token: string, name: string) {
  const res = await fetch(`${API_BASE}/admin/farms`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to create farm");
  }
  return res.json() as Promise<Farm>;
}

export async function listDevices(token: string) {
  const res = await fetch(`${API_BASE}/admin/devices`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch devices");
  }
  return res.json() as Promise<Device[]>;
}

export async function createDevice(
  token: string,
  data: { device_code: string; label?: string; farm_id?: string }
) {
  const res = await fetch(`${API_BASE}/admin/devices`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to create device");
  }
  return res.json() as Promise<Device>;
}
