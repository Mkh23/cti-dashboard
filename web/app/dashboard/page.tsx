import Link from "next/link";

export default function DashRoot() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <div className="card">
        <h1 className="text-2xl font-bold">Choose a dashboard</h1>
        <div className="mt-4 flex gap-4">
          <Link className="btn" href="/dashboard/admin">Admin</Link>
          <Link className="btn" href="/dashboard/technician">Technician</Link>
          <Link className="btn" href="/dashboard/farmer">Farmer</Link>
        </div>
      </div>
    </main>
  );
}
