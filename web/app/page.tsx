import Link from "next/link";

import { listPublicAnnouncements } from "@/lib/api";

export default async function HomePage() {
  let announcements: Awaited<ReturnType<typeof listPublicAnnouncements>> = [];
  try {
    announcements = await listPublicAnnouncements();
  } catch {
    announcements = [];
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-slate-950 to-black px-6 py-16 text-white">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-10 left-10 h-64 w-64 rounded-full bg-emerald-500 blur-[140px] opacity-20 animate-pulse" />
        <div className="absolute bottom-0 right-10 h-72 w-72 rounded-full bg-sky-500 blur-[160px] opacity-20 animate-pulse" />
      </div>

      <div className="relative mx-auto grid max-w-6xl gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-8">
          <header>
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">
              Precision Beef Insights
            </p>
            <h1 className="mt-3 text-5xl font-black leading-tight tracking-tight">
              AI-powered Ultrasound Grading for Cattle
            </h1>
            <p className="mt-4 text-lg text-slate-200/90">
              Stream captures from the pasture into a unified grading pipeline. Overlay masks, log clarity scores, and share results with your team instantly.
            </p>
          </header>

          <div className="flex flex-wrap gap-4">
            <Link
              href="/login"
              className="group rounded-full bg-emerald-500 px-6 py-3 text-base font-semibold uppercase tracking-wide text-black transition hover:bg-emerald-400"
            >
              Log in
            </Link>
            <Link
              href="/register"
              className="rounded-full border border-emerald-400/60 px-6 py-3 text-base font-semibold uppercase tracking-wide text-white/90 hover:bg-emerald-400/10"
            >
              Request access
            </Link>
            <a
              href="#panels"
              className="rounded-full border border-white/30 px-6 py-3 text-base font-semibold uppercase tracking-wide text-white/90 hover:border-emerald-400"
            >
              Explore panels
            </a>
          </div>

        </section>

        <section>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="text-lg font-semibold" id="announcements">
              {announcements.length === 0 ? "Notes" : "Notes"}
            </h2>
            {announcements.length === 0 ? (
              <p className="mt-4 text-sm text-slate-300">No announcements yet.</p>
            ) : (
              <ul className="mt-4 space-y-4 text-sm text-slate-200">
                {announcements.map((item) => (
                  <li key={item.id} className="rounded-2xl border border-white/10 bg-slate-900/60 p-4">
                    <h3 className="text-base font-semibold text-white">{item.subject}</h3>
                    <div
                      className="prose prose-invert max-w-none text-sm mt-2"
                      dangerouslySetInnerHTML={{ __html: item.content_html }}
                    />
                    <p className="mt-3 text-xs uppercase tracking-wide text-slate-400">
                      {item.author_name ?? "CTI Admin"} • {new Date(item.created_at).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      <section
        id="panels"
        className="relative z-10 mx-auto mt-20 max-w-5xl rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-200 shadow-2xl backdrop-blur"
      >
        <h2 className="text-lg font-semibold text-white">Dashboards at a glance</h2>
        <p className="mt-2 text-slate-300">
          Navigate directly to the workspace you need: Admin orchestration, Technician grading, or Farmer summaries.
        </p>
        <div className="mt-6 flex flex-wrap gap-4">
          <Link className="btn" href="/dashboard/admin">
            Admin panel
          </Link>
          <Link className="btn" href="/dashboard/technician">
            Technician console
          </Link>
          <Link className="btn" href="/dashboard/farmer">
            Farmer view
          </Link>
        </div>
      </section>
    </main>
  );
}
