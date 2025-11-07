"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getScanStats,
  listScans,
  me,
  type PaginatedScans,
  type Profile,
  type Scan,
  type ScanStats,
  type ScanStatus,
} from "@/lib/api";

type Role = "admin" | "technician" | "farmer";
type StatusFilter = "all" | ScanStatus;

const STATUS_LABELS: Record<ScanStatus, string> = {
  uploaded: "Uploaded",
  ingested: "Ingested",
  graded: "Graded",
  error: "Error",
};

const STATUS_CLASSES: Record<ScanStatus, string> = {
  uploaded: "bg-sky-500/20 text-sky-300 border border-sky-500/40",
  ingested: "bg-indigo-500/20 text-indigo-200 border border-indigo-500/40",
  graded: "bg-emerald-500/20 text-emerald-200 border border-emerald-500/40",
  error: "bg-rose-500/20 text-rose-200 border border-rose-500/40",
};

const STATUS_ORDER: ScanStatus[] = ["uploaded", "ingested", "graded", "error"];
const PER_PAGE = 25;

const hasRoleAccess = (role: Role, roles: string[]): boolean => {
  if (role === "admin") return roles.includes("admin");
  if (roles.includes("admin")) return true;
  return roles.includes(role);
};

const formatDate = (value?: string | null) =>
  value ? new Date(value).toLocaleString() : "—";

const formatConfidence = (value?: number | null) => {
  if (value === undefined || value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
};

function StatusBadge({ status }: { status: ScanStatus }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${
        STATUS_CLASSES[status]
      }`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

function StatsSummary({ stats }: { stats: ScanStats | null }) {
  if (!stats) return null;

  return (
    <section className="grid gap-4 md:grid-cols-3">
      <div className="card">
        <h3 className="text-sm font-medium text-gray-400">Total scans</h3>
        <p className="mt-2 text-3xl font-bold text-white">{stats.total}</p>
      </div>
      <div className="card">
        <h3 className="text-sm font-medium text-gray-400">Last 24 hours</h3>
        <p className="mt-2 text-3xl font-bold text-white">{stats.recent_count}</p>
      </div>
      <div className="card">
        <h3 className="text-sm font-medium text-gray-400">Status breakdown</h3>
        <ul className="mt-2 space-y-1 text-sm text-gray-300">
          {STATUS_ORDER.map((status) => (
            <li key={status} className="flex items-center justify-between">
              <span>{STATUS_LABELS[status]}</span>
              <span className="font-semibold">
                {stats.by_status?.[status] ?? 0}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default function ScanListPage({ role }: { role: Role }) {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [scans, setScans] = useState<Scan[]>([]);
  const [pageMeta, setPageMeta] = useState<
    Pick<PaginatedScans, "page" | "per_page" | "total" | "total_pages">
  >({
    page: 1,
    per_page: PER_PAGE,
    total: 0,
    total_pages: 1,
  });
  const [stats, setStats] = useState<ScanStats | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [labelInput, setLabelInput] = useState("");
  const [appliedLabel, setAppliedLabel] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const statusOptions = useMemo<StatusFilter[]>(() => {
    return ["all", ...STATUS_ORDER];
  }, []);

  const basePath = useMemo(() => `/dashboard/${role}/scans`, [role]);

  const loadData = useCallback(
    async (nextStatus: StatusFilter, nextPage: number, labelValue: string) => {
      setStatusFilter(nextStatus);
      setPageMeta((prev) => ({ ...prev, page: nextPage }));
      setLoading(true);
      try {
        const token = localStorage.getItem("token");
        if (!token) throw new Error("Not logged in");
        const params: Record<string, string | number> = {
          page: nextPage,
          per_page: PER_PAGE,
        };
        if (nextStatus !== "all") {
          params.status = nextStatus;
        }
        if (labelValue) {
          params.label = labelValue;
        }

        const [statsData, listData] = await Promise.all([
          getScanStats(token),
          listScans(token, params),
        ]);
        setStats(statsData);
        setScans(listData.scans);
        setPageMeta({
          page: listData.page,
          per_page: listData.per_page,
          total: listData.total,
          total_pages: Math.max(listData.total_pages, 1),
        });
        setError(null);
      } catch (err: any) {
        setError(err?.message || "Failed to load scans");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          setError("Not logged in");
          router.push("/login");
          return;
        }
        const profileData = await me(token);
        if (!hasRoleAccess(role, profileData.roles)) {
          router.replace("/dashboard");
          return;
        }
        setProfile(profileData);
        await loadData("all", 1, "");
      } catch (err: any) {
        setError(err?.message || "Failed to load scans");
      }
    })();
  }, [loadData, role, router]);

  const handleStatusChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value as StatusFilter;
    void loadData(value, 1, appliedLabel);
  };

  const handleRefresh = () =>
    void loadData(statusFilter, pageMeta.page, appliedLabel);

  const goToPage = (nextPage: number) => {
    if (nextPage < 1 || nextPage > pageMeta.total_pages) return;
    void loadData(statusFilter, nextPage, appliedLabel);
  };

  const handleLabelSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = labelInput.trim();
    setAppliedLabel(trimmed);
    void loadData(statusFilter, 1, trimmed);
  };

  const handleLabelClear = () => {
    setLabelInput("");
    setAppliedLabel("");
    void loadData(statusFilter, 1, "");
  };

  if (error) {
    return (
      <main className="p-6">
        <div className="rounded-md border border-rose-500 bg-rose-500/10 p-4 text-rose-200">
          {error}
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Scans</h1>
          <p className="mt-1 text-sm text-gray-400">
            Role-aware scan list with grading summaries.
          </p>
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <form
            onSubmit={handleLabelSubmit}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={labelInput}
              placeholder="Filter by label"
              onChange={(event) => setLabelInput(event.target.value)}
              className="rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white hover:bg-gray-800"
            >
              Apply
            </button>
            <button
              type="button"
              onClick={handleLabelClear}
              disabled={!appliedLabel}
              className="rounded-md border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Reset
            </button>
          </form>
          <select
            className="rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={statusFilter}
            onChange={handleStatusChange}
          >
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {option === "all" ? "All statuses" : STATUS_LABELS[option]}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleRefresh}
            className="rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white hover:bg-gray-800"
          >
            Refresh
          </button>
        </div>
      </header>

      <StatsSummary stats={stats} />

      <section className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-800 text-sm">
            <thead className="bg-gray-900 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
              <tr>
                <th className="px-4 py-3">Capture</th>
                <th className="px-4 py-3">Farm</th>
                <th className="px-4 py-3">Device</th>
                 <th className="px-4 py-3">Label</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Latest grading</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-gray-400">
                    Loading scans...
                  </td>
                </tr>
              ) : scans.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-gray-400">
                    No scans found for the selected filters.
                  </td>
                </tr>
              ) : (
                scans.map((scan) => {
                  const latest = scan.latest_grading;
                  return (
                    <tr key={scan.id}>
                      <td className="px-4 py-4">
                        <div className="font-medium text-white">
                          {scan.capture_id}
                        </div>
                        <div className="text-xs text-gray-400">
                          ID: {scan.scan_id ?? "—"}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="font-medium">
                          {scan.farm_name ?? "Unassigned"}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div>{scan.device_label ?? scan.device_code ?? "—"}</div>
                        <div className="text-xs text-gray-500">
                          Device ID: {scan.device_id}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        {scan.label ? (
                          <span className="rounded-full bg-amber-500/10 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-amber-300">
                            {scan.label}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-500">—</span>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge status={scan.status} />
                      </td>
                      <td className="px-4 py-4">
                        {latest ? (
                          <div>
                            <div className="font-semibold text-white">
                              {formatConfidence(latest.confidence)}
                            </div>
                            <div className="text-xs text-gray-400">
                              {latest.model_name ?? "—"}@
                              {latest.model_version ?? "—"}
                            </div>
                            <div className="text-xs text-gray-500">
                              {formatDate(latest.created_at)}
                            </div>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-500">
                            Awaiting grading
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-400">
                        {formatDate(scan.created_at)}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <Link
                          href={`${basePath}/${scan.id}`}
                          className="inline-flex items-center rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {!loading && pageMeta.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-gray-800 bg-gray-950/60 px-4 py-3 text-sm text-gray-300">
            <span>
              Page {pageMeta.page} of {pageMeta.total_pages} • {pageMeta.total}{" "}
              total
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded-md border border-gray-700 px-3 py-1.5 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => goToPage(pageMeta.page - 1)}
                disabled={pageMeta.page <= 1}
              >
                Previous
              </button>
              <button
                type="button"
                className="rounded-md border border-gray-700 px-3 py-1.5 hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => goToPage(pageMeta.page + 1)}
                disabled={pageMeta.page >= pageMeta.total_pages}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>

      {profile && (
        <p className="text-xs text-gray-500">
          Signed in as {profile.email} ({profile.roles.join(", ")})
        </p>
      )}
    </main>
  );
}
