// web/app/dashboard/admin/users/page.tsx
"use client";

import { useEffect, useState } from "react";

import {
  approvePendingUser,
  listAdminUsers,
  listPendingUsers,
  rejectPendingUser,
  type AdminUser,
  type PendingUser,
} from "@/lib/api";

const roles = ["admin", "technician", "farmer"];
const STATUS_CLASSES: Record<string, string> = {
  approved: "bg-emerald-500/20 text-emerald-300",
  pending: "bg-amber-500/20 text-amber-300",
  rejected: "bg-rose-500/20 text-rose-300",
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [pending, setPending] = useState<PendingUser[]>([]);
  const [pendingRoleDrafts, setPendingRoleDrafts] = useState<Record<string, string>>({});
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [showPending, setShowPending] = useState(false);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!stored) {
      setError("Not logged in");
      setLoading(false);
      return;
    }
    setToken(stored);
    (async () => {
      try {
        const [userRows, pendingRows] = await Promise.all([
          listAdminUsers(stored),
          listPendingUsers(stored),
        ]);
        setUsers(userRows);
        setPending(pendingRows);
      } catch (err: any) {
        setError(err?.message || "Failed to load users");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    setPendingRoleDrafts((prev) => {
      const next: Record<string, string> = {};
      for (const p of pending) {
        next[p.id] = prev[p.id] || p.requested_role || "technician";
      }
      return next;
    });
  }, [pending]);

  function formatStatus(status: string) {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  async function toggleRole(user: AdminUser, role: string) {
    if (user.registration_status !== "approved") return;
    const tokenValue = token || localStorage.getItem("token");
    if (!tokenValue) {
      setError("Not logged in");
      return;
    }
    const nextRoles = user.roles.includes(role)
      ? user.roles.filter((r) => r !== role)
      : [...user.roles, role];

    try {
      setSaving(user.id);
      setError(null);
      setMessage(null);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/admin/users/${user.id}/roles`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tokenValue}`,
          },
          body: JSON.stringify({ roles: nextRoles }),
        }
      );
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to update roles");
      }
      const updated = (await res.json()) as AdminUser;
      setUsers((prev) => prev.map((row) => (row.id === user.id ? updated : row)));
      setMessage(`Updated roles for ${user.email}`);
    } catch (err: any) {
      setError(err?.message || "Failed to update roles");
    } finally {
      setSaving(null);
    }
  }

  async function approve(id: string) {
    const tokenValue = token || localStorage.getItem("token");
    if (!tokenValue) {
      setError("Not logged in");
      return;
    }
    const desiredRole = pendingRoleDrafts[id] || "technician";
    try {
      setSaving(id);
      setError(null);
      setMessage(null);
      const approved = await approvePendingUser(tokenValue, id, [desiredRole]);
      setPending((prev) => prev.filter((p) => p.id !== id));
      setUsers((prev) => [...prev, approved]);
      setMessage(`Approved ${approved.email}`);
    } catch (err: any) {
      setError(err?.message || "Failed to approve user");
    } finally {
      setSaving(null);
    }
  }

  async function reject(id: string) {
    const tokenValue = token || localStorage.getItem("token");
    if (!tokenValue) {
      setError("Not logged in");
      return;
    }
    try {
      setSaving(id);
      setError(null);
      setMessage(null);
      await rejectPendingUser(tokenValue, id, "Rejected via dashboard");
      setPending((prev) => prev.filter((p) => p.id !== id));
      setMessage("Request rejected");
    } catch (err: any) {
      setError(err?.message || "Failed to reject user");
    } finally {
      setSaving(null);
    }
  }

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading users…</p>
      </main>
    );
  }

  if (error && !users.length && !pending.length) {
    return (
      <main className="p-6">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Users & Roles</h1>
          <p className="mt-2 text-gray-400">
            Approved users can have roles toggled below. Review new account requests from the pending drawer.
          </p>
        </div>
        <button
          className="btn"
          onClick={() => setShowPending((prev) => !prev)}
        >
          {showPending ? "Hide pending users" : `Review pending users (${pending.length})`}
        </button>
      </div>
      {message && <p className="text-sm text-emerald-300">{message}</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}

      {showPending && (
        <section className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <h2 className="text-xl font-semibold">Pending approvals</h2>
          {pending.length === 0 ? (
            <p className="mt-3 text-sm text-gray-400">No new sign-ups to review.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {pending.map((p) => (
                <li
                  key={p.id}
                  className="rounded-2xl border border-white/10 bg-black/30 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-semibold">{p.full_name || p.email}</p>
                      <p className="text-sm text-gray-400">{p.email}</p>
                      <p className="text-xs text-gray-500">
                        Requested role: {p.requested_role || "technician"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <select
                        className="input text-sm"
                        value={pendingRoleDrafts[p.id] || "technician"}
                        onChange={(event) =>
                          setPendingRoleDrafts((prev) => ({
                            ...prev,
                            [p.id]: event.target.value,
                          }))
                        }
                      >
                        {roles.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                      <button
                        className="btn"
                        disabled={saving === p.id}
                        onClick={() => approve(p.id)}
                      >
                        Approve
                      </button>
                      <button
                        className="btn bg-rose-500/90 hover:bg-rose-500"
                        disabled={saving === p.id}
                        onClick={() => reject(p.id)}
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    Phone: {p.phone_number || "—"} · Address: {p.address || "—"}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div className="overflow-x-auto rounded-2xl border border-white/10">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400">
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Roles</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-t border-white/10">
                <td className="px-4 py-3">
                  <div className="font-semibold">
                    {user.full_name && user.full_name.trim().length > 0 ? user.full_name : "No name set"}
                  </div>
                  <p className="text-xs text-gray-500">
                    Requested: {user.requested_role || "N/A"}
                  </p>
                </td>
                <td className="px-4 py-3">{user.email}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_CLASSES[user.registration_status] || "bg-white/10 text-white"}`}
                  >
                    {formatStatus(user.registration_status)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    {roles.map((role) => {
                      const active = user.roles.includes(role);
                      const disabled = user.registration_status !== "approved" || saving === user.id;
                      return (
                        <button
                          key={role}
                          className={`btn ${active ? "bg-white/20" : ""} ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
                          onClick={() => toggleRole(user, role)}
                          disabled={disabled}
                          title={
                            user.registration_status !== "approved"
                              ? "Pending accounts cannot be edited"
                              : active
                                ? "Remove role"
                                : "Add role"
                          }
                        >
                          {role}
                        </button>
                      );
                    })}
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-gray-400" colSpan={4}>
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
