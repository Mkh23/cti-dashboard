// web/app/dashboard/admin/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { me, type Profile } from "@/lib/api";
import { pickRole, roleToPath } from "@/lib/roles";

export default function AdminDash() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) throw new Error("Not logged in");
        const u = await me(token);

        // Redirect non-admins to their own dashboard with role priority
        if (!u.roles?.includes("admin")) {
          const chosen = pickRole(u.roles);
          router.replace(roleToPath(chosen));
          return;
        }
        setProfile(u);
      } catch (e: any) {
        setError(e.message || "Auth error");
      }
    })();
  }, [router]);

  if (error) return <main className="p-6"><p className="text-red-500">{error}</p></main>;
  if (!profile) return <main className="p-6"><p>Loading...</p></main>;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold">Welcome, {profile.full_name || profile.email}</h1>
          <p className="mt-2 text-gray-500">
            Your roles: <b>{profile.roles.join(", ")}</b>
          </p>
        </div>
        <a 
          href="/dashboard/admin/profile" 
          className="btn"
        >
          Manage Profile
        </a>
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="card">
          <h2 className="text-xl font-semibold">Getting Started</h2>
          <ul className="mt-3 space-y-2 text-gray-300">
            <li>• This is the <b>admin</b> dashboard placeholder.</li>
            <li>• We'll add shared & role-specific panels next.</li>
          </ul>
        </div>
        <div className="card">
          <h2 className="text-xl font-semibold">Admin Tools</h2>
          <ul className="mt-3 space-y-2 text-gray-300">
            <li>
              • <a className="underline" href="/dashboard/admin/scans">
                  Scan Oversight →
                </a>
            </li>
            <li>
              • <a className="underline" href="/dashboard/admin/users">
                  Manage Users & Roles →
                </a>
            </li>
            <li>
              • <a className="underline" href="/dashboard/farms">
                  Manage Farms →
                </a>
            </li>
            <li>
              • <a className="underline" href="/dashboard/admin/devices">
                  Device Registry →
                </a>
            </li>
            <li>
              • <a className="underline" href="/dashboard/admin/profile">
                  Profile Settings →
                </a>
            </li>
          </ul>
        </div>
      </div>
    </main>
  );
}
