"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  gradeScan,
  getScan,
  me,
  type GradeScanPayload,
  type Profile,
  type ScanDetail,
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

type GradeFormState = {
  model_name: string;
  model_version: string;
  confidence: string;
};

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

      {scan.image_url && (
        <section className="card space-y-3">
          <h2 className="text-lg font-semibold text-white">Image preview</h2>
          <div className="overflow-hidden rounded-md border border-gray-800">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={scan.image_url}
              alt={`Scan ${scan.capture_id}`}
              className="w-full max-h-[420px] object-contain bg-black"
            />
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
