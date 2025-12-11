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
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-br from-slate-900 via-slate-950 to-black text-white">
      {/* Soft background glows */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-16 -left-10 h-64 w-64 rounded-full bg-emerald-500/60 blur-[140px] opacity-25" />
        <div className="absolute bottom-[-4rem] right-0 h-72 w-72 rounded-full bg-sky-500/60 blur-[160px] opacity-25" />
      </div>

      <div className="relative mx-auto max-w-6xl px-6 py-12 space-y-20">
        {/* HERO / TOP SECTION */}
        <section className="pt-4">
          <header className="space-y-5">
            <p className="text-xs uppercase tracking-[0.32em] text-emerald-300">
              Precision Beef Insights
            </p>

            {/* Title full-width */}
            <h1 className="text-4xl font-black leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              AI-powered Ultrasound Group Grading
            </h1>

            {/* Small text under title */}
            <p className="max-w-3xl text-base text-slate-200/90 sm:text-lg">
              Turn ultrasound captures from the chute into consistent, traceable
              grades. Overlay masks, log clarity scores, and share ribeye,
              backfat, and IMF results with your team.
            </p>

            {/* Buttons in one line */}
            <div className="flex flex-wrap gap-4">
              <Link
                href="/login"
                className="rounded-full bg-emerald-500 px-7 py-3 text-sm font-semibold uppercase tracking-wide text-slate-900 shadow-lg transition hover:bg-emerald-400"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-full border border-emerald-400/70 px-7 py-3 text-sm font-semibold uppercase tracking-wide text-emerald-200 hover:bg-emerald-400/10"
              >
                Request access
              </Link>
              <a
                href="#dashboards"
                className="rounded-full border border-white/30 px-7 py-3 text-sm font-semibold uppercase tracking-wide text-white/90 hover:border-emerald-400"
              >
                Explore panels
              </a>
            </div>
          </header>
        </section>

        {/* NOTES / ANNOUNCEMENTS */}
        <section id="notes" className="space-y-4">
          {/* Title + description side by side where room allows */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-baseline sm:justify-between">
            <h2 className="text-lg font-semibold text-white">Notes</h2>
            <p className="text-xs text-slate-400">
              General announcements
            </p>
          </div>

          <div className="w-full rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
            {announcements.length === 0 ? (
              <p className="text-sm text-slate-300">
                No announcements yet. When you go live, admin messages will be
                posted here for everyone on the team.
              </p>
            ) : (
              <ul className="space-y-4 text-sm text-slate-200">
                {announcements.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-2xl border border-white/10 bg-slate-950/70 p-4"
                  >
                    <h3 className="text-base font-semibold text-white">
                      {item.subject}
                    </h3>
                    <div
                      className="prose prose-invert mt-2 max-w-none text-sm"
                      dangerouslySetInnerHTML={{ __html: item.content_html }}
                    />
                    <p className="mt-3 text-xs uppercase tracking-wide text-slate-400">
                      {item.author_name ?? "CTI Admin"} •{" "}
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* PARALLAX BACKGROUND IMAGE 1 – even longer */}
        <section className="relative h-[26rem] md:h-[32rem] overflow-hidden rounded-3xl border border-white/10">
          <div className="absolute inset-0 bg-[url('/devices/image-1.png')] bg-cover bg-center bg-fixed opacity-80" />
          <div className="relative flex h-full items-center bg-gradient-to-r from-slate-950/90 via-slate-950/40 to-slate-900/80 px-6 sm:px-10">
            <div className="max-w-xl space-y-2 text-sm sm:text-base">
              <h2 className="text-lg font-semibold sm:text-xl">
                Built for real barn conditions
              </h2>
              <p className="text-slate-200">
                CTI connects ultrasound devices in the crush directly to a
                grading pipeline in the cloud. Captures are buffered, retried,
                and tagged—so your team can keep scanning, even when the network
                isn’t perfect.
              </p>
            </div>
          </div>
        </section>

        {/* DASHBOARDS / CONTENT SECTION */}
        <section
          id="dashboards"
          className="space-y-6 w-full rounded-3xl border border-white/10 bg-white/5 p-6 text-sm text-slate-200 shadow-2xl backdrop-blur sm:p-8"
        >
          {/* Title + text side by side */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-baseline sm:justify-between">
            <h2 className="text-lg font-semibold text-white sm:text-xl">
              Dashboards at a glance
            </h2>
            <p className="max-w-xl text-slate-300">
              One pipeline, three views. Each role sees what they need—without
              losing the connection back to the original scans.
            </p>
          </div>

          {/* Boxes across page */}
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col justify-between rounded-2xl bg-slate-950/70 p-4">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Admin panel
                </h3>
                <p className="mt-1 text-xs text-slate-300">
                  Configure herds, lots, users, and grading rules. Monitor data
                  quality and system health.
                </p>
              </div>
              <Link className="btn mt-4 w-fit" href="/dashboard/admin">
                Admin panel
              </Link>
            </div>

            <div className="flex flex-col justify-between rounded-2xl bg-slate-950/70 p-4">
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Technician console
                </h3>
                <p className="mt-1 text-xs text-slate-300">
                  See scans arrive in real time, review masks, log clarity
                  scores, and finalize grades before animals leave the chute.
                </p>
              </div>
              <Link className="btn mt-4 w-fit" href="/dashboard/technician">
                Technician console
              </Link>
            </div>

            <div className="flex flex-col justify-between rounded-2xl bg-slate-950/70 p-4">
              <div>
                <h3 className="text-sm font-semibold text-white">Farmer view</h3>
                <p className="mt-1 text-xs text-slate-300">
                  Producers get clear summaries of ribeye, backfat, IMF, and
                  predicted grade at lot or animal level.
                </p>
              </div>
              <Link className="btn mt-4 w-fit" href="/dashboard/farmer">
                Farmer view
              </Link>
            </div>
          </div>
        </section>

        {/* PARALLAX BACKGROUND IMAGE 2 – even longer */}
        <section className="relative h-[26rem] md:h-[32rem] overflow-hidden rounded-3xl border border-white/10">
          <div className="absolute inset-0 bg-[url('/devices/image-2.png')] bg-cover bg-center bg-fixed opacity-80" />
          <div className="relative flex h-full items-center justify-end bg-gradient-to-l from-slate-950/90 via-slate-950/40 to-slate-900/80 px-6 sm:px-10">
            <div className="max-w-xl space-y-2 text-right text-sm sm:text-base">
              <h2 className="text-lg font-semibold sm:text-xl">
                Traceable from frame to final grade
              </h2>
              <p className="text-slate-200">
                Every prediction is stored with its ultrasound frame, mask, and
                technician edits. Export-ready data lets you link grading back
                to genetics, feed, or carcass outcomes.
              </p>
            </div>
          </div>
        </section>

        {/* CONTACT FULL-WIDTH */}
        <section
          id="contact"
          className="w-full rounded-3xl border border-white/10 bg-slate-950/85 p-6 sm:p-8"
        >
          {/* Title + text side by side */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-baseline sm:justify-between">
            <h2 className="text-lg font-semibold text-white sm:text-xl">
              Contact us
            </h2>
            <p className="max-w-xl text-sm text-slate-300">
              Tell us a bit about your herd, feedlot, or program. We’ll reach
              out with next steps and a demo slot.
            </p>
          </div>

          {/* Full-width contact form */}
          <form className="mt-6 space-y-4 text-sm" action="#" method="post">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="name"
                  className="block text-xs font-medium uppercase tracking-wide text-slate-300"
                >
                  Name
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900/80 px-3 py-2 text-sm text-white outline-none ring-emerald-500/40 focus:ring"
                  placeholder="Jane Doe"
                />
              </div>
              <div>
                <label
                  htmlFor="email"
                  className="block text-xs font-medium uppercase tracking-wide text-slate-300"
                >
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900/80 px-3 py-2 text-sm text-white outline-none ring-emerald-500/40 focus:ring"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="role"
                  className="block text-xs font-medium uppercase tracking-wide text-slate-300"
                >
                  Role
                </label>
                <input
                  id="role"
                  name="role"
                  type="text"
                  className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900/80 px-3 py-2 text-sm text-white outline-none ring-emerald-500/40 focus:ring"
                  placeholder="Producer, feedlot, grader, researcher…"
                />
              </div>
              <div>
                <label
                  htmlFor="herd-size"
                  className="block text-xs font-medium uppercase tracking-wide text-slate-300"
                >
                  Herd / lot size (optional)
                </label>
                <input
                  id="herd-size"
                  name="herdSize"
                  type="text"
                  className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900/80 px-3 py-2 text-sm text-white outline-none ring-emerald-500/40 focus:ring"
                  placeholder="e.g., 400 cows, 1,200 head feedlot"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="message"
                className="block text-xs font-medium uppercase tracking-wide text-slate-300"
              >
                Message
              </label>
              <textarea
                id="message"
                name="message"
                rows={4}
                className="mt-1 w-full rounded-lg border border-white/15 bg-slate-900/80 px-3 py-2 text-sm text-white outline-none ring-emerald-500/40 focus:ring"
                placeholder="Share what you’re hoping to do with ultrasound grading."
              />
            </div>

            <button
              type="submit"
              className="mt-2 rounded-full bg-emerald-500 px-7 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-900 shadow-lg hover:bg-emerald-400"
            >
              Send message
            </button>
          </form>

          {/* Stay connected – icon-style links under contact form */}
          <div className="mt-8 flex justify-center gap-6 text-slate-300">
            {/* YouTube */}
            <a
              href="https://www.youtube.com"
              target="_blank"
              rel="noreferrer"
              aria-label="YouTube"
              className="hover:text-emerald-300"
            >
              <svg
                className="h-7 w-7"
                viewBox="0 0 24 24"
                aria-hidden="true"
                fill="currentColor"
              >
                <rect x="2.5" y="6" width="19" height="12" rx="3" ry="3" />
                <polygon points="10,9 16,12 10,15" fill="black" />
              </svg>
            </a>

            {/* Instagram */}
            <a
              href="https://www.instagram.com"
              target="_blank"
              rel="noreferrer"
              aria-label="Instagram"
              className="hover:text-emerald-300"
            >
              <svg
                className="h-7 w-7"
                viewBox="0 0 24 24"
                aria-hidden="true"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
              >
                <rect x="4" y="4" width="16" height="16" rx="4" ry="4" />
                <circle cx="12" cy="12" r="4" />
                <circle cx="17" cy="7" r="1.2" fill="currentColor" />
              </svg>
            </a>

            {/* LinkedIn – classic "in" icon */}
            <a
              href="https://www.linkedin.com"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn"
              className="hover:text-emerald-300"
            >
              <svg
                className="h-7 w-7"
                viewBox="0 0 24 24"
                aria-hidden="true"
                fill="currentColor"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path
                  d="M8 17h2.2v-6.5H8V17zm1.1-7.6c.8 0 1.3-.5 1.3-1.2-.1-.7-.5-1.2-1.3-1.2s-1.3.5-1.3 1.2c0 .7.5 1.2 1.3 1.2z"
                  fill="black"
                />
                <path
                  d="M11.5 10.5H13v.9c.2-.4.8-1.1 1.9-1.1 1.5 0 2.6 1 2.6 3.1V17H15v-3.2c0-.9-.4-1.5-1.2-1.5-.7 0-1.1.5-1.3 1v3.7h-2V10.5z"
                  fill="black"
                />
              </svg>
            </a>

            {/* X / Twitter – simple X mark */}
            <a
              href="https://x.com"
              target="_blank"
              rel="noreferrer"
              aria-label="X (Twitter)"
              className="hover:text-emerald-300"
            >
              <svg
                className="h-7 w-7"
                viewBox="0 0 24 24"
                aria-hidden="true"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <line x1="6" y1="6" x2="18" y2="18" />
                <line x1="18" y1="6" x2="6" y2="18" />
              </svg>
            </a>
          </div>

          {/* FOOTER BAR WITH KEY LINKS */}
          <div className="mt-8 border-t border-white/10 pt-4 text-xs text-slate-500 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <p>
              © {new Date().getFullYear()} CTI – Precision Beef Insights. All
              rights reserved.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/register"
                className="text-xs font-semibold uppercase tracking-wide text-emerald-300 hover:text-emerald-200"
              >
                Request access
              </Link>
              <Link
                href="/login"
                className="text-xs font-semibold uppercase tracking-wide text-slate-200 hover:text-white"
              >
                Log in
              </Link>
              <a
                href="#dashboards"
                className="text-xs font-semibold uppercase tracking-wide text-slate-300 hover:text-white"
              >
                Explore panels
              </a>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
