"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getGroup, getGroupAnimals, type Animal, type Group } from "@/lib/api";

export default function GroupDetailPage() {
  const params = useParams<{ groupId: string }>();
  const groupId = params?.groupId;
  const [group, setGroup] = useState<Group | null>(null);
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      if (!groupId) return;
      const token = localStorage.getItem("token");
      if (!token) {
        setError("Not logged in");
        setLoading(false);
        return;
      }
      try {
        const [groupResp, animalsResp] = await Promise.all([
          getGroup(token, groupId),
          getGroupAnimals(token, groupId),
        ]);
        setGroup(groupResp);
        setAnimals(animalsResp);
        setError(null);
      } catch (err: any) {
        setError(err?.message || "Failed to load group");
      } finally {
        setLoading(false);
      }
    };
    void run();
  }, [groupId]);

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading group...</p>
      </main>
    );
  }

  if (error || !group) {
    return (
      <main className="p-6 space-y-4">
        {error && (
          <div className="rounded-md border border-red-500 bg-red-900/20 p-4 text-red-200">
            {error}
          </div>
        )}
        <Link href="/dashboard/groups" className="text-sm text-blue-400 hover:underline">
          ← Back to groups
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/dashboard/groups" className="text-sm text-blue-400 hover:underline">
            ← Back to groups
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-white">Group: {group.name}</h1>
          <p className="text-sm text-gray-400">External ID: {group.external_id ?? "—"}</p>
          <p className="text-sm text-gray-400">Farm: {group.farm_name ?? "Unassigned"}</p>
        </div>
      </div>

      <section className="card space-y-3 text-sm text-gray-300">
        <h2 className="text-xl font-semibold text-white">Animals in this group</h2>
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
