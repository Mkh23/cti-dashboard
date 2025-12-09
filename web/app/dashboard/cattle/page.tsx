"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import {
  createCattle,
  listCattle,
  listFarms,
  me,
  type Cattle,
  type Farm,
  type Profile,
  updateCattle,
} from "@/lib/api";

const ROLE_SET = new Set(["admin", "technician", "farmer"]);

function CattleManagerContent() {
  const searchParams = useSearchParams();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [cattle, setCattle] = useState<Cattle[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [filters, setFilters] = useState({ farm_id: "", born_from: "", born_to: "", name: "" });
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    external_id: "",
    born_date: "",
    farm_id: "",
  });

  const canManage = profile?.roles?.some((role) => ROLE_SET.has(role)) ?? false;
  const farmFilter = useMemo(() => searchParams?.get("farm_id") || undefined, [searchParams]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");

      const [profileResp, farmsResp, cattleResp] = await Promise.all([
        me(token),
        listFarms(token),
        listCattle(token, filters.farm_id || farmFilter, {
          born_from: filters.born_from || undefined,
          born_to: filters.born_to || undefined,
          name: filters.name || undefined,
        }),
      ]);
      setProfile(profileResp);
      setFarms(farmsResp);
      setCattle(cattleResp);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Failed to load cattle");
    } finally {
      setLoading(false);
    }
  }, [farmFilter, filters]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!profile) return;
    const isAdmin = profile.roles.includes("admin");
    if (isAdmin) return;
    if (!form.farm_id && farms.length > 0) {
      setForm((prev) => ({ ...prev, farm_id: farms[0].id }));
    }
  }, [profile, farms, form.farm_id]);

  const resetForm = () =>
    setForm({
      name: "",
      external_id: "",
      born_date: "",
      farm_id: "",
    });

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const payload = {
        name: form.name.trim(),
        external_id: form.external_id.trim() || undefined,
        born_date: form.born_date || undefined,
        farm_id: form.farm_id || undefined,
      };
      if (editingId) {
        await updateCattle(token, editingId, payload);
      } else {
        await createCattle(token, payload);
      }
      resetForm();
      setEditingId(null);
      setFormOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to save cattle");
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading cattle...</p>
      </main>
    );
  }

  if (error && !profile) {
    return (
      <main className="p-6 space-y-4">
        <div className="rounded-md border border-red-500 bg-red-900/20 p-4 text-red-200">
          {error}
        </div>
        <Link href="/dashboard" className="btn inline-block">
          Back to dashboard
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Cattle</h1>
          <p className="mt-2 text-sm text-gray-400">
            Define cattle groups and associate them with farms for scan assignments.
          </p>
        </div>
        <Link href="/dashboard" className="text-sm text-blue-400 hover:underline">
          ← Back to dashboard
        </Link>
      </div>

      {error && (
        <div className="rounded-md border border-red-500 bg-red-900/20 p-4 text-red-200">
          {error}
        </div>
      )}

      {canManage && (
        <section className="card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">
                {editingId ? "Edit cattle group" : "Create a cattle group"}
              </h2>
              <p className="text-sm text-gray-500">Add or edit cattle groups.</p>
            </div>
            <button
              type="button"
              onClick={() => {
                setFormOpen((prev) => !prev);
                if (formOpen) {
                  resetForm();
                  setEditingId(null);
                }
              }}
              className="rounded-md border border-gray-700 px-4 py-2 text-sm text-white hover:bg-gray-800"
            >
              {formOpen ? "Hide" : "Show"}
            </button>
          </div>
          {formOpen && (
            <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-1">
                <label className="text-sm text-gray-400" htmlFor="cattle-name">
                  Name
                </label>
                <input
                  id="cattle-name"
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Herd name"
                  required
                />
              </div>
              <div className="md:col-span-1">
                <label className="text-sm text-gray-400" htmlFor="cattle-external">
                  External ID
                </label>
                <input
                  id="cattle-external"
                  type="text"
                  value={form.external_id}
                  onChange={(e) => setForm((prev) => ({ ...prev, external_id: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Optional identifier"
                />
              </div>
              <div className="md:col-span-1">
                <label className="text-sm text-gray-400" htmlFor="cattle-born-date">
                  Born date
                </label>
                <input
                  id="cattle-born-date"
                  type="date"
                  value={form.born_date}
                  onChange={(e) => setForm((prev) => ({ ...prev, born_date: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="md:col-span-1">
                <label className="text-sm text-gray-400" htmlFor="cattle-farm">
                  Farm
                </label>
                <select
                  id="cattle-farm"
                  value={form.farm_id}
                  onChange={(e) => setForm((prev) => ({ ...prev, farm_id: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Unassigned</option>
                  {farms.map((farm) => (
                    <option key={farm.id} value={farm.id}>
                      {farm.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2 flex justify-end">
                {editingId && (
                  <button
                    type="button"
                    onClick={() => {
                      resetForm();
                      setEditingId(null);
                      setFormOpen(false);
                    }}
                    className="mr-3 rounded-md border border-gray-600 px-6 py-2 text-sm text-gray-300 hover:bg-gray-800"
                  >
                    Cancel
                  </button>
                )}
                <button
                  type="submit"
                  disabled={creating || !form.name.trim()}
                  className="rounded-md bg-blue-600 px-6 py-2 text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {creating ? "Saving..." : editingId ? "Update cattle" : "Save cattle"}
                </button>
              </div>
            </form>
          )}
        </section>
      )}

      <section className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Filter cattle</h2>
          <button
            type="button"
            className="rounded-md border border-gray-700 px-4 py-2 text-sm text-white hover:bg-gray-800"
            onClick={() => setFiltersOpen((prev) => !prev)}
          >
            {filtersOpen ? "Hide" : "Show"}
          </button>
        </div>
        {filtersOpen && (
          <>
            <div className="grid gap-3 md:grid-cols-4">
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-name">Cattle</label>
                <input
                  id="filter-name"
                  type="text"
                  value={filters.name}
                  onChange={(e) => setFilters((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Name contains..."
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
                  {farms.map((farm) => (
                    <option key={farm.id} value={farm.id}>
                      {farm.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-born-from">Born from</label>
                <input
                  id="filter-born-from"
                  type="date"
                  value={filters.born_from}
                  onChange={(e) => setFilters((prev) => ({ ...prev, born_from: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400" htmlFor="filter-born-to">Born to</label>
                <input
                  id="filter-born-to"
                  type="date"
                  value={filters.born_to}
                  onChange={(e) => setFilters((prev) => ({ ...prev, born_to: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => void loadData()}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
              >
                Apply filters
              </button>
            </div>
          </>
        )}
      </section>

      <section className="card">
        <div className="flex items-center justify-between pb-4">
          <h2 className="text-xl font-semibold text-white">Cattle list</h2>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            {farmFilter && <span>Filtered by farm</span>}
            <span>{cattle.length} total</span>
          </div>
        </div>
        {cattle.length === 0 ? (
          <p className="py-8 text-center text-gray-500">No cattle defined yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-800 text-sm">
              <thead className="bg-gray-900 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">External ID</th>
                  <th className="px-4 py-3">Born date</th>
                  <th className="px-4 py-3">Farm</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800 text-gray-200">
                {cattle.map((herd) => {
                  const bornDate = herd.born_date
                    ? new Date(herd.born_date).toLocaleDateString()
                    : "—";
                  return (
                    <tr key={herd.id}>
                      <td className="px-4 py-3 font-semibold text-white">
                        <Link href={`/dashboard/cattle/${herd.id}`} className="hover:text-emerald-300">
                          {herd.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-gray-400">{herd.external_id || "—"}</td>
                      <td className="px-4 py-3 text-gray-400">{bornDate}</td>
                      <td className="px-4 py-3 text-gray-300">{herd.farm_name || "Unassigned"}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          className="text-sm text-blue-400 hover:underline"
                          onClick={() => {
                            setEditingId(herd.id);
                            setForm({
                              name: herd.name,
                              external_id: herd.external_id || "",
                              born_date: herd.born_date || "",
                              farm_id: herd.farm_id || "",
                            });
                          }}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

export default function CattleManagerPage() {
  return (
    <Suspense fallback={<main className="p-6"><p>Loading cattle...</p></main>}>
      <CattleManagerContent />
    </Suspense>
  );
}
