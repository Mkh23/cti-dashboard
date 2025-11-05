"use client";
import { useEffect, useState } from "react";
import { me } from "@/lib/api";

export default function FarmerDash() {
  const [profile, setProfile] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { setError("Not logged in"); return; }
    me(token).then(setProfile).catch(err => setError(err.message || "Auth error"));
  }, []);

  if (error) return <main className="p-6"><p className="text-red-400">{error}</p></main>;
  if (!profile) return <main className="p-6"><p>Loading...</p></main>;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-bold">Welcome, {profile.full_name || profile.email}</h1>
          <p className="mt-2 text-gray-400">Your roles: {profile.roles.join(", ")}</p>
        </div>
        <a 
          href="/dashboard/farmer/profile" 
          className="btn"
        >
          Manage Profile
        </a>
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="card">
          <h2 className="text-xl font-semibold">Getting Started</h2>
          <ul className="mt-3 space-y-2 text-gray-300">
            <li>• This is the <b>farmer</b> dashboard placeholder.</li>
            <li>• We'll add shared & role-specific panels next.</li>
          </ul>
        </div>
        <div className="card">
          <h2 className="text-xl font-semibold">Quick Links</h2>
          <ul className="mt-3 space-y-2 text-gray-300">
            <li>• Connect to PostGIS entities (farms/devices/scans)</li>
            <li>• Wire S3 object listings & previews</li>
            <li>
              • <a className="underline" href="/dashboard/farmer/profile">
                  Profile Settings →
                </a>
            </li>
          </ul>
        </div>
      </div>
    </main>
  );
}
