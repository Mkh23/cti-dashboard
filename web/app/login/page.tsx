"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, me } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const { access_token } = await login(email, password);
      localStorage.setItem("token", access_token);
      const profile = await me(access_token);
      const role = profile.roles[0] || "technician";
      router.push(`/dashboard/${role}`);
    } catch (err: any) {
      setError(err.message || "Login failed");
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <div className="card">
        <h1 className="text-2xl font-bold">Login</h1>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="block text-sm mb-1">Email</label>
            <input className="input" placeholder="you@example.com" value={email} onChange={e=>setEmail(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm mb-1">Password</label>
            <input className="input" type="password" value={password} onChange={e=>setPassword(e.target.value)} />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button className="btn w-full" type="submit">Sign in</button>
        </form>
        <p className="mt-4 text-sm text-gray-400">Tip: Register the first user in Swagger at <code>/auth/register</code> to become admin.</p>
      </div>
    </main>
  );
}
