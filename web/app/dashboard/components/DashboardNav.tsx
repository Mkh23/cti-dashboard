"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/admin", label: "Admin" },
  { href: "/dashboard/technician", label: "Technician" },
  { href: "/dashboard/farmer", label: "Farmer" },
  { href: "/dashboard/farms", label: "Farms" },
  { href: "/dashboard/animals", label: "Animals" },
  { href: "/dashboard/cattle", label: "Cattle" },
  { href: "/dashboard/admin/announcements", label: "Admin Notes" },
];

export function DashboardNav() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4 text-sm font-semibold text-slate-200">
        <span className="text-xs uppercase tracking-[0.4em] text-emerald-300">
          CTI Dashboard
        </span>
        <div className="flex flex-wrap gap-3">
          {NAV_LINKS.map((link) => {
            const active = pathname?.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-full px-3 py-1.5 transition ${
                  active
                    ? "bg-emerald-500/20 text-white"
                    : "text-slate-300 hover:text-white"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
