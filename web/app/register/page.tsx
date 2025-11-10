"use client";

import Link from "next/link";
import { useState } from "react";

import { registerUser } from "@/lib/api";

const ROLE_OPTIONS = [
  { value: "farmer", label: "Farmer" },
  { value: "technician", label: "Technician" },
];

export default function RegisterPage() {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    phone_number: "",
    address: "",
    requested_role: ROLE_OPTIONS[0].value as "farmer" | "technician",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await registerUser(form);
      setSuccess("Request submitted! We'll email you once an admin approves it.");
      setForm({
        full_name: "",
        email: "",
        password: "",
        phone_number: "",
        address: "",
        requested_role: ROLE_OPTIONS[0].value as "farmer" | "technician",
      });
    } catch (err: any) {
      let message = err?.message || "Registration failed";
      try {
        const parsed = JSON.parse(message);
        message = parsed?.detail || message;
      } catch {
        // ignore JSON parse errors
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <div className="card space-y-6">
        <header>
          <p className="text-xs uppercase tracking-[0.4em] text-emerald-300">Request access</p>
          <h1 className="mt-2 text-3xl font-bold">Create an account</h1>
          <p className="mt-2 text-sm text-gray-400">
            Submit your details to request dashboard access. An administrator will review and approve your account.
          </p>
        </header>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm">
              Full name
              <input
                className="input mt-1"
                required
                value={form.full_name}
                onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
              />
            </label>
            <label className="text-sm">
              Email
              <input
                className="input mt-1"
                type="email"
                required
                value={form.email}
                onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              />
            </label>
            <label className="text-sm">
              Password
              <input
                className="input mt-1"
                type="password"
                required
                value={form.password}
                onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              />
            </label>
            <label className="text-sm">
              Phone number
              <input
                className="input mt-1"
                required
                value={form.phone_number}
                onChange={(event) => setForm((prev) => ({ ...prev, phone_number: event.target.value }))}
              />
            </label>
          </div>
          <label className="text-sm block">
            Mailing address
            <textarea
              className="input mt-1 min-h-[90px]"
              required
              value={form.address}
              onChange={(event) => setForm((prev) => ({ ...prev, address: event.target.value }))}
            />
          </label>
          <label className="text-sm block">
            Requested role
            <select
              className="input mt-1"
              value={form.requested_role}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, requested_role: event.target.value as "farmer" | "technician" }))
              }
            >
              {ROLE_OPTIONS.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </label>
          {error && <p className="text-sm text-red-400">{error}</p>}
          {success && <p className="text-sm text-emerald-300">{success}</p>}
          <button type="submit" className="btn w-full" disabled={loading}>
            {loading ? "Submitting…" : "Submit request"}
          </button>
        </form>
        <p className="text-sm text-gray-400">
          Already approved?{" "}
          <Link className="underline" href="/login">
            Go back to login
          </Link>
          .
        </p>
      </div>
    </main>
  );
}
