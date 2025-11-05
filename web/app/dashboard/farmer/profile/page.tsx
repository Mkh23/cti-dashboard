"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { me, Profile } from "@/lib/api";
import ProfilePanel from "@/app/components/ProfilePanel";

export default function FarmerProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    me(token)
      .then((data) => {
        // Verify user is farmer
        if (!data.roles.includes("farmer")) {
          router.push("/dashboard");
          return;
        }
        setProfile(data);
      })
      .catch((err) => {
        setError(err.message || "Failed to load profile");
      });
  }, [router]);

  if (error) {
    return (
      <main className="p-6">
        <p className="text-red-400">{error}</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="p-6">
        <p>Loading...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <div className="mb-6">
        <a
          href="/dashboard/farmer"
          className="text-blue-400 hover:text-blue-300 mb-4 inline-block"
        >
          ← Back to Dashboard
        </a>
      </div>
      <ProfilePanel profile={profile} onProfileUpdate={setProfile} />
    </main>
  );
}
