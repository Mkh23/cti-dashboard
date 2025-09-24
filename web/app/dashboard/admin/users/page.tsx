"use client";

import { useEffect, useState } from "react";

type UserRow = { id: number; email: string; roles: string[] };
const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function AdminUsersPage() {
  const [data, setData] = useState<UserRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<number | null>(null);
  const roles = ["admin", "technician", "farmer"];

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { setError("Not logged in"); return; }
    fetch(`${API}/admin/users`, { headers: { Authorization: `Bearer ${token}` }})
      .then(r => r.ok ? r.json() : Promise.reject(new Error("Failed to load")))
      .then(setData)
      .catch(e => setError(e.message));
  }, []);

  async function toggleRole(u: UserRow, role: string) {
    const token = localStorage.getItem("token");
    if (!token) { setError("Not logged in"); return; }
    const nextRoles = u.roles.includes(role)
      ? u.roles.filter(r => r !== role)
      : [...u.roles, role];
    try {
      setSaving(u.id);
      const res = await fetch(`${API}/admin/users/${u.id}/roles`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ roles: nextRoles })
      });
      if (!res.ok) throw new Error("Save failed");
      const updated = await res.json();
      setData(prev => prev.map(x => x.id === u.id ? updated : x));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(null);
    }
  }

  if (error) return <main className="p-6"><p className="text-red-400">{error}</p></main>;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-3xl font-bold">Users & Roles</h1>
      <p className="mt-2 text-gray-400">Add/remove roles per user.</p>

      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Roles</th>
            </tr>
          </thead>
          <tbody>
            {data.map(u => (
              <tr key={u.id} className="border-t border-white/10">
                <td className="px-3 py-2">{u.id}</td>
                <td className="px-3 py-2">{u.email}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-2">
                    {roles.map(r => {
                      const active = u.roles.includes(r);
                      return (
                        <button
                          key={r}
                          className={`btn ${active ? "bg-white/20" : ""}`}
                          onClick={() => toggleRole(u, r)}
                          disabled={saving === u.id}
                          title={active ? "Click to remove role" : "Click to add role"}
                        >
                          {r}
                        </button>
                      );
                    })}
                  </div>
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td className="px-3 py-6 text-gray-400" colSpan={3}>No users yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
