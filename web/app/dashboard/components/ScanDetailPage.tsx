"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  gradeScan,
  getScan,
  me,
  updateScanAttributes,
  type GradeScanPayload,
  type Profile,
  type ScanDetail,
  type ScanQuality,
  type UpdateScanAttributesPayload,
} from "@/lib/api";
import type { Role } from "@/lib/roles";

const canGrade = (roles: string[]): boolean =>
  roles.includes("admin") || roles.includes("technician");

const formatDateTime = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : "—";

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

export default function ScanDetailPage({ role }: { role: Role }) {
  const params = useParams<{ scanId: string }>();
  const scanId = params?.scanId;
  const router = useRouter();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [gradeForm, setGradeForm] = useState<GradeFormState>({
    model_name: "cti-sim",
    model_version: "1.0.0",
    confidence: "",
  });
  const [gradeLoading, setGradeLoading] = useState(false);
  const [gradeError, setGradeError] = useState<string | null>(null);
  const [gradeSuccess, setGradeSuccess] = useState<string | null>(null);
  const [showMask, setShowMask] = useState(false);
  const [attributesForm, setAttributesForm] = useState<AttributesFormState>({
    label: "",
    clarity: "",
    usability: "",
  });
  const [attributesLoading, setAttributesLoading] = useState(false);
  const [attributesError, setAttributesError] = useState<string | null>(null);
  const [attributesSuccess, setAttributesSuccess] = useState<string | null>(null);

  const detailBasePath = useMemo(() => `/dashboard/${role}/scans`, [role]);

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
      setShowMask(false);
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
              <dd>{formatDateTime(scan.captured_at)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-gray-400">Created</dt>
              <dd>{formatDateTime(scan.created_at)}</dd>
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
              <div>Completed: {formatDateTime(scan.latest_grading.created_at)}</div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No grading results yet.</p>
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
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Image preview</h2>
            {scan.mask_url && (
              <label className="flex items-center gap-2 text-xs font-semibold uppercase text-gray-400">
                <input
                  type="checkbox"
                  checked={showMask}
                  onChange={(event) => setShowMask(event.target.checked)}
                  className="h-4 w-4 rounded border-gray-600 bg-gray-900 text-emerald-500 focus:ring-emerald-400"
                />
                Highlight mask
              </label>
            )}
          </div>
          <div className="relative overflow-hidden rounded-md border border-gray-800 bg-black">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={scan.image_url}
              alt={`Scan ${scan.capture_id}`}
              className="w-full max-h-[420px] object-contain"
            />
            {showMask && scan.mask_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={scan.mask_url}
                alt=""
                className="pointer-events-none absolute inset-0 h-full w-full object-contain mix-blend-screen opacity-60"
                style={{
                  filter: "invert(1) sepia(1) saturate(8) hue-rotate(80deg)",
                }}
              />
            )}
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
                      {formatDateTime(result.created_at)}
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
    </main>
  );
}
