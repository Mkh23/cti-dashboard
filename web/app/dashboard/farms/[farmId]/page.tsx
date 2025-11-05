"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  addFarmMember,
  getFarm,
  me,
  removeFarmMember,
  updateFarm,
  type Farm,
  type FarmMember,
  type Profile,
} from "@/lib/api";

export default function FarmDetailPage() {
  const params = useParams<{ farmId: string }>();
  const farmId = params?.farmId;

  const [profile, setProfile] = useState<Profile | null>(null);
  const [farm, setFarm] = useState<Farm | null>(null);
  const [nameInput, setNameInput] = useState("");
  const [memberInput, setMemberInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [memberActionLoading, setMemberActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [memberStatus, setMemberStatus] = useState<string | null>(null);
  const [memberError, setMemberError] = useState<string | null>(null);

  const loadFarm = useCallback(async () => {
    if (!farmId) return;
    setLoading(true);
    setStatus(null);
    setMemberStatus(null);
    setMemberError(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const [profileData, farmData] = await Promise.all([
        me(token),
        getFarm(token, farmId),
      ]);
      setProfile(profileData);
      setFarm(farmData);
      setNameInput(farmData.name);
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

  const handleAddMember = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!farmId || !farm?.can_edit) return;
    const value = memberInput.trim();
    if (!value) return;

    setMemberActionLoading(true);
    setMemberError(null);
    setMemberStatus(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const usingEmail = value.includes("@");
      const payload = usingEmail
        ? { email: value.toLowerCase() }
        : { user_id: value };
      const updated = await addFarmMember(token, farmId, payload);
      setFarm(updated);
      setMemberInput("");
      const addedMember = updated.members.find((member) => {
        if (usingEmail) {
          return member.email.toLowerCase() === value.toLowerCase();
        }
        return member.user_id === value;
      });
      const displayName =
        addedMember?.full_name || addedMember?.email || "Member";
      setMemberStatus(`Added ${displayName} to the management group.`);
    } catch (err: any) {
      setMemberError(err?.message || "Failed to add member");
    } finally {
      setMemberActionLoading(false);
    }
  };

  const handleRemoveMember = async (member: FarmMember) => {
    if (!farmId || !farm?.can_edit) return;
    setMemberActionLoading(true);
    setMemberError(null);
    setMemberStatus(null);
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Not logged in");
      const updated = await removeFarmMember(token, farmId, member.user_id);
      setFarm(updated);
      const displayName = member.full_name || member.email;
      setMemberStatus(`Removed ${displayName} from the management group.`);
    } catch (err: any) {
      setMemberError(err?.message || "Failed to remove member");
    } finally {
      setMemberActionLoading(false);
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

  const isAdmin = profile?.roles?.includes("admin") ?? false;
  const ownerNames = farm.members
    .filter((member) => member.is_owner)
    .map((member) => member.full_name || member.email);
  const ownerCount = farm.members.filter((member) => member.is_owner).length;

  const canRemoveMember = (member: FarmMember) => {
    if (!farm.can_edit) return false;
    if (isAdmin) {
      if (member.is_owner && ownerCount <= 1) {
        return false;
      }
      return true;
    }
    return !member.is_owner && member.roles.includes("technician");
  };

  const memberPlaceholder = isAdmin
    ? "User email or ID"
    : "Technician email";

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      <div>
        <Link href="/dashboard/farms" className="text-sm text-blue-400 hover:underline">
          ← Back to farms
        </Link>
        <h1 className="mt-2 text-3xl font-bold">{farm.name}</h1>
        <p className="mt-1 text-gray-400">Farm ID: {farmId}</p>
        <p className="mt-1 text-sm text-gray-500">
          Created {new Date(farm.created_at).toLocaleString()} • Updated{" "}
          {new Date(farm.updated_at).toLocaleString()}
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
          <h2 className="text-xl font-semibold">Management group</h2>
          <span className="text-sm text-gray-400">
            Owners and technicians with access to this farm.
          </span>
        </div>

        {memberError && (
          <div className="rounded-md border border-red-500 bg-red-900/20 p-3 text-sm text-red-200">
            {memberError}
          </div>
        )}

        {memberStatus && (
          <div className="rounded-md border border-emerald-500 bg-emerald-900/20 p-3 text-sm text-emerald-200">
            {memberStatus}
          </div>
        )}

        <div className="overflow-hidden rounded-md border border-gray-700">
          <table className="min-w-full divide-y divide-gray-800 text-sm">
            <thead className="bg-gray-900 text-gray-300">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Roles</th>
                <th className="px-4 py-3 text-left font-medium">Access</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 bg-gray-950/40 text-gray-200">
              {farm.members.map((member) => {
                const displayName = member.full_name || member.email;
                const rolesLabel = member.roles.length
                  ? member.roles.join(", ")
                  : "—";
                const accessLabel = member.is_owner ? "Owner" : "Manager";
                const removable = canRemoveMember(member);

                return (
                  <tr key={member.user_id}>
                    <td className="px-4 py-3">
                      <div className="font-medium">{displayName}</div>
                      <div className="text-xs text-gray-400">{member.email}</div>
                    </td>
                    <td className="px-4 py-3">{rolesLabel}</td>
                    <td className="px-4 py-3">{accessLabel}</td>
                    <td className="px-4 py-3 text-right">
                      {removable ? (
                        <button
                          type="button"
                          onClick={() => handleRemoveMember(member)}
                          className="rounded-md border border-red-500 px-3 py-1 text-sm text-red-200 hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                          disabled={memberActionLoading}
                        >
                          {memberActionLoading ? "Working..." : "Remove"}
                        </button>
                      ) : (
                        <span className="text-xs text-gray-500">
                          {member.is_owner ? "Primary owner" : "No permission"}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {farm.can_edit && (
          <form onSubmit={handleAddMember} className="flex flex-col gap-3 md:flex-row md:items-center">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-gray-300" htmlFor="member-input">
                Add to management group
              </label>
              <input
                id="member-input"
                type="text"
                value={memberInput}
                onChange={(event) => setMemberInput(event.target.value)}
                placeholder={memberPlaceholder}
                className="w-full rounded-md border border-gray-700 bg-gray-800 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={memberActionLoading}
              />
              <p className="mt-1 text-xs text-gray-500">
                {isAdmin
                  ? "Admins can add by email or user ID. Farmers can add technicians by email."
                  : "Enter a technician's email address to give them access."}
              </p>
            </div>
            <button
              type="submit"
              disabled={
                memberActionLoading ||
                memberInput.trim().length === 0
              }
              className="rounded-md bg-blue-600 px-5 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {memberActionLoading ? "Working..." : "Add member"}
            </button>
          </form>
        )}
      </section>

      <section className="card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Farm details</h2>
          {!farm.can_edit && (
            <span className="text-sm text-gray-400">
              You do not have permission to edit this farm.
            </span>
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
              disabled={
                !farm.can_edit ||
                saving ||
                nameInput.trim().length === 0 ||
                nameInput.trim() === farm.name
              }
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
