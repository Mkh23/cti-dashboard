// web/lib/api.ts

export const API_BASE =
  process.env.INTERNAL_API_BASE || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type RegistrationStatus = "pending" | "approved" | "rejected";

export type Profile = {
  id: number;
  email: string;
  full_name?: string | null;
  phone_number?: string | null;
  address?: string | null;
  roles: string[]; // ["admin","technician"] etc.
  registration_status: RegistrationStatus;
};

export type RegisterUserPayload = {
  email: string;
  password: string;
  full_name: string;
  phone_number: string;
  address: string;
  requested_role: "farmer" | "technician";
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

export async function registerUser(payload: RegisterUserPayload) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Registration failed");
  }
  return res.json() as Promise<{ id: string; email: string; registration_status: RegistrationStatus }>;
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

export type UpdateProfileData = {
  full_name?: string | null;
  phone_number?: string | null;
  address?: string | null;
};

export async function updateProfile(token: string, data: UpdateProfileData) {
  const res = await fetch(`${API_BASE}/me`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update profile");
  }
  return res.json() as Promise<Profile>;
}

export type ChangePasswordData = {
  current_password: string;
  new_password: string;
};

export async function changePassword(token: string, data: ChangePasswordData) {
  const res = await fetch(`${API_BASE}/me/password`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to change password");
  }
  return res.json() as Promise<{ message: string }>;
}

export type AdminUser = {
  id: string;
  email: string;
  full_name?: string | null;
  roles: string[];
  registration_status: RegistrationStatus;
  requested_role?: string | null;
};

export type PendingUser = {
  id: string;
  email: string;
  full_name?: string | null;
  phone_number?: string | null;
  address?: string | null;
  requested_role?: string | null;
  registration_status: RegistrationStatus;
  created_at: string;
};

export async function listAdminUsers(token: string) {
  const res = await fetch(`${API_BASE}/admin/users`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to load users");
  }
  return res.json() as Promise<AdminUser[]>;
}

export async function listPendingUsers(token: string) {
  const res = await fetch(`${API_BASE}/admin/users/pending`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to load pending users");
  }
  return res.json() as Promise<PendingUser[]>;
}

export async function approvePendingUser(
  token: string,
  id: string,
  roles: string[]
) {
  const res = await fetch(`${API_BASE}/admin/users/${id}/approve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ roles }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to approve user");
  }
  return res.json() as Promise<AdminUser>;
}

export async function rejectPendingUser(
  token: string,
  id: string,
  reason?: string
) {
  const res = await fetch(`${API_BASE}/admin/users/${id}/reject`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to reject user");
  }
  return res.json() as Promise<PendingUser>;
}

// Scans API

export type ScanStatus = "uploaded" | "ingested" | "graded" | "error";

export type LatestGrading = {
  id?: string;
  model_name?: string;
  model_version?: string;
  confidence?: number | null;
  created_at?: string;
};

export type GradingResult = {
  id: string;
  model_name: string;
  model_version: string;
  inference_sha256?: string | null;
  confidence?: number | null;
  confidence_breakdown?: Record<string, number>;
  features_used?: Record<string, number>;
  created_by?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
  created_at: string;
};

export type Scan = {
  id: string;
  scan_id?: string | null;
  capture_id: string;
  ingest_key: string;
  device_id: string;
  device_code?: string | null;
  device_label?: string | null;
  farm_id?: string | null;
  farm_name?: string | null;
  animal_id?: string | null;
  operator_id?: string | null;
  captured_at?: string | null;
  status: ScanStatus;
  image_asset_id?: string | null;
  mask_asset_id?: string | null;
  backfat_line_asset_id?: string | null;
  created_at: string;
  latest_grading?: LatestGrading | null;
  group_id?: string | null;
  group_name?: string | null;
  group_external_id?: string | null;
  imf?: number | null;
  backfat_thickness?: number | null;
  animal_weight?: number | null;
  animal_rfid?: string | null;
  ribeye_area?: number | null;
  clarity?: ScanQuality | null;
  usability?: ScanQuality | null;
  label?: string | null;
  grading?: string | null;
};

export type ScanDetail = Scan & {
  image_bucket?: string | null;
  image_key?: string | null;
  image_url?: string | null;
  mask_bucket?: string | null;
  mask_key?: string | null;
  mask_url?: string | null;
  backfat_line_bucket?: string | null;
  backfat_line_key?: string | null;
  backfat_line_url?: string | null;
  grading_results: GradingResult[];
};

export type ScanQuality = "good" | "medium" | "bad";
export type MaskType = "ribeye" | "backfat";

export type PaginatedScans = {
  scans: Scan[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
};

export type ScanStats = {
  total: number;
  by_status: Record<string, number>;
  recent_count: number;
};

export type GradeScanPayload = {
  model_name: string;
  model_version?: string;
  inference_sha256?: string | null;
  confidence?: number | null;
  confidence_breakdown?: Record<string, number>;
  features_used?: Record<string, number>;
};

export async function listScans(
  token: string,
  params?: {
    page?: number;
    per_page?: number;
    status?: ScanStatus;
    device_id?: string;
    farm_id?: string;
    label?: string;
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
  if (params?.label) query.set("label", params.label);
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

export async function getScanStats(token: string) {
  const res = await fetch(`${API_BASE}/scans/stats`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch scan statistics");
  }
  return res.json() as Promise<ScanStats>;
}

export async function gradeScan(
  token: string,
  scanId: string,
  data: GradeScanPayload
) {
  const res = await fetch(`${API_BASE}/scans/${scanId}/grade`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to grade scan");
  }
  return res.json() as Promise<ScanDetail>;
}

export type UpdateScanAttributesPayload = {
  label?: string | null;
  clarity?: ScanQuality | null;
  usability?: ScanQuality | null;
};

export async function updateScanAttributes(
  token: string,
  scanId: string,
  data: UpdateScanAttributesPayload
) {
  const res = await fetch(`${API_BASE}/scans/${scanId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update scan");
  }
  return res.json() as Promise<ScanDetail>;
}

export async function updateScanAssignment(
  token: string,
  scanId: string,
  data: { farm_id?: string | null; group_id?: string | null }
) {
  const res = await fetch(`${API_BASE}/scans/${scanId}/assignment`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update scan assignment");
  }
  return res.json() as Promise<ScanDetail>;
}

export async function deleteScan(token: string, scanId: string) {
  const res = await fetch(`${API_BASE}/scans/${scanId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to delete scan");
  }
  return res.json() as Promise<{ message: string; id: string }>;
}

export async function getScanMask(
  token: string,
  scanId: string,
  maskType: MaskType
) {
  const res = await fetch(`${API_BASE}/scans/${scanId}/mask?mask_type=${maskType}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to load mask");
  }
  return res.blob();
}

export async function updateScanMask(
  token: string,
  scanId: string,
  maskType: MaskType,
  blob: Blob
) {
  const url = `${API_BASE}/scans/${scanId}/mask?mask_type=${maskType}`;
  const form = new FormData();
  form.append(
    "file",
    blob,
    maskType === "ribeye" ? "mask.png" : "backfat_line.png"
  );

  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update mask");
  }
  return (await res.json()) as ScanDetail;
}

// Admin API

export type FarmOwner = {
  user_id: string;
  email: string;
  full_name?: string | null;
};

export type FarmMember = {
  user_id: string;
  email: string;
  full_name?: string | null;
  roles: string[];
  is_owner: boolean;
};

export type GeoPoint = {
  lat: number;
  lon: number;
};

export type FarmGeofencePayload = {
  lat: number;
  lon: number;
  radius_m?: number;
};

export type Farm = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  owners: FarmOwner[];
  members: FarmMember[];
  can_edit: boolean;
  /**
   * Optional centroid (lat/lon) used to auto-route ingest by GPS.
   */
  centroid?: GeoPoint | null;
  geofence_exists?: boolean;
};

export type Group = {
  id: string;
  name: string;
  external_id?: string | null;
  born_date?: string | null;
  farm_id?: string | null;
  farm_name?: string | null;
  created_at: string;
  updated_at: string;
};

export type Animal = {
  id: string;
  tag_id: string;
  rfid?: string | null;
  breed?: string | null;
  sex?: string | null;
  birth_date?: string | null;
  farm_id?: string | null;
  farm_name?: string | null;
  group_id?: string | null;
  group_name?: string | null;
  created_at: string;
};

export type AnimalScan = {
  id: string;
  capture_id: string;
  label?: string | null;
  created_at: string;
  grading?: string | null;
  latest_model?: string | null;
  latest_version?: string | null;
  latest_confidence?: number | null;
  imf?: number | null;
  backfat_thickness?: number | null;
  animal_weight?: number | null;
  ribeye_area?: number | null;
  image_url?: string | null;
  image_key?: string | null;
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
  const res = await fetch(`${API_BASE}/farms`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch farms");
  }
  return res.json() as Promise<Farm[]>;
}

export async function createFarm(
  token: string,
  data: { name: string; owner_ids?: string[]; geofence?: FarmGeofencePayload }
) {
  const res = await fetch(`${API_BASE}/farms`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to create farm");
  }
  return res.json() as Promise<Farm>;
}

export async function listGroups(
  token: string,
  farmId?: string,
  options?: { born_from?: string; born_to?: string; name?: string }
) {
  const query = new URLSearchParams();
  if (farmId) query.set("farm_id", farmId);
  if (options?.born_from) query.set("born_from", options.born_from);
  if (options?.born_to) query.set("born_to", options.born_to);
  if (options?.name) query.set("name", options.name);
  const qs = query.toString();
  const res = await fetch(`${API_BASE}/groups${qs ? `?${qs}` : ""}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch groups");
  }
  return res.json() as Promise<Group[]>;
}

export async function createGroup(
  token: string,
  data: { name: string; external_id?: string; born_date?: string; farm_id?: string }
) {
  const res = await fetch(`${API_BASE}/groups`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to create group");
  }
  return res.json() as Promise<Group>;
}

export async function updateGroup(
  token: string,
  groupId: string,
  data: { name?: string; external_id?: string; born_date?: string; farm_id?: string }
) {
  const res = await fetch(`${API_BASE}/groups/${groupId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update group");
  }
  return res.json() as Promise<Group>;
}

export async function listAnimals(
  token: string,
  params?: { farm_id?: string; group_id?: string; tag?: string }
) {
  const query = new URLSearchParams();
  if (params?.farm_id) query.set("farm_id", params.farm_id);
  if (params?.group_id) query.set("group_id", params.group_id);
  if (params?.tag) query.set("tag", params.tag);
  const qs = query.toString();
  const res = await fetch(`${API_BASE}/animals${qs ? `?${qs}` : ""}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch animals");
  }
  return res.json() as Promise<Animal[]>;
}

export async function createAnimal(
  token: string,
  data: {
    tag_id: string;
    rfid?: string;
    breed?: string;
    sex?: string;
    birth_date?: string;
    farm_id?: string;
    group_id?: string;
  }
) {
  const res = await fetch(`${API_BASE}/animals`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to create animal");
  }
  return res.json() as Promise<Animal>;
}

export async function updateAnimal(
  token: string,
  animalId: string,
  data: {
    tag_id?: string;
    rfid?: string;
    breed?: string;
    sex?: string;
    birth_date?: string;
    farm_id?: string;
    group_id?: string;
  }
) {
  const res = await fetch(`${API_BASE}/animals/${animalId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update animal");
  }
  return res.json() as Promise<Animal>;
}

export async function deleteAnimal(token: string, animalId: string) {
  const res = await fetch(`${API_BASE}/animals/${animalId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to delete animal");
  }
}

export async function getAnimal(token: string, animalId: string) {
  const res = await fetch(`${API_BASE}/animals/${animalId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch animal");
  }
  return res.json() as Promise<Animal>;
}

export async function getAnimalScans(token: string, animalId: string) {
  const res = await fetch(`${API_BASE}/animals/${animalId}/scans`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch animal scans");
  }
  return res.json() as Promise<AnimalScan[]>;
}

export async function getGroup(token: string, groupId: string) {
  const res = await fetch(`${API_BASE}/groups/${groupId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch group");
  }
  return res.json() as Promise<Group>;
}

export async function getGroupAnimals(token: string, groupId: string) {
  const res = await fetch(`${API_BASE}/groups/${groupId}/animals`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch group animals");
  }
  return res.json() as Promise<Animal[]>;
}

export async function getFarmGroups(token: string, farmId: string) {
  const res = await fetch(`${API_BASE}/farms/${farmId}/groups`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch farm groups");
  }
  return res.json() as Promise<Array<{ id: string; name: string; external_id?: string | null; born_date?: string | null }>>;
}

export async function getFarm(token: string, farmId: string) {
  const res = await fetch(`${API_BASE}/farms/${farmId}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch farm");
  }
  return res.json() as Promise<Farm>;
}

export async function updateFarm(
  token: string,
  farmId: string,
  data: { name?: string; owner_ids?: string[]; geofence?: FarmGeofencePayload }
) {
  const res = await fetch(`${API_BASE}/farms/${farmId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update farm");
  }
  return res.json() as Promise<Farm>;
}

export async function addFarmMember(
  token: string,
  farmId: string,
  data: { user_id?: string; email?: string }
) {
  const res = await fetch(`${API_BASE}/farms/${farmId}/members`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to add member");
  }
  return res.json() as Promise<Farm>;
}

export async function removeFarmMember(
  token: string,
  farmId: string,
  userId: string
) {
  const res = await fetch(`${API_BASE}/farms/${farmId}/members/${userId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to remove member");
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

export type SyncScansMode = "add_only" | "add_remove";

export type SyncScansResult = {
  bucket: string;
  prefix: string;
  mode: string;
  added: number;
  duplicates: number;
  removed: number;
  errors: string[];
  synced_ingest_keys: number;
};

export async function syncScans(
  token: string,
  mode: SyncScansMode,
  prefix?: string
) {
  const res = await fetch(`${API_BASE}/admin/database/sync-scans`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ mode, prefix }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to sync scans");
  }
  return res.json() as Promise<SyncScansResult>;
}

export type Announcement = {
  id: string;
  author_name?: string | null;
  subject?: string | null;
  content_html: string;
  created_at: string;
  show_on_home?: boolean;
  pinned?: boolean;
};

export async function listPublicAnnouncements() {
  const res = await fetch(`${API_BASE}/announcements`, { cache: "no-store" });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch announcements");
  }
  return res.json() as Promise<Announcement[]>;
}

export async function listAdminAnnouncements(token: string) {
  const res = await fetch(`${API_BASE}/admin/announcements`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to fetch announcements");
  }
  return res.json() as Promise<Announcement[]>;
}

export async function createAnnouncement(
  token: string,
  data: {
    subject: string;
    content_html: string;
    show_on_home: boolean;
    pinned: boolean;
  }
) {
  const res = await fetch(`${API_BASE}/admin/announcements`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to create announcement");
  }
  return res.json() as Promise<Announcement>;
}

export async function updateAnnouncement(
  token: string,
  id: string,
  data: {
    subject?: string;
    content_html?: string;
    show_on_home?: boolean;
    pinned?: boolean;
  }
) {
  const res = await fetch(`${API_BASE}/admin/announcements/${id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Failed to update announcement");
  }
  return res.json() as Promise<Announcement>;
}
