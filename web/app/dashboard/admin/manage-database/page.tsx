"use client";

import { useState } from "react";
import { syncScans, type SyncScansMode, type SyncScansResult } from "@/lib/api";

const ACTIONS: { mode: SyncScansMode; title: string; description: string }[] = [
  {
    mode: "add_only",
    title: "AWS Sync Scans (Add Only)",
    description:
      "Scan the configured S3 bucket and ingest any capture folders that are missing in Postgres. Existing scans stay untouched.",
  },
  {
    mode: "add_remove",
    title: "AWS Sync Scans (Add + Remove)",
    description:
      "Mirror Postgres with the bucket: add missing scans and remove database scans whose capture folders are no longer available in S3.",
  },
];

export default function ManageDatabasePage() {
  const [loading, setLoading] = useState<SyncScansMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<SyncScansResult | null>(null);

  async function triggerSync(mode: SyncScansMode) {
    const token = localStorage.getItem("token");
    if (!token) {
      setError("You must be logged in.");
      return;
    }

    try {
      setLoading(mode);
      setError(null);
      const result = await syncScans(token, mode);
      setSummary(result);
    } catch (err: any) {
      setError(err?.message || "Failed to execute sync");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Manage Database</h1>
        <p className="mt-2 text-gray-400">
          Run administrative sync jobs against the AWS bucket using the exact
          same ingest logic as the webhook. Use the destructive option with
          care.
        </p>
      </div>

      {error && (
        <div className="rounded border border-red-500/50 bg-red-500/10 px-4 py-3 text-red-200">
          {error}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {ACTIONS.map((action) => (
          <div key={action.mode} className="card space-y-3">
            <div>
              <h2 className="text-xl font-semibold">{action.title}</h2>
              <p className="mt-2 text-gray-400">{action.description}</p>
            </div>
            <button
              className="btn"
              onClick={() => triggerSync(action.mode)}
              disabled={loading !== null}
            >
              {loading === action.mode ? "Running..." : "Run"}
            </button>
          </div>
        ))}
      </div>

      {summary && (
        <section className="card">
          <h2 className="text-xl font-semibold">Latest Sync Result</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-400">Bucket</dt>
              <dd className="font-mono">{summary.bucket}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Prefix</dt>
              <dd className="font-mono">{summary.prefix}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Mode</dt>
              <dd className="uppercase">{summary.mode}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Seen Folders</dt>
              <dd>{summary.synced_ingest_keys}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Added</dt>
              <dd className="text-green-300">{summary.added}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Duplicates</dt>
              <dd>{summary.duplicates}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Removed</dt>
              <dd className="text-red-300">{summary.removed}</dd>
            </div>
          </dl>
          {summary.errors.length > 0 && (
            <div className="mt-4 rounded border border-yellow-500/50 bg-yellow-500/5 p-3 text-sm text-yellow-200">
              <p className="font-semibold">Errors</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {summary.errors.map((err, idx) => (
                  <li key={`${err}-${idx}`}>{err}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
