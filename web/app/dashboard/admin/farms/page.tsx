"use client";

import { useEffect, useState } from "react";
import { listFarms, createFarm, type Farm } from "@/lib/api";

export default function FarmsPage() {
  const [farms, setFarms] = useState<Farm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newFarmName, setNewFarmName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadFarms = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const data = await listFarms(token);
      setFarms(data);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to load farms");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFarms();
  }, []);

  const handleCreateFarm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFarmName.trim()) return;
    
    setCreating(true);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      await createFarm(token, newFarmName);
      setNewFarmName("");
      await loadFarms();
    } catch (e: any) {
      setError(e.message || "Failed to create farm");
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <main className="p-6"><p>Loading farms...</p></main>;

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-bold">Farm Management</h1>
      <p className="mt-2 text-gray-400">
        View and manage farms in the system
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-red-900/20 border border-red-500 p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Create Farm Form */}
      <div className="mt-8 card">
        <h2 className="text-xl font-semibold mb-4">Create New Farm</h2>
        <form onSubmit={handleCreateFarm} className="flex gap-4">
          <input
            type="text"
            placeholder="Farm name"
            value={newFarmName}
            onChange={(e) => setNewFarmName(e.target.value)}
            className="flex-1 rounded-md bg-gray-800 border border-gray-700 px-4 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={creating}
          />
          <button
            type="submit"
            disabled={creating || !newFarmName.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creating ? "Creating..." : "Create Farm"}
          </button>
        </form>
      </div>

      {/* Farms List */}
      <div className="mt-8">
        <h2 className="text-2xl font-semibold mb-4">
          Farms ({farms.length})
        </h2>
        
        {farms.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-gray-400">No farms yet. Create one above to get started.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {farms.map((farm) => (
              <div key={farm.id} className="card">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{farm.name}</h3>
                    <p className="text-sm text-gray-400 mt-1">
                      ID: {farm.id}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Created: {new Date(farm.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button className="px-4 py-2 bg-gray-700 text-white rounded-md hover:bg-gray-600">
                      View
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
