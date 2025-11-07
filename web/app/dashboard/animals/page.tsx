"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import {
  createAnimal,
  listAnimals,
  listCattle,
  listFarms,
  me,
  updateAnimal,
  deleteAnimal,
  type Animal,
  type Cattle,
  type Farm,
  type Profile,
} from "@/lib/api";

const ROLE_SET = new Set(["admin", "technician", "farmer"]);

export default function AnimalsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [cattle, setCattle] = useState<Cattle[]>([]);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    tag_id: "",
    rfid: "",
    breed: "",
    sex: "",
    born_date: "",
    farm_id: "",
    cattle_id: "",
  });

  const canManage = profile?.roles?.some((role) => ROLE_SET.has(role)) ?? false;

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const [profileResp, farmsResp, cattleResp, animalsResp] = await Promise.all([
        me(token),
        listFarms(token),
        listCattle(token),
        listAnimals(token),
      ]);
      setProfile(profileResp);
      setFarms(farmsResp);
      setCattle(cattleResp);
      setAnimals(animalsResp);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Failed to load animals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const preferredFarmId = useMemo(() => {
    if (profile?.roles.includes("admin")) return form.farm_id;
    if (form.farm_id) return form.farm_id;
    return farms[0]?.id || "";
  }, [form.farm_id, farms, profile]);

  const resetForm = () =>
    setForm({
      tag_id: "",
      rfid: "",
      breed: "",
      sex: "",
      born_date: "",
      farm_id: "",
      cattle_id: "",
    });

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.tag_id.trim()) return;
    setSaving(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const payload = {
        tag_id: form.tag_id.trim(),
        rfid: form.rfid.trim() || undefined,
        breed: form.breed.trim() || undefined,
        sex: form.sex.trim() || undefined,
        birth_date: form.born_date || undefined,
        farm_id: form.farm_id || undefined,
        cattle_id: form.cattle_id || undefined,
      };
      if (editingId) {
        await updateAnimal(token, editingId, payload);
      } else {
        await createAnimal(token, payload);
      }
      resetForm();
      setEditingId(null);
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to save animal");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (animalId: string) => {
    if (!confirm("Are you sure you want to delete this animal?")) return;
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      await deleteAnimal(token, animalId);
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to delete animal");
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading animals...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Animals</h1>
          <p className="mt-2 text-sm text-gray-400">
            Maintain animal records, RFIDs, and cattle assignments for your farms.
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
          <h2 className="text-xl font-semibold text-white">
            {editingId ? "Update animal" : "Register animal"}
          </h2>
          <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm text-gray-400" htmlFor="animal-tag">
                Tag ID *
              </label>
              <input
                id="animal-tag"
                type="text"
                value={form.tag_id}
                onChange={(e) => setForm((prev) => ({ ...prev, tag_id: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="animal-rfid">
                Animal RFID
              </label>
              <input
                id="animal-rfid"
                type="text"
                value={form.rfid}
                onChange={(e) => setForm((prev) => ({ ...prev, rfid: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="RFID value"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="animal-breed">
                Breed
              </label>
              <input
                id="animal-breed"
                type="text"
                value={form.breed}
                onChange={(e) => setForm((prev) => ({ ...prev, breed: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="animal-sex">
                Sex
              </label>
              <input
                id="animal-sex"
                type="text"
                value={form.sex}
                onChange={(e) => setForm((prev) => ({ ...prev, sex: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="animal-born">
                Birth date
              </label>
              <input
                id="animal-born"
                type="date"
                value={form.born_date}
                onChange={(e) => setForm((prev) => ({ ...prev, born_date: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="animal-farm">
                Farm
              </label>
              <select
                id="animal-farm"
                value={preferredFarmId}
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
            <div>
              <label className="text-sm text-gray-400" htmlFor="animal-cattle">
                Cattle
              </label>
              <select
                id="animal-cattle"
                value={form.cattle_id}
                onChange={(e) => setForm((prev) => ({ ...prev, cattle_id: e.target.value }))}
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Unassigned</option>
                {cattle.map((herd) => (
                  <option key={herd.id} value={herd.id}>
                    {herd.name}
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
                  }}
                  className="mr-3 rounded-md border border-gray-600 px-6 py-2 text-sm text-gray-300 hover:bg-gray-800"
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                disabled={saving || !form.tag_id.trim()}
                className="rounded-md bg-blue-600 px-6 py-2 text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? "Saving..." : editingId ? "Update animal" : "Save animal"}
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="card">
        <div className="flex items-center justify-between pb-4">
          <h2 className="text-xl font-semibold text-white">Animal list</h2>
          <span className="text-sm text-gray-400">{animals.length} total</span>
        </div>
        {animals.length === 0 ? (
          <p className="py-8 text-center text-gray-500">No animals recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-800 text-sm">
              <thead className="bg-gray-900 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
                <tr>
                  <th className="px-4 py-3">Tag</th>
                  <th className="px-4 py-3">RFID</th>
                  <th className="px-4 py-3">Farm</th>
                  <th className="px-4 py-3">Cattle</th>
                  <th className="px-4 py-3">Breed/Sex</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800 text-gray-200">
                {animals.map((animal) => (
                  <tr key={animal.id}>
                    <td className="px-4 py-3 font-semibold text-white">{animal.tag_id}</td>
                    <td className="px-4 py-3 text-gray-400">{animal.rfid || "—"}</td>
                    <td className="px-4 py-3 text-gray-300">{animal.farm_name || "Unassigned"}</td>
                    <td className="px-4 py-3 text-gray-300">{animal.cattle_name || "Unassigned"}</td>
                    <td className="px-4 py-3 text-gray-400">
                      {(animal.breed || "—")}/{animal.sex || "?"}
                    </td>
                    <td className="px-4 py-3 text-right space-x-3">
                      <button
                        type="button"
                        className="text-sm text-blue-400 hover:underline"
                        onClick={() => {
                          setEditingId(animal.id);
                          setForm({
                            tag_id: animal.tag_id,
                            rfid: animal.rfid || "",
                            breed: animal.breed || "",
                            sex: animal.sex || "",
                            born_date: animal.birth_date || "",
                            farm_id: animal.farm_id || "",
                            cattle_id: animal.cattle_id || "",
                          });
                        }}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="text-sm text-red-400 hover:underline"
                        onClick={() => handleDelete(animal.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>

  );
}
