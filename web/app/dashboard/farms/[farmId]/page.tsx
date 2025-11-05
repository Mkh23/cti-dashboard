"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { getFarm, updateFarm, type Farm } from "@/lib/api";

export default function FarmDetailPage() {
  const params = useParams<{ farmId: string }>();
  const farmId = params?.farmId;

  const [farm, setFarm] = useState<Farm | null>(null);
  const [nameInput, setNameInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const loadFarm = useCallback(async () => {
    if (!farmId) return;
    setLoading(true);
    setStatus(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const data = await getFarm(token, farmId);
      setFarm(data);
      setNameInput(data.name);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Failed to load farm");
    } finally {
      setLoading(false);
    }
  }, [farmId]);

  useEffect(() => {
    void loadFarm();
  }, [loadFarm]);

  const handleUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!farmId || !farm?.can_edit || !nameInput.trim()) return;

    setSaving(true);
    setStatus(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const updated = await updateFarm(token, farmId, { name: nameInput.trim() });
      setFarm(updated);
      setNameInput(updated.name);
      setError(null);
      setStatus("Farm updated successfully.");
    } catch (err: any) {
      setError(err?.message || "Failed to update farm");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading farm...</p>
      </main>
    );
  }

  if (error && !farm) {
    return (
      <main className="p-6 space-y-4">
        <div className="rounded-md border border-red-500 bg-red-900/20 p-4">
          <p className="text-red-300">{error}</p>
        </div>
        <Link href="/dashboard/farms" className="btn inline-block">
          Back to farms
        </Link>
      </main>
    );
  }

  if (!farm || !farmId) {
    return (
      <main className="p-6">
        <p className="text-gray-400">Farm not found.</p>
      </main>
    );
  }

  const ownerNames = farm.owners.map((owner) => owner.full_name || owner.email);

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      <div>
        <Link href="/dashboard/farms" className="text-sm text-blue-400 hover:underline">
          ← Back to farms
        </Link>
        <h1 className="mt-2 text-3xl font-bold">{farm.name}</h1>
        <p className="mt-1 text-gray-400">Farm ID: {farmId}</p>
        <p className="mt-1 text-sm text-gray-500">
          Created {new Date(farm.created_at).toLocaleString()} • Updated {new Date(farm.updated_at).toLocaleString()}
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-500 bg-red-900/20 p-4">
          <p className="text-red-300">{error}</p>
        </div>
      )}

      {status && (
        <div className="rounded-md border border-emerald-500 bg-emerald-900/20 p-4">
          <p className="text-emerald-200">{status}</p>
        </div>
      )}

      <section className="card space-y-3">
        <h2 className="text-xl font-semibold">Owners</h2>
        <p className="text-sm text-gray-400">
          {ownerNames.length ? ownerNames.join(", ") : "No owners assigned"}
        </p>
      </section>

      <section className="card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Farm details</h2>
          {!farm.can_edit && (
            <span className="text-sm text-gray-400">You do not have permission to edit this farm.</span>
          )}
        </div>

        <form onSubmit={handleUpdate} className="space-y-3">
          <label className="block text-sm font-medium text-gray-300" htmlFor="farm-name">
            Farm name
          </label>
          <input
            id="farm-name"
            type="text"
            value={nameInput}
            onChange={(event) => setNameInput(event.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={!farm.can_edit || saving}
          />
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!farm.can_edit || saving || nameInput.trim().length === 0 || nameInput.trim() === farm.name}
              className="rounded-md bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save changes"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
