// web/app/login/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, me } from "@/lib/api";
import { roleToPath, pickRole } from "@/lib/roles";

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
      const { access_token } = await login(email, password);

      // store token for client-side code + middleware
      localStorage.setItem("token", access_token);
      document.cookie = `token=${access_token}; Path=/; SameSite=Lax`;

      const profile = await me(access_token); // { id, email, roles: string[] }
      const chosen = pickRole(profile.roles);
      const dest = roleToPath(chosen);

      // Prefer replace() so /login isn't kept in history
      router.replace(dest);

      // Hard fallback in case client router stalls
      setTimeout(() => {
        if (window.location.pathname.startsWith("/login")) {
          window.location.assign(dest);
        }
      }, 150);
    } catch (err: any) {
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
          Tip: Register the first user in Swagger at <code>/auth/register</code>{" "}
          to become admin.
        </p>
      </div>
    </main>
  );
}
