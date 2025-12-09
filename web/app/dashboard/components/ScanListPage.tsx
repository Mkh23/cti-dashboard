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
  const [filters, setFilters] = useState({
    capture: "",
    farm_id: "",
    status: "all" as StatusFilter,
    created_from: "",
    created_to: "",
    latest_grading: "",
    device_id: "",
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const statusOptions = useMemo<StatusFilter[]>(() => ["all", ...STATUS_ORDER], []);
  const farmOptions = useMemo(() => {
    const ids = new Map<string, string>();
    scans.forEach((scan) => {
      if (scan.farm_id && scan.farm_name) {
        ids.set(scan.farm_id, scan.farm_name);
      }
    });
    return Array.from(ids.entries()).map(([id, name]) => ({ id, name }));
  }, [scans]);

  const deviceOptions = useMemo(() => {
    const devices = new Map<string, string>();
    scans.forEach((scan) => {
      if (scan.device_id) {
        devices.set(scan.device_id, scan.device_label ?? scan.device_code ?? scan.device_id);
      }
    });
    return Array.from(devices.entries()).map(([id, label]) => ({ id, label }));
  }, [scans]);

  const gradingOptions = useMemo(() => {
    const grades = new Set<string>();
    scans.forEach((scan) => {
      if (scan.latest_grading?.model_name) {
        grades.add(scan.latest_grading.model_name);
      } else if (scan.grading) {
        grades.add(scan.grading);
      }
    });
    return Array.from(grades);
  }, [scans]);

  const basePath = useMemo(() => `/dashboard/${role}/scans`, [role]);

  const loadData = useCallback(
    async (nextFilters: typeof appliedFilters, nextPage: number) => {
      setPageMeta((prev) => ({ ...prev, page: nextPage }));
      setLoading(true);
      try {
        const token = localStorage.getItem("token");
        if (!token) throw new Error("Not logged in");
        const params: Record<string, string | number> = {
          page: nextPage,
          per_page: PER_PAGE,
        };
        if (nextFilters.status !== "all") params.status = nextFilters.status;
        if (nextFilters.capture) params.capture = nextFilters.capture;
        if (nextFilters.farm_id) params.farm_id = nextFilters.farm_id;
        if (nextFilters.created_from) params.created_from = nextFilters.created_from;
        if (nextFilters.created_to) params.created_to = nextFilters.created_to;
        if (nextFilters.latest_grading) params.latest_grading = nextFilters.latest_grading;
        if (nextFilters.device_id) params.device_id = nextFilters.device_id;

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
        setAppliedFilters((prev) => prev); // keep applied state
        await loadData(appliedFilters, 1);
      } catch (err: any) {
        setError(err?.message || "Failed to load scans");
      }
    })();
  }, [appliedFilters, loadData, role, router]);

  const handleApplyFilters = () => {
    setAppliedFilters(filters);
    void loadData(filters, 1);
  };

  const handleClearFilters = () => {
    const cleared = {
      capture: "",
      farm_id: "",
      status: "all" as StatusFilter,
      created_from: "",
      created_to: "",
      latest_grading: "",
      device_id: "",
    };
    setFilters(cleared);
    setAppliedFilters(cleared);
    void loadData(cleared, 1);
  };

  const handleRefresh = () => void loadData(appliedFilters, pageMeta.page);

  const goToPage = (nextPage: number) => {
    if (nextPage < 1 || nextPage > pageMeta.total_pages) return;
    void loadData(appliedFilters, nextPage);
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
        <button
          type="button"
          onClick={handleRefresh}
          className="rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white hover:bg-gray-800"
        >
          Refresh
        </button>
      </header>

      <StatsSummary stats={stats} />

      <section className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Filter scans</h2>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded-md border border-gray-700 px-4 py-2 text-sm text-white hover:bg-gray-800"
              onClick={() => setFiltersOpen((prev) => !prev)}
            >
              {filtersOpen ? "Hide" : "Show"}
            </button>
          </div>
        </div>
        {filtersOpen && (
          <>
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-capture">Capture</label>
                <input
                  id="filter-capture"
                  type="text"
                  value={filters.capture}
                  onChange={(e) => setFilters((prev) => ({ ...prev, capture: e.target.value }))}
                  placeholder="Search capture id"
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-farm">Farm</label>
                <select
                  id="filter-farm"
                  value={filters.farm_id}
                  onChange={(e) => setFilters((prev) => ({ ...prev, farm_id: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All</option>
                  {farmOptions.map((farm) => (
                    <option key={farm.id} value={farm.id}>
                      {farm.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-status">Status</label>
                <select
                  id="filter-status"
                  value={filters.status}
                  onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value as StatusFilter }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {statusOptions.map((option) => (
                    <option key={option} value={option}>
                      {option === "all" ? "All statuses" : STATUS_LABELS[option]}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-created-from">Created from</label>
                <input
                  id="filter-created-from"
                  type="date"
                  value={filters.created_from}
                  onChange={(e) => setFilters((prev) => ({ ...prev, created_from: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-created-to">Created to</label>
                <input
                  id="filter-created-to"
                  type="date"
                  value={filters.created_to}
                  onChange={(e) => setFilters((prev) => ({ ...prev, created_to: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-grading">Latest grading</label>
                <select
                  id="filter-grading"
                  value={filters.latest_grading}
                  onChange={(e) => setFilters((prev) => ({ ...prev, latest_grading: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All</option>
                  {gradingOptions.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-device">Device</label>
                <select
                  id="filter-device"
                  value={filters.device_id}
                  onChange={(e) => setFilters((prev) => ({ ...prev, device_id: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All</option>
                  {deviceOptions.map((device) => (
                    <option key={device.id} value={device.id}>
                      {device.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleApplyFilters}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
              >
                Apply filters
              </button>
            </div>
          </>
        )}
      </section>

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
                  const reportedGrade = scan.grading;
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
                        ) : reportedGrade ? (
                          <span className="text-sm text-emerald-200">
                            Reported: {reportedGrade}
                          </span>
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
