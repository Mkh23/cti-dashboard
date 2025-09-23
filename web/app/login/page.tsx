"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, me } from "@/lib/api";
import { roleToPath } from "@/lib/roles";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("StrongPass!123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      console.log("[login] submitting");
      const { access_token } = await login(email, password);
      console.log("[login] token received", access_token?.slice(0, 10) + "…");
      localStorage.setItem("token", access_token);

      const profile = await me(access_token);
      const dest = roleToPath(profile.role);
      console.log("[login] redirecting to", dest);

      // Prefer replace to avoid keeping /login in history
      router.replace(dest);

      // Hard fallback in case client router doesn't navigate
      setTimeout(() => {
        if (window.location.pathname.startsWith("/login")) {
          console.warn("[login] router stalled; forcing hard navigation to", dest);
          window.location.assign(dest);
        }
      }, 150);
      return;
    } catch (err: any) {
      console.error("[login] error", err);
      let msg = err?.message || "Login failed";
      try {
        const parsed = JSON.parse(msg);
        msg = parsed?.detail || msg;
      } catch {}
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <div className="card">
        <h1 className="text-2xl font-bold">Login</h1>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="block text-sm mb-1">Email</label>
            <input
              className="input"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button className="btn w-full" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="mt-4 text-sm text-gray-400">
          Tip: Register the first user in Swagger at <code>/auth/register</code> to become admin.
        </p>
      </div>
    </main>
  );
}
