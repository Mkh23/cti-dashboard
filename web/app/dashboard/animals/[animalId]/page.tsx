"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  getAnimal,
  getAnimalScans,
  me,
  type Animal,
  type AnimalScan,
  type Profile,
} from "@/lib/api";

function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export default function AnimalDetailPage() {
  const params = useParams<{ animalId: string }>();
  const animalId = params?.animalId;
  const [animal, setAnimal] = useState<Animal | null>(null);
  const [scans, setScans] = useState<AnimalScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);

  const scansBasePath = useMemo(() => {
    if (!profile) return "/dashboard/admin/scans";
    if (profile.roles.includes("admin")) return "/dashboard/admin/scans";
    if (profile.roles.includes("technician")) return "/dashboard/technician/scans";
    if (profile.roles.includes("farmer")) return "/dashboard/farmer/scans";
    return "/dashboard/admin/scans";
  }, [profile]);

  useEffect(() => {
    const run = async () => {
      if (!animalId) return;
      const token = localStorage.getItem("token");
      if (!token) {
        setError("Not logged in");
        setLoading(false);
        return;
      }
      try {
        const [profileResp, animalResp, scansResp] = await Promise.all([
          me(token),
          getAnimal(token, animalId),
          getAnimalScans(token, animalId),
        ]);
        setProfile(profileResp);
        setAnimal(animalResp);
        setScans(scansResp);
        setError(null);
      } catch (err: any) {
        setError(err?.message || "Failed to load animal");
      } finally {
        setLoading(false);
      }
    };
    void run();
  }, [animalId]);

  if (loading) {
    return (
      <main className="p-6">
        <p>Loading animal...</p>
      </main>
    );
  }

  if (error || !animal) {
    return (
      <main className="p-6 space-y-4">
        {error && (
          <div className="rounded-md border border-red-500 bg-red-900/20 p-4 text-red-200">
            {error}
          </div>
        )}
        <Link href="/dashboard/animals" className="text-sm text-blue-400 hover:underline">
          ← Back to animals
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/dashboard/animals" className="text-sm text-blue-400 hover:underline">
            ← Back to animals
          </Link>
          <h1 className="text-3xl font-bold text-white mt-2">Animal: {animal.tag_id}</h1>
          <p className="text-sm text-gray-400">RFID: {animal.rfid ?? "—"}</p>
        </div>
      </div>

      <section className="card space-y-2 text-sm text-gray-300">
        <h2 className="text-xl font-semibold text-white">Details</h2>
        <dl className="grid gap-3 md:grid-cols-2">
          <div className="flex justify-between gap-4">
            <dt className="text-gray-400">Birth date</dt>
            <dd>{animal.birth_date ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-gray-400">Farm</dt>
            <dd>{animal.farm_name ?? "Unassigned"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-gray-400">Cattle</dt>
            <dd>{animal.cattle_name ?? "Unassigned"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-gray-400">TAG (RFID)</dt>
            <dd>{animal.rfid ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-gray-400">Breed</dt>
            <dd>{animal.breed ?? "—"}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-gray-400">Sex</dt>
            <dd>{animal.sex ?? "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">Related scans</h2>
          <span className="text-sm text-gray-400">{scans.length} total</span>
        </div>
        {scans.length === 0 ? (
          <p className="text-sm text-gray-500">No scans linked to this animal.</p>
        ) : (
          <div className="space-y-6">
            {scans.map((scan) => (
              <div key={scan.id} className="card space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-lg font-semibold text-white">Capture {scan.capture_id}</div>
                    <div className="text-xs text-gray-400">
                      Created: {formatDate(scan.created_at)} • Latest grading:{" "}
                      {scan.latest_model ? `${scan.latest_model}@${scan.latest_version ?? "?"}` : scan.grading ?? "Awaiting grading"}
                    </div>
                  </div>
                  <Link
                    href={`${scansBasePath}/${scan.id}`}
                    className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-500"
                  >
                    View scan
                  </Link>
                </div>
                <div className="grid gap-3 text-sm text-gray-300 sm:grid-cols-2 md:grid-cols-3">
                  <div>Label: {scan.label ?? "—"}</div>
                  <div>IMF: {scan.imf ?? "—"}</div>
                  <div>Backfat: {scan.backfat_thickness ?? "—"}</div>
                  <div>Weight: {scan.animal_weight ?? "—"}</div>
                  <div>Ribeye: {scan.ribeye_area ?? "—"}</div>
                  <div>Confidence: {scan.latest_confidence ?? "—"}</div>
                </div>
                {scan.image_url ? (
                  <div className="relative h-64 w-full overflow-hidden rounded-lg border border-gray-800 bg-black">
                    <Image
                      src={scan.image_url}
                      alt={`Scan ${scan.capture_id}`}
                      fill
                      className="object-contain"
                      unoptimized
                    />
                  </div>
                ) : (
                  <p className="text-xs text-gray-500">No image available.</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
