"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  gradeScan,
  getScan,
  getScanMask,
  listFarms,
  listGroups,
  me,
  updateScanAttributes,
  updateScanAssignment,
  updateScanMask,
  deleteScan,
  type GradeScanPayload,
  type Group,
  type Farm,
  type Profile,
  type ScanDetail,
  type ScanQuality,
  type MaskType,
  type UpdateScanAttributesPayload,
} from "@/lib/api";
import { buildFarmTimeZoneMap, DEFAULT_FARM_TIME_ZONE, formatDateTime } from "@/lib/datetime";
import type { Role } from "@/lib/roles";

const canGrade = (roles: string[]): boolean =>
  roles.includes("admin") || roles.includes("technician");

const formatConfidence = (value?: number | null) => {
  if (value === undefined || value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
};

const formatMetric = (
  value?: number | null,
  options: { digits?: number; suffix?: string } = {}
) => {
  if (value === undefined || value === null) return "—";
  const digits = options.digits ?? 2;
  const suffix = options.suffix ?? "";
  return `${Number(value).toFixed(digits)}${suffix}`;
};

const qualityDisplay = (value?: string | null) => {
  if (!value) return "—";
  return value.charAt(0).toUpperCase() + value.slice(1);
};

const QUALITY_TONE: Record<ScanQuality, string> = {
  good: "text-emerald-300",
  medium: "text-amber-300",
  bad: "text-rose-300",
};

function QualityBadge({ value }: { value?: string | null }) {
  if (!value) return <span className="text-sm text-gray-500">—</span>;
  const tone = QUALITY_TONE[value as ScanQuality] ?? "text-gray-300";
  return (
    <span className={`text-sm font-semibold uppercase tracking-wide ${tone}`}>
      {qualityDisplay(value)}
    </span>
  );
}

type GradeFormState = {
  model_name: string;
  model_version: string;
  confidence: string;
};

type AttributesFormState = {
  label: string;
  clarity: "" | ScanQuality;
  usability: "" | ScanQuality;
};

const QUALITY_OPTIONS: { value: "" | ScanQuality; label: string }[] = [
  { value: "", label: "Not set" },
  { value: "good", label: "Good" },
  { value: "medium", label: "Medium" },
  { value: "bad", label: "Bad" },
];

const toQualityOrNull = (value: "" | ScanQuality): ScanQuality | null =>
  value === "" ? null : value;

const tzLabel = (value?: string) => {
  const map: Record<string, string> = {
    "America/Edmonton": "MT",
    "America/Denver": "MT",
    "America/Phoenix": "MT",
    "America/Chicago": "CT",
    "America/New_York": "ET",
    "America/Los_Angeles": "PT",
    "America/Vancouver": "PT",
  };
  if (value && map[value]) return map[value];
  if (value) return value;
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "Browser local";
};

export default function ScanDetailPage({ role }: { role: Role }) {
  const params = useParams<{ scanId: string }>();
  const scanId = params?.scanId;
  const router = useRouter();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [farmTimeZones, setFarmTimeZones] = useState<Record<string, string>>({});
  const [farms, setFarms] = useState<Farm[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);

  const [gradeForm, setGradeForm] = useState<GradeFormState>({
    model_name: "cti-sim",
    model_version: "1.0.0",
    confidence: "",
  });
  const [gradeLoading, setGradeLoading] = useState(false);
  const [gradeError, setGradeError] = useState<string | null>(null);
  const [gradeSuccess, setGradeSuccess] = useState<string | null>(null);
  const [showMask, setShowMask] = useState(false);
  const [showBackfatMask, setShowBackfatMask] = useState(false);
  const [editingMask, setEditingMask] = useState<MaskType | null>(null);
  const [brushSize, setBrushSize] = useState(24);
  const [brushMode, setBrushMode] = useState<"add" | "erase">("add");
  const [maskSaving, setMaskSaving] = useState(false);
  const [maskError, setMaskError] = useState<string | null>(null);
  const [maskSuccess, setMaskSuccess] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const maskCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawingRef = useRef(false);
  const lastPointRef = useRef<{ x: number; y: number } | null>(null);
  const [attributesForm, setAttributesForm] = useState<AttributesFormState>({
    label: "",
    clarity: "",
    usability: "",
  });
  const [attributesLoading, setAttributesLoading] = useState(false);
  const [attributesError, setAttributesError] = useState<string | null>(null);
  const [attributesSuccess, setAttributesSuccess] = useState<string | null>(null);
  const [assignmentForm, setAssignmentForm] = useState<{ farm_id: string; group_id: string }>({
    farm_id: "",
    group_id: "",
  });
  const [assignmentLoading, setAssignmentLoading] = useState(false);
  const [assignmentStatus, setAssignmentStatus] = useState<string | null>(null);
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const browserTimeZone = useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone,
    []
  );

  const detailBasePath = useMemo(() => `/dashboard/${role}/scans`, [role]);
  const farmTimeZone = useMemo(
    () => (scan?.farm_id ? farmTimeZones[scan.farm_id] ?? DEFAULT_FARM_TIME_ZONE : undefined),
    [farmTimeZones, scan?.farm_id]
  );
  const groupedOptions = useMemo(() => {
    const targetFarm = assignmentForm.farm_id || scan?.farm_id || null;
    return groups.filter((g) => !targetFarm || g.farm_id === targetFarm);
  }, [assignmentForm.farm_id, groups, scan?.farm_id]);

  const refreshScan = useCallback(
    async (token: string, id: string) => {
      const data = await getScan(token, id);
      setScan(data);
      setGradeForm((prev) => ({
        ...prev,
        model_name: data.latest_grading?.model_name ?? prev.model_name,
        model_version: data.latest_grading?.model_version ?? prev.model_version,
      }));
      setAttributesForm({
        label: data.label ?? "",
        clarity: (data.clarity as ScanQuality | null) ?? "",
        usability: (data.usability as ScanQuality | null) ?? "",
      });
      setAssignmentForm({
        farm_id: data.farm_id ?? "",
        group_id: data.group_id ?? "",
      });
      setShowMask(false);
      setShowBackfatMask(false);
      setEditingMask(null);
    },
    []
  );

  useEffect(() => {
    (async () => {
      try {
        if (!scanId) {
          setError("Missing scan identifier");
          return;
        }
        const token = localStorage.getItem("token");
        if (!token) {
          router.push("/login");
          return;
        }
        const profileData = await me(token);
        if (!profileData.roles.includes("admin") && role === "admin") {
          router.replace("/dashboard");
          return;
        }
        if (!profileData.roles.includes(role) && role !== "admin" && !profileData.roles.includes("admin")) {
          router.replace("/dashboard");
          return;
        }
        setProfile(profileData);
        try {
          const farms = await listFarms(token);
          setFarms(farms);
          setFarmTimeZones(buildFarmTimeZoneMap(farms));
        } catch {
          setFarmTimeZones({});
        }
        try {
          const groupsData = await listGroups(token);
          setGroups(groupsData);
        } catch {
          setGroups([]);
        }
        await refreshScan(token, scanId);
        setError(null);
      } catch (err: any) {
        setError(err?.message || "Failed to load scan");
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshScan, role, router, scanId]);

  const handleGradeSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scan || !profile) return;

    setGradeLoading(true);
    setGradeError(null);
    setGradeSuccess(null);

    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");

      const payload: GradeScanPayload = {
        model_name: gradeForm.model_name.trim() || "cti-sim",
        model_version: gradeForm.model_version.trim() || "1.0.0",
      };
      if (gradeForm.confidence.trim().length > 0) {
        payload.confidence = Number(gradeForm.confidence);
      }

      const updated = await gradeScan(token, scan.id, payload);
      setScan(updated);
      setGradeSuccess("Grading request recorded successfully.");
    } catch (err: any) {
      setGradeError(err?.message || "Failed to run grading");
    } finally {
      setGradeLoading(false);
    }
  };

  const handleAttributesSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    if (!scan) return;

    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      setAttributesLoading(true);
      setAttributesError(null);
      setAttributesSuccess(null);

      const trimmedLabel = attributesForm.label.trim();
      const payload: UpdateScanAttributesPayload = {
        label: trimmedLabel.length ? trimmedLabel : null,
        clarity: toQualityOrNull(attributesForm.clarity),
        usability: toQualityOrNull(attributesForm.usability),
      };
      const updated = await updateScanAttributes(token, scan.id, payload);
      setScan(updated);
      setAttributesSuccess("Scan attributes updated.");
    } catch (err: any) {
      setAttributesError(err?.message || "Failed to update scan attributes");
    } finally {
      setAttributesLoading(false);
    }
  };

  const handleAssignmentSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!scan) return;
    setAssignmentLoading(true);
    setAssignmentError(null);
    setAssignmentStatus(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const payload = {
        farm_id: assignmentForm.farm_id || null,
        group_id: assignmentForm.group_id || null,
      };
      const updated = await updateScanAssignment(token, scan.id, payload);
      setScan(updated);
      setAssignmentStatus("Assignment updated.");
    } catch (err: any) {
      setAssignmentError(err?.message || "Failed to update assignment");
    } finally {
      setAssignmentLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!scan) return;
    if (!window.confirm("Delete this scan permanently? This cannot be undone.")) return;
    setDeleteLoading(true);
    setDeleteError(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      await deleteScan(token, scan.id);
      router.push(detailBasePath);
    } catch (err: any) {
      setDeleteError(err?.message || "Failed to delete scan");
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleImageLoad = useCallback((event: React.SyntheticEvent<HTMLImageElement>) => {
    const img = event.currentTarget;
    setImageSize({ width: img.naturalWidth, height: img.naturalHeight });
  }, []);

  const getCanvasPoint = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      if (!imageSize) return null;
      const rect = event.currentTarget.getBoundingClientRect();
      if (!rect.width || !rect.height) return null;
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      if (x < 0 || y < 0 || x > rect.width || y > rect.height) return null;
      return {
        x: (x / rect.width) * imageSize.width,
        y: (y / rect.height) * imageSize.height,
      };
    },
    [imageSize]
  );

  const drawStroke = useCallback(
    (from: { x: number; y: number }, to: { x: number; y: number }) => {
      const canvas = maskCanvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.lineWidth = brushSize;
      ctx.strokeStyle = "white";
      ctx.globalCompositeOperation =
        brushMode === "add" ? "source-over" : "destination-out";
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    },
    [brushMode, brushSize]
  );

  const handleMaskPointerDown = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      if (!editingMask) return;
      event.preventDefault();
      const point = getCanvasPoint(event);
      if (!point) return;
      drawingRef.current = true;
      lastPointRef.current = point;
      drawStroke(point, point);
    },
    [drawStroke, editingMask, getCanvasPoint]
  );

  const handleMaskPointerMove = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      if (!drawingRef.current || !editingMask) return;
      event.preventDefault();
      const point = getCanvasPoint(event);
      if (!point || !lastPointRef.current) return;
      drawStroke(lastPointRef.current, point);
      lastPointRef.current = point;
    },
    [drawStroke, editingMask, getCanvasPoint]
  );

  const handleMaskPointerUp = useCallback(() => {
    drawingRef.current = false;
    lastPointRef.current = null;
  }, []);

  const exportMaskBlob = useCallback(async () => {
    const canvas = maskCanvasRef.current;
    if (!canvas) return null;
    const outCanvas = document.createElement("canvas");
    outCanvas.width = canvas.width;
    outCanvas.height = canvas.height;
    const ctx = outCanvas.getContext("2d");
    if (!ctx) return null;
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, outCanvas.width, outCanvas.height);
    ctx.drawImage(canvas, 0, 0);
    return await new Promise<Blob | null>((resolve) =>
      outCanvas.toBlob((blob) => resolve(blob), "image/png")
    );
  }, []);

  const handleMaskSave = useCallback(async () => {
    if (!scan || !editingMask) return;
    setMaskSaving(true);
    setMaskError(null);
    setMaskSuccess(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const blob = await exportMaskBlob();
      if (!blob) throw new Error("Unable to export mask");
      await updateScanMask(token, scan.id, editingMask, blob);
      await refreshScan(token, scan.id);
      setMaskSuccess("Mask saved.");
      setEditingMask(null);
    } catch (err: any) {
      setMaskError(err?.message || "Failed to save mask");
    } finally {
      setMaskSaving(false);
    }
  }, [editingMask, exportMaskBlob, refreshScan, scan]);

  const handleMaskCancel = useCallback(() => {
    setEditingMask(null);
    setMaskError(null);
    setMaskSuccess(null);
  }, []);

  useEffect(() => {
    if (!editingMask || !imageSize || !scan) return;
    const canvas = maskCanvasRef.current;
    if (!canvas) return;
    canvas.width = imageSize.width;
    canvas.height = imageSize.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let cancelled = false;
    const loadMask = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;
      try {
        const blob = await getScanMask(token, scan.id, editingMask);
        if (!blob || cancelled) return;
        const url = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = () => {
          if (cancelled) {
            URL.revokeObjectURL(url);
            return;
          }
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          URL.revokeObjectURL(url);
        };
        img.onerror = () => {
          URL.revokeObjectURL(url);
        };
        img.src = url;
      } catch {
        // best-effort: leave blank canvas if the mask can't be loaded
      }
    };

    loadMask();

    return () => {
      cancelled = true;
    };
  }, [editingMask, imageSize, scan?.id]);

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading scan...</p>
      </main>
    );
  }

  if (error || !scan) {
    return (
      <main className="p-6 space-y-4">
        {error && (
          <div className="rounded-md border border-rose-500 bg-rose-500/10 p-4 text-rose-200">
            {error}
          </div>
        )}
        <Link href={detailBasePath} className="btn inline-block">
          ← Back to scans
        </Link>
      </main>
    );
  }

  const gradeAllowed = profile ? canGrade(profile.roles) : false;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <header className="space-y-2">
        <Link
          href={detailBasePath}
          className="text-sm text-blue-400 hover:underline"
        >
          ← Back to scans
        </Link>
        <h1 className="text-3xl font-bold text-white">{scan.capture_id}</h1>
        <p className="text-sm text-gray-400">
          Scan ID: {scan.scan_id ?? "n/a"} • Farm: {scan.farm_name ?? "Unknown"}
        </p>
      </header>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="card space-y-3">
          <h2 className="text-lg font-semibold text-white">Scan details</h2>
          <dl className="space-y-2 text-sm text-gray-300">
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Status</dt>
              <dd className="font-semibold capitalize">{scan.status}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Farm</dt>
              <dd>{scan.farm_name ?? "Unassigned"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Device</dt>
              <dd>{scan.device_label ?? scan.device_code ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Captured at</dt>
              <dd>{formatDateTime(scan.captured_at, { timeZone: farmTimeZone })}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Added at</dt>
              <dd>{formatDateTime(scan.created_at, { timeZone: browserTimeZone })}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Timezone</dt>
              <dd>
                Captured: {tzLabel(farmTimeZone)} • Added: {tzLabel(browserTimeZone)}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Reported grading</dt>
              <dd className="font-semibold">{scan.grading ?? "Not provided"}</dd>
            </div>
          </dl>
        </div>

        <div className="card space-y-3">
          <h2 className="text-lg font-semibold text-white">Latest grading</h2>
          {scan.latest_grading ? (
              <div className="space-y-2 text-sm text-gray-300">
                <div className="text-2xl font-semibold text-white">
                  {formatConfidence(scan.latest_grading.confidence)}
                </div>
                <div>
                Model:{" "}
                <span className="font-semibold">
                  {scan.latest_grading.model_name ?? "—"}@
                  {scan.latest_grading.model_version ?? "—"}
                </span>
              </div>
              <div>Completed: {formatDateTime(scan.latest_grading.created_at, { timeZone: farmTimeZone })}</div>
            </div>
          ) : scan.grading ? (
            <p className="text-sm text-emerald-200">Reported: {scan.grading}</p>
          ) : (
            <p className="text-sm text-gray-400">Awaiting grading</p>
          )}
        </div>
      </section>

      {scan && (
        <section className="grid gap-6 md:grid-cols-2">
          <div className="card space-y-4">
            <h2 className="text-lg font-semibold text-white">Scan metrics</h2>
            <dl className="grid gap-4 text-sm text-gray-300 sm:grid-cols-2">
              <div>
                <dt className="text-gray-400">IMF</dt>
                <dd className="text-xl font-semibold text-white">
                  {formatMetric(scan.imf)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-400">Backfat thickness</dt>
                <dd className="text-xl font-semibold text-white">
                  {formatMetric(scan.backfat_thickness)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-400">Animal weight</dt>
                <dd className="text-xl font-semibold text-white">
                  {formatMetric(scan.animal_weight)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-400">Ribeye area</dt>
                <dd className="text-xl font-semibold text-white">
                  {formatMetric(scan.ribeye_area)}
                </dd>
              </div>
            </dl>
            <div className="grid gap-4 border-t border-gray-800 pt-4 text-sm text-gray-300 sm:grid-cols-2">
              <div>
                <dt className="text-gray-400">Clarity</dt>
                <dd className="mt-1">
                  <QualityBadge value={scan.clarity} />
                </dd>
              </div>
              <div>
                <dt className="text-gray-400">Usability</dt>
                <dd className="mt-1">
                  <QualityBadge value={scan.usability} />
                </dd>
              </div>
            </div>
          </div>

          <div className="card space-y-4">
            <h2 className="text-lg font-semibold text-white">Review notes</h2>
            <form
              onSubmit={handleAttributesSubmit}
              className="space-y-3 text-sm text-gray-300"
            >
              <div>
                <label className="text-xs font-semibold uppercase text-gray-400">
                  Label
                </label>
                <input
                  type="text"
                  value={attributesForm.label}
                  onChange={(event) =>
                    setAttributesForm((prev) => ({
                      ...prev,
                      label: event.target.value,
                    }))
                  }
                  placeholder='e.g. "Flag" or "Review later"'
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold uppercase text-gray-400">
                    Clarity
                  </label>
                  <select
                    value={attributesForm.clarity}
                    onChange={(event) => {
                      const value = event.target
                        .value as "" | ScanQuality;
                      setAttributesForm((prev) => ({
                        ...prev,
                        clarity: value,
                      }));
                    }}
                    className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {QUALITY_OPTIONS.map((option) => (
                      <option key={option.value || "unset"} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase text-gray-400">
                    Usability
                  </label>
                  <select
                    value={attributesForm.usability}
                    onChange={(event) => {
                      const value = event.target
                        .value as "" | ScanQuality;
                      setAttributesForm((prev) => ({
                        ...prev,
                        usability: value,
                      }));
                    }}
                    className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {QUALITY_OPTIONS.map((option) => (
                      <option key={option.value || "unset"} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  disabled={attributesLoading}
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {attributesLoading ? "Saving..." : "Save changes"}
                </button>
                {attributesError && (
                  <span className="text-xs text-rose-300">{attributesError}</span>
                )}
                {attributesSuccess && (
                  <span className="text-xs text-emerald-300">
                    {attributesSuccess}
                  </span>
                )}
              </div>
            </form>
          </div>
        </section>
      )}

      {scan.image_url && (
        <section className="card space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-white">Image preview</h2>
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-xs font-semibold uppercase text-gray-400">
                  <input
                    type="checkbox"
                    checked={showMask}
                    onChange={(event) => setShowMask(event.target.checked)}
                    className="h-4 w-4 rounded border-gray-600 bg-gray-900 text-emerald-500 focus:ring-emerald-400"
                  />
                  Ribeye
                </label>
                {gradeAllowed && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingMask("ribeye");
                      setMaskError(null);
                      setMaskSuccess(null);
                    }}
                    className="rounded-md border border-gray-700 px-2 py-1 text-xs font-semibold uppercase text-gray-300 hover:border-gray-500"
                  >
                    {editingMask === "ribeye" ? "Editing" : "Edit"}
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-xs font-semibold uppercase text-gray-400">
                  <input
                    type="checkbox"
                    checked={showBackfatMask}
                    onChange={(event) => setShowBackfatMask(event.target.checked)}
                    className="h-4 w-4 rounded border-gray-600 bg-gray-900 text-emerald-500 focus:ring-emerald-400"
                  />
                  Backfat
                </label>
                {gradeAllowed && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingMask("backfat");
                      setMaskError(null);
                      setMaskSuccess(null);
                    }}
                    className="rounded-md border border-gray-700 px-2 py-1 text-xs font-semibold uppercase text-gray-300 hover:border-gray-500"
                  >
                    {editingMask === "backfat" ? "Editing" : "Edit"}
                  </button>
                )}
              </div>
            </div>
          </div>
          {editingMask && gradeAllowed && (
            <div className="flex flex-wrap items-center gap-3 rounded-md border border-gray-800 bg-gray-950/70 p-3">
              <span className="text-xs font-semibold uppercase text-gray-400">
                Editing {editingMask === "ribeye" ? "Ribeye" : "Backfat"} mask
              </span>
              <label className="flex items-center gap-2 text-xs font-semibold uppercase text-gray-400">
                Brush
                <input
                  type="range"
                  min={4}
                  max={80}
                  step={2}
                  value={brushSize}
                  onChange={(event) => setBrushSize(Number(event.target.value))}
                />
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setBrushMode("add")}
                  className={`rounded-md px-2 py-1 text-xs font-semibold uppercase ${
                    brushMode === "add"
                      ? "bg-emerald-500 text-black"
                      : "border border-gray-700 text-gray-300"
                  }`}
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => setBrushMode("erase")}
                  className={`rounded-md px-2 py-1 text-xs font-semibold uppercase ${
                    brushMode === "erase"
                      ? "bg-rose-500 text-black"
                      : "border border-gray-700 text-gray-300"
                  }`}
                >
                  Erase
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleMaskSave}
                  disabled={maskSaving}
                  className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-semibold uppercase text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {maskSaving ? "Saving..." : "Save"}
                </button>
                <button
                  type="button"
                  onClick={handleMaskCancel}
                  className="rounded-md border border-gray-700 px-3 py-1 text-xs font-semibold uppercase text-gray-300 hover:border-gray-500"
                >
                  Cancel
                </button>
              </div>
              {maskError && <span className="text-xs text-rose-300">{maskError}</span>}
              {maskSuccess && (
                <span className="text-xs text-emerald-300">{maskSuccess}</span>
              )}
            </div>
          )}
          <div className="relative overflow-hidden rounded-md border border-gray-800 bg-black flex justify-center">
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                ref={imageRef}
                src={scan.image_url}
                alt={`Scan ${scan.capture_id}`}
                className="block max-h-[420px] max-w-full"
                onLoad={handleImageLoad}
              />
              {showMask && scan.mask_url && editingMask !== "ribeye" && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={scan.mask_url}
                  alt=""
                  className="pointer-events-none absolute inset-0 h-full w-full mix-blend-screen opacity-60"
                  style={{
                    filter: "sepia(1) saturate(8) hue-rotate(80deg)",
                  }}
                />
              )}
              {showBackfatMask && scan.backfat_line_url && editingMask !== "backfat" && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={scan.backfat_line_url}
                  alt=""
                  className="pointer-events-none absolute inset-0 h-full w-full mix-blend-screen opacity-60"
                  style={{
                    filter: "sepia(1) saturate(8) hue-rotate(80deg)",
                  }}
                />
              )}
              {editingMask && (
                <canvas
                  ref={maskCanvasRef}
                  className="absolute inset-0 h-full w-full cursor-crosshair mix-blend-screen opacity-60"
                  style={{ filter: "sepia(1) saturate(8) hue-rotate(80deg)", touchAction: "none" }}
                  onPointerDown={handleMaskPointerDown}
                  onPointerMove={handleMaskPointerMove}
                  onPointerUp={handleMaskPointerUp}
                  onPointerLeave={handleMaskPointerUp}
                />
              )}
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Served via temporary signed URL. Refresh the page to generate a new one
            if expired.
          </p>
        </section>
      )}

      <section className="card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Grading history</h2>
          {gradeAllowed && (
            <form
              onSubmit={handleGradeSubmit}
              className="flex flex-col gap-3 rounded-md border border-gray-800 bg-gray-950/70 p-4 md:flex-row md:items-end"
            >
              <div className="flex-1">
                <label
                  htmlFor="model-name"
                  className="text-xs font-semibold uppercase text-gray-400"
                >
                  Model name
                </label>
                <input
                  id="model-name"
                  type="text"
                  value={gradeForm.model_name}
                  onChange={(event) =>
                    setGradeForm((prev) => ({
                      ...prev,
                      model_name: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label
                  htmlFor="model-version"
                  className="text-xs font-semibold uppercase text-gray-400"
                >
                  Version
                </label>
                <input
                  id="model-version"
                  type="text"
                  value={gradeForm.model_version}
                  onChange={(event) =>
                    setGradeForm((prev) => ({
                      ...prev,
                      model_version: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label
                  htmlFor="confidence"
                  className="text-xs font-semibold uppercase text-gray-400"
                >
                  Confidence (0-1)
                </label>
                <input
                  id="confidence"
                  type="number"
                  min="0"
                  max="1"
                  step="0.0001"
                  value={gradeForm.confidence}
                  onChange={(event) =>
                    setGradeForm((prev) => ({
                      ...prev,
                      confidence: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                type="submit"
                disabled={gradeLoading}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {gradeLoading ? "Grading..." : "Run grading"}
              </button>
            </form>
          )}
        </div>

        {gradeError && (
          <div className="rounded-md border border-rose-500 bg-rose-500/10 p-3 text-sm text-rose-200">
            {gradeError}
          </div>
        )}

        {gradeSuccess && (
          <div className="rounded-md border border-emerald-500 bg-emerald-500/10 p-3 text-sm text-emerald-200">
            {gradeSuccess}
          </div>
        )}

        {scan.grading_results.length === 0 ? (
          <p className="text-sm text-gray-400">No grading runs yet.</p>
        ) : (
          <div className="space-y-4">
            {scan.grading_results.map((result) => (
              <div
                key={result.id}
                className="rounded-md border border-gray-800 bg-gray-950/60 p-4"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {result.model_name}@{result.model_version}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatDateTime(result.created_at, { timeZone: farmTimeZone })}
                    </p>
                  </div>
                  <div className="text-right text-sm text-gray-300">
                    Confidence:{" "}
                    <span className="font-semibold text-white">
                      {formatConfidence(result.confidence)}
                    </span>
                  </div>
                </div>
                {result.confidence_breakdown && (
                  <div className="mt-3 space-y-1 text-xs text-gray-400">
                    <p className="font-semibold text-gray-300">Confidence breakdown</p>
                    <ul className="grid grid-cols-2 gap-x-4 gap-y-1">
                      {Object.entries(result.confidence_breakdown).map(
                        ([label, value]) => (
                          <li key={label} className="flex justify-between">
                            <span>{label}</span>
                            <span>{(value * 100).toFixed(1)}%</span>
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}
                {result.features_used && (
                  <div className="mt-3 space-y-1 text-xs text-gray-400">
                    <p className="font-semibold text-gray-300">Features used</p>
                    <ul className="grid grid-cols-2 gap-x-4 gap-y-1">
                      {Object.entries(result.features_used).map(
                        ([label, value]) => (
                          <li key={label} className="flex justify-between">
                            <span>{label}</span>
                            <span>{value.toFixed(3)}</span>
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}
                <div className="mt-3 text-xs text-gray-500">
                  Operator: {result.created_by_email ?? "system"}
                  {result.created_by_name && ` (${result.created_by_name})`}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Scan edit</h2>
          <button
            type="button"
            onClick={() => setEditOpen((prev) => !prev)}
            className="rounded-md border border-gray-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-gray-800"
          >
            {editOpen ? "Hide" : "Show"}
          </button>
        </div>
        {editOpen && (
          <div className="space-y-3">
            {deleteError && (
              <div className="rounded-md border border-rose-500 bg-rose-500/10 p-2 text-xs text-rose-200">
                {deleteError}
              </div>
            )}
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleteLoading}
              className="rounded-md border border-rose-500 px-4 py-2 text-sm font-semibold text-rose-100 hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {deleteLoading ? "Deleting..." : "Delete scan"}
            </button>
            <p className="text-xs text-gray-500">
              Deletes this scan plus its events, grading records, and assets. Animals/groups remain unchanged.
            </p>
          </div>
        )}
      </section>

      <section className="card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Assignment</h2>
          <button
            type="button"
            onClick={() => setAssignmentOpen((prev) => !prev)}
            className="rounded-md border border-gray-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-gray-800"
          >
            {assignmentOpen ? "Hide" : "Show"}
          </button>
        </div>
        {assignmentOpen && (
          <form onSubmit={handleAssignmentSubmit} className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm text-gray-400" htmlFor="assignment-farm">
                Farm
              </label>
              <select
                id="assignment-farm"
                value={assignmentForm.farm_id}
                onChange={(e) =>
                  setAssignmentForm((prev) => ({
                    ...prev,
                    farm_id: e.target.value,
                    // clear group if farm changes
                    group_id: prev.group_id && groups.find((g) => g.id === prev.group_id && g.farm_id === e.target.value)
                      ? prev.group_id
                      : "",
                  }))
                }
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Unassigned</option>
                {farms.map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Current: {scan.farm_name ?? "Unassigned"}
              </p>
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="assignment-group">
                Group
              </label>
              <select
                id="assignment-group"
                value={assignmentForm.group_id}
                onChange={(e) =>
                  setAssignmentForm((prev) => ({
                    ...prev,
                    group_id: e.target.value,
                  }))
                }
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Unassigned</option>
                {groupedOptions.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                    {group.farm_name ? ` • ${group.farm_name}` : ""}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Current: {scan.group_name ?? "Unassigned"}
              </p>
            </div>
            <div className="md:col-span-2 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={assignmentLoading}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {assignmentLoading ? "Saving..." : "Save assignment"}
              </button>
              {assignmentError && (
                <span className="text-xs text-rose-300">{assignmentError}</span>
              )}
              {assignmentStatus && (
                <span className="text-xs text-emerald-300">{assignmentStatus}</span>
              )}
            </div>
          </form>
        )}
      </section>
    </main>
  );
}
