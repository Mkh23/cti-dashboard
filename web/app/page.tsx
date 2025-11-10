import Link from "next/link";

import { listPublicAnnouncements } from "@/lib/api";

const CowLineArt = () => (
  <svg
    viewBox="0 0 600 320"
    xmlns="http://www.w3.org/2000/svg"
    className="cow-outline h-48 w-full"
    fill="none"
  >
    <defs>
      <linearGradient id="cowStroke" x1="0" y1="0" x2="600" y2="0">
        <stop offset="0%" stopColor="#34d399" />
        <stop offset="60%" stopColor="#60a5fa" />
        <stop offset="100%" stopColor="#f472b6" />
      </linearGradient>
    </defs>
    <path
      stroke="url(#cowStroke)"
      strokeWidth={3}
      d="M40 210 C90 160, 150 130, 210 150 C230 155, 240 150, 260 130 C270 120, 300 110, 330 140 C350 160, 360 160, 390 150 C430 140, 460 150, 480 190 C495 220, 510 260, 540 260 C560 260, 560 300, 520 295 C495 292, 480 270, 470 250 C460 230, 440 230, 420 240 C400 250, 360 260, 330 250 C300 240, 260 240, 220 260 C190 275, 160 285, 130 280 C110 276, 120 240, 130 220 C140 200, 130 180, 100 185 C70 190, 50 200, 40 210 Z"
    />
  </svg>
);

const CowScene = () => (
  <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/60 p-6 shadow-2xl backdrop-blur">
    <div className="flex items-center justify-between text-xs uppercase tracking-[0.4em] text-slate-400">
      <span>Contour Trace</span>
      <span>Probe Sweep</span>
    </div>
    <div className="relative mt-6">
      <div className="cow-glow absolute inset-0 rounded-[2.25rem] border border-emerald-400/20" />
      <CowLineArt />
      <div className="pointer-events-none absolute inset-x-10 bottom-2 flex justify-between text-[0.7rem] uppercase tracking-[0.3em] text-slate-400">
        <span>BRISKET</span>
        <span>RIBEYE</span>
      </div>
      <div className="probe-glow absolute left-1/4 top-5 flex h-12 w-12 items-center justify-center rounded-full border border-emerald-300/70 bg-black/60">
        <div className="h-3 w-8 rounded-full bg-emerald-300/70" />
      </div>
      <div className="pointer-events-none absolute left-1/4 top-5 h-1 w-40 origin-left bg-gradient-to-r from-emerald-300/70 to-transparent blur-[2px]" />
    </div>
    <div className="mt-6 grid gap-4 text-sm text-slate-200 md:grid-cols-2">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
        <p className="text-xs uppercase tracking-[0.3em] text-emerald-300">Glowing trace</p>
        <p className="mt-1 text-lg font-semibold text-white">Real-time cow silhouette rendered from the latest scan.</p>
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
        <p className="text-xs uppercase tracking-[0.3em] text-sky-300">Probe sweep</p>
        <p className="mt-1 text-lg font-semibold text-white">Animated transducer arc shows exactly where data is collected.</p>
      </div>
    </div>
  </div>
);

export default async function HomePage() {
  let announcements: Awaited<ReturnType<typeof listPublicAnnouncements>> = [];
  try {
    announcements = await listPublicAnnouncements();
  } catch (error) {
    announcements = [];
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-slate-950 to-black px-6 py-16 text-white">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-10 left-10 h-64 w-64 rounded-full bg-emerald-500 blur-[140px] opacity-20 animate-pulse" />
        <div className="absolute bottom-0 right-10 h-72 w-72 rounded-full bg-sky-500 blur-[160px] opacity-20 animate-pulse" />
      </div>

      <div className="relative mx-auto flex max-w-6xl flex-col gap-12 lg:flex-row">
        <section className="flex-1 space-y-8">
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

          <ul className="grid gap-4 text-sm text-slate-300 sm:grid-cols-2">
            <li className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
              <p className="text-xs uppercase tracking-wide text-emerald-300">Capture → Cloud</p>
              <p className="mt-1 text-base text-white">Raspberry Pi uploads sealed with HMAC headers &amp; schema validation.</p>
            </li>
            <li className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
              <p className="text-xs uppercase tracking-wide text-sky-300">Mask overlay</p>
              <p className="mt-1 text-base text-white">Toggle ultrasound masks in-line with clarity + usability annotations.</p>
            </li>
            <li className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
              <p className="text-xs uppercase tracking-wide text-amber-300">Farm-aware</p>
              <p className="mt-1 text-base text-white">PostGIS geofences auto-assign scans to herds, cattle, and animals.</p>
            </li>
            <li className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
              <p className="text-xs uppercase tracking-wide text-rose-300">Collaborative</p>
              <p className="mt-1 text-base text-white">Admins publish notices that surface directly on this page.</p>
            </li>
          </ul>
        </section>

        <section className="flex-1 space-y-6">
          <CowScene />
          <div className="rounded-3xl border border-white/10 bg-slate-950/60 p-6 shadow-2xl backdrop-blur">
            <div className="flex items-center justify-between text-xs uppercase tracking-[0.4em] text-slate-400">
              <span>Ultrasound Live</span>
              <span>CTI-EDGE</span>
            </div>
            <div className="relative mt-4 rounded-2xl border border-white/10 bg-black/70 p-4">
              <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_20%_20%,rgba(16,185,129,0.25),transparent_45%),radial-gradient(circle_at_80%_30%,rgba(59,130,246,0.2),transparent_50%)]" />
              <div className="relative flex flex-col gap-3 text-xs text-slate-300">
                <p className="text-base font-semibold text-white">Ribeye overlay</p>
                <div className="grid grid-cols-2 gap-3 text-[0.85rem]">
                  <div>
                    <p className="text-slate-400">IMF</p>
                    <p className="text-2xl font-semibold text-emerald-300">9.2%</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Ribeye area</p>
                    <p className="text-2xl font-semibold text-sky-300">78.4 cm²</p>
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-[0.85rem]">
                  <p className="uppercase tracking-[0.2em] text-emerald-300">Clarity</p>
                  <p className="text-lg font-bold text-white">Good</p>
                  <p className="text-slate-400">Mask overlay ready • Technician can flip to grading in one click.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
            <h2 className="text-lg font-semibold" id="announcements">
              Field notes from admins
            </h2>
            {announcements.length === 0 ? (
              <p className="mt-4 text-sm text-slate-300">
                No announcements yet. Admins can publish guidance directly from the dashboard.
              </p>
            ) : (
              <ul className="mt-4 space-y-4 text-sm text-slate-200">
                {announcements.map((item) => (
                  <li key={item.id} className="rounded-2xl border border-white/10 bg-slate-900/60 p-4">
                    <div
                      className="prose prose-invert max-w-none text-sm"
                      dangerouslySetInnerHTML={{ __html: item.content_html }}
                    />
                    <p className="mt-3 text-xs uppercase tracking-wide text-slate-400">
                      {item.author_name ?? "CTI Admin"} •
                      {" "}
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      <section id="panels" className="relative z-10 mx-auto mt-20 max-w-5xl rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-200 shadow-2xl backdrop-blur">
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
