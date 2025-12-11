"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { me, type Profile } from "@/lib/api";
import { pickRole, roleToPath } from "@/lib/roles";

type NavLink = {
  href: string;
  label: string;
  matchExact?: boolean;
};

export function DashboardNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!token) return;
    me(token)
      .then(setProfile)
      .catch(() => setProfile(null));
  }, []);

  const preferredDashboard = useMemo(() => {
    if (!profile) return "/dashboard";
    const primaryRole = pickRole(profile.roles);
    return roleToPath(primaryRole);
  }, [profile]);

  const roles = profile?.roles ?? [];
  const isAdmin = roles.includes("admin");
  const isTechnician = roles.includes("technician") && !isAdmin;
  const isFarmer = roles.includes("farmer") && !isAdmin && !isTechnician;

  const scansHref = useMemo(() => {
    if (isAdmin) return "/dashboard/admin/scans";
    if (isTechnician) return "/dashboard/technician/scans";
    if (isFarmer) return "/dashboard/farmer/scans";
    return "/dashboard/admin/scans";
  }, [isAdmin, isTechnician, isFarmer]);

  const links: NavLink[] = useMemo(() => {
    const base: NavLink[] = [{ href: "/", label: "Home", matchExact: true }];
    if (isAdmin) {
      return [
        ...base,
        { href: "/dashboard/admin", label: "Admin" },
        { href: "/dashboard/farms", label: "Farms" },
        { href: "/dashboard/groups", label: "Groups" },
        { href: "/dashboard/animals", label: "Animals" },
        { href: scansHref, label: "Scans" },
        { href: "/dashboard/admin/announcements", label: "Admin Notes" },
      ];
    }
    if (isTechnician) {
      return [
        ...base,
        { href: "/dashboard/technician", label: "Technician" },
        { href: "/dashboard/groups", label: "Groups" },
        { href: "/dashboard/animals", label: "Animals" },
        { href: scansHref, label: "Scans" },
      ];
    }
    if (isFarmer) {
      return [
        ...base,
        { href: "/dashboard/farmer", label: "Farmer" },
        { href: "/dashboard/farms", label: "Farms" },
        { href: "/dashboard/groups", label: "Groups" },
        { href: "/dashboard/animals", label: "Animals" },
        { href: scansHref, label: "Scans" },
      ];
    }
    return base;
  }, [isAdmin, isTechnician, isFarmer, scansHref]);

  const handleSignOut = () => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("token");
    document.cookie = "token=; Path=/; Max-Age=0";
    setProfile(null);
    router.replace("/login");
  };

  const handleBrandClick = () => {
    router.push(preferredDashboard);
  };

  return (
    <nav className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-6 py-4 text-sm font-semibold text-slate-200">
        <button
          type="button"
          onClick={handleBrandClick}
          className="text-xs uppercase tracking-[0.4em] text-emerald-300 transition hover:text-emerald-200"
        >
          CTI Dashboard
        </button>
        <div className="flex flex-1 flex-wrap items-center justify-end gap-3">
          {links.map((link) => {
            const active = link.matchExact
              ? pathname === link.href
              : pathname?.startsWith(link.href);
            return (
              <Link
                key={`${link.href}-${link.label}`}
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
          <button
            type="button"
            onClick={handleSignOut}
            className="rounded-full border border-white/20 px-3 py-1.5 text-xs uppercase tracking-wide text-slate-200 transition hover:border-emerald-400 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
}
