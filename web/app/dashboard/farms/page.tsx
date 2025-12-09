"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  listFarms,
  createFarm,
  me,
  type Farm,
  type Profile,
} from "@/lib/api";

const MANAGEABLE_ROLES = new Set(["admin", "technician", "farmer"]);

export default function FarmManagerPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newFarmName, setNewFarmName] = useState("");

  const canManage = profile?.roles?.some((role) => MANAGEABLE_ROLES.has(role)) ?? false;

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");

      const [profileData, farmsData] = await Promise.all([
        me(token),
        listFarms(token),
      ]);
      setProfile(profileData);
      setFarms(farmsData);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Failed to load farms");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCreateFarm = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newFarmName.trim()) return;

    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      await createFarm(token, { name: newFarmName.trim() });
      setNewFarmName("");
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to create farm");
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading farms...</p>
      </main>
    );
  }

  if (error && !profile) {
    return (
      <main className="p-6">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Farms</h1>
        <p className="mt-2 text-gray-400">
          Manage farms you own. Admins can see every farm in the platform.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-500 bg-red-900/20 p-4">
          <p className="text-red-300">{error}</p>
        </div>
      )}

      {canManage && (
        <div className="card">
          <h2 className="text-xl font-semibold">Create a farm</h2>
          <p className="mt-1 text-sm text-gray-400">
            New farms are automatically associated with your account.
          </p>
          <form onSubmit={handleCreateFarm} className="mt-4 flex flex-col gap-3 md:flex-row">
            <input
              type="text"
              placeholder="Farm name"
              value={newFarmName}
              onChange={(event) => setNewFarmName(event.target.value)}
              className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={creating}
            />
            <button
              type="submit"
              disabled={creating || !newFarmName.trim()}
              className="rounded-md bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {creating ? "Creating..." : "Create"}
            </button>
          </form>
        </div>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold">Farm list</h2>
          {profile && (
            <span className="text-sm text-gray-400">
              Showing {farms.length} farm{farms.length === 1 ? "" : "s"}
            </span>
          )}
        </div>

        {farms.length === 0 ? (
          <div className="card py-12 text-center text-gray-400">
            {canManage ? "No farms yet. Create one above to get started." : "No farms available."}
          </div>
        ) : (
          <div className="space-y-4">
            {farms.map((farm) => {
              const ownerNames = farm.owners.map((owner) => owner.full_name || owner.email);
              return (
                <div key={farm.id} className="card">
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h3 className="text-lg font-semibold">{farm.name}</h3>
                      <p className="mt-1 text-sm text-gray-400">
                        Owners: {ownerNames.length ? ownerNames.join(", ") : "Unassigned"}
                      </p>
                      <p className="mt-1 text-xs text-gray-500">
                        Created {new Date(farm.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Link
                        href={`/dashboard/cattle?farm_id=${farm.id}`}
                        className="rounded-md border border-gray-700 px-4 py-2 text-white hover:bg-gray-700"
                      >
                        Cattles list
                      </Link>
                      <Link
                        href={`/dashboard/farms/${farm.id}`}
                        className="rounded-md bg-gray-700 px-4 py-2 text-white hover:bg-gray-600"
                      >
                        View / Edit
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
