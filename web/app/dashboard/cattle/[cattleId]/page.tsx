"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getCattle, getCattleAnimals, type Animal, type Cattle } from "@/lib/api";

export default function CattleDetailPage() {
  const params = useParams<{ cattleId: string }>();
  const cattleId = params?.cattleId;
  const [cattle, setCattle] = useState<Cattle | null>(null);
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      if (!cattleId) return;
      const token = localStorage.getItem("token");
      if (!token) {
        setError("Not logged in");
        setLoading(false);
        return;
      }
      try {
        const [cattleResp, animalsResp] = await Promise.all([
          getCattle(token, cattleId),
          getCattleAnimals(token, cattleId),
        ]);
        setCattle(cattleResp);
        setAnimals(animalsResp);
        setError(null);
      } catch (err: any) {
        setError(err?.message || "Failed to load cattle");
      } finally {
        setLoading(false);
      }
    };
    void run();
  }, [cattleId]);

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading cattle...</p>
      </main>
    );
  }

  if (error || !cattle) {
    return (
      <main className="p-6 space-y-4">
        {error && (
          <div className="rounded-md border border-red-500 bg-red-900/20 p-4 text-red-200">
            {error}
          </div>
        )}
        <Link href="/dashboard/cattle" className="text-sm text-blue-400 hover:underline">
          ← Back to cattle
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/dashboard/cattle" className="text-sm text-blue-400 hover:underline">
            ← Back to cattle
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-white">Cattle: {cattle.name}</h1>
          <p className="text-sm text-gray-400">External ID: {cattle.external_id ?? "—"}</p>
          <p className="text-sm text-gray-400">Farm: {cattle.farm_name ?? "Unassigned"}</p>
        </div>
      </div>

      <section className="card space-y-3 text-sm text-gray-300">
        <h2 className="text-xl font-semibold text-white">Animals in this cattle</h2>
        {animals.length === 0 ? (
          <p className="text-gray-500">No animals assigned.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-800 text-sm">
              <thead className="bg-gray-900 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
                <tr>
                  <th className="px-4 py-3">Tag</th>
                  <th className="px-4 py-3">RFID</th>
                  <th className="px-4 py-3">Farm</th>
                  <th className="px-4 py-3">Breed/Sex</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800 text-gray-200">
                {animals.map((animal) => (
                  <tr key={animal.id}>
                    <td className="px-4 py-3 font-semibold text-white">
                      <Link href={`/dashboard/animals/${animal.id}`} className="hover:text-emerald-300">
                        {animal.tag_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-400">{animal.rfid || "—"}</td>
                    <td className="px-4 py-3 text-gray-300">{animal.farm_name || "Unassigned"}</td>
                    <td className="px-4 py-3 text-gray-400">
                      {(animal.breed || "—")}/{animal.sex || "?"}
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(animal.created_at).toLocaleString()}
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
