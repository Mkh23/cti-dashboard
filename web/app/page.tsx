import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-16">
      <div className="grid gap-8 lg:grid-cols-2 items-center">
        <section>
          <h1 className="text-5xl font-extrabold tracking-tight leading-tight">
            AI‑enabled Ultrasound Grading for Cattle
          </h1>
          <p className="mt-6 text-lg text-gray-300">
            From barn to cloud: Raspberry Pi → AWS S3 → Secure Server.
            Visualize scans, manage farms & devices, and deliver beef quality grades.
          </p>
          <div className="mt-8 flex gap-4">
            <Link href="/login" className="btn">Log in</Link>
            <a href="https://localhost:8000/docs" className="btn">API Docs</a>
          </div>
          <ul className="mt-8 space-y-2 text-gray-400">
            <li>• Role‑aware dashboards: <b>Admin</b>, <b>Technician</b>, <b>Farmer</b></li>
            <li>• PostGIS geofences for farms & parcels</li>
            <li>• Secure JWT authentication</li>
          </ul>
        </section>
        <section className="card">
          <h2 className="text-2xl font-semibold">Data Path</h2>
          <ol className="mt-4 space-y-2">
            <li>1) Pi captures US image + metadata</li>
            <li>2) Upload to AWS S3 (Lambda optional)</li>
            <li>3) Server ingests event → DB</li>
            <li>4) Dashboard visualizes & grades</li>
          </ol>
        </section>
      </div>
    </main>
  );
}
