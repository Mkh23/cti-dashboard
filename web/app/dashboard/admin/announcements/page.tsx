"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createAnnouncement,
  listAdminAnnouncements,
  me,
  updateAnnouncement,
  type Announcement,
} from "@/lib/api";

const TOOLBAR_ACTIONS = [
  { label: "Bold", command: "bold" },
  { label: "Italic", command: "italic" },
  { label: "Underline", command: "underline" },
];

export default function AdminAnnouncementsPage() {
  const router = useRouter();
  const editorRef = useRef<HTMLDivElement>(null);
  const subjectInputRef = useRef<HTMLInputElement>(null);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fields, setFields] = useState({
    subject: "",
    show_on_home: true,
    pinned: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          router.push("/login");
          return;
        }
        const profile = await me(token);
        if (!profile.roles.includes("admin")) {
          router.replace("/dashboard");
          return;
        }
        const data = await listAdminAnnouncements(token);
        setAnnouncements(data);
        setError(null);
      } catch (err: any) {
        setError(err?.message || "Failed to load announcements");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const exec = (command: string) => {
    if (typeof document !== "undefined") {
      document.execCommand(command);
      editorRef.current?.focus();
    }
  };

  const resetForm = () => {
    setSelectedId(null);
    setFields({ subject: "", show_on_home: true, pinned: false });
    if (editorRef.current) editorRef.current.innerHTML = "";
    subjectInputRef.current?.focus();
  };

  const populateForm = (announcement: Announcement) => {
    setSelectedId(announcement.id);
    setFields({
      subject: announcement.subject ?? "",
      show_on_home: announcement.show_on_home ?? false,
      pinned: announcement.pinned ?? false,
    });
    if (editorRef.current) editorRef.current.innerHTML = announcement.content_html;
  };

  const handleSelect = (id: string) => {
    const target = announcements.find((item) => item.id === id);
    if (target) populateForm(target);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const token = localStorage.getItem("token");
    if (!token) {
      setError("Not logged in");
      return;
    }
    const content = editorRef.current?.innerHTML?.trim() || "";
    if (!fields.subject.trim() || !content) {
      setError("Subject and body are required");
      return;
    }
    try {
      setError(null);
      setSuccess(null);
      let saved: Announcement;
      if (selectedId) {
        saved = await updateAnnouncement(token, selectedId, {
          subject: fields.subject,
          content_html: content,
          show_on_home: fields.show_on_home,
          pinned: fields.pinned,
        });
        setAnnouncements((prev) => prev.map((item) => (item.id === selectedId ? saved : item)));
        setSuccess("Announcement updated");
      } else {
        saved = await createAnnouncement(token, {
          subject: fields.subject,
          content_html: content,
          show_on_home: fields.show_on_home,
          pinned: fields.pinned,
        });
        setAnnouncements((prev) => [saved, ...prev]);
        setSuccess("Announcement published");
      }
      populateForm(saved);
    } catch (err: any) {
      setError(err?.message || "Action failed");
    }
  };

  return (
    <main className="grid gap-10 md:grid-cols-[320px_1fr]">
      <section className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Subjects</h2>
          <button
            className="text-xs font-semibold uppercase tracking-wide text-emerald-300"
            onClick={resetForm}
            type="button"
          >
            New note
          </button>
        </div>
        {loading ? (
          <p className="mt-4 text-sm text-slate-400">Loading…</p>
        ) : announcements.length === 0 ? (
          <p className="mt-4 text-sm text-slate-400">No notes published yet.</p>
        ) : (
          <ul className="mt-4 space-y-2 text-sm text-slate-200">
            {announcements.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={`w-full rounded-2xl border border-white/10 px-3 py-2 text-left transition ${
                    selectedId === item.id
                      ? "bg-emerald-500/10 text-white"
                      : "bg-white/5 hover:border-emerald-400"
                  }`}
                  onClick={() => handleSelect(item.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{item.subject ?? "(No subject)"}</span>
                    {item.pinned && <span className="text-xs uppercase tracking-wide text-amber-300">Pinned</span>}
                  </div>
                  <p className="text-xs text-slate-400">
                    {new Date(item.created_at).toLocaleString()} • {item.show_on_home ? "Shown" : "Hidden"}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-4 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
        <header>
          <p className="text-sm uppercase tracking-[0.4em] text-emerald-300">
            {selectedId ? "Edit note" : "Compose note"}
          </p>
          <h1 className="text-3xl font-bold">Admin announcements</h1>
          <p className="text-sm text-slate-300">
            Subjects drive the list on the left; pin important updates to keep them at the top. Untick "Show on landing page" to hide a published note instantly.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            ref={subjectInputRef}
            type="text"
            value={fields.subject}
            onChange={(event) => setFields((prev) => ({ ...prev, subject: event.target.value }))}
            placeholder="Subject (visible to admins)"
            className="w-full rounded-full border border-white/10 bg-black/40 px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
          <div className="flex flex-wrap gap-2">
            {TOOLBAR_ACTIONS.map((action) => (
              <button
                key={action.command}
                type="button"
                onClick={() => exec(action.command)}
                className="rounded-full border border-white/20 px-3 py-1 text-xs uppercase tracking-wide text-white/80 hover:border-emerald-300"
              >
                {action.label}
              </button>
            ))}
          </div>
          <div
            ref={editorRef}
            contentEditable
            className="min-h-[200px] rounded-2xl border border-white/10 bg-black/40 p-4 text-sm text-white focus:outline-none"
            data-placeholder="Write an update for your team..."
          />
          <div className="flex flex-wrap gap-4 text-sm text-slate-200">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-600 bg-gray-900 text-emerald-500 focus:ring-emerald-400"
                checked={fields.show_on_home}
                onChange={(event) => setFields((prev) => ({ ...prev, show_on_home: event.target.checked }))}
              />
              Show on landing page
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-gray-600 bg-gray-900 text-amber-400 focus:ring-amber-300"
                checked={fields.pinned}
                onChange={(event) => setFields((prev) => ({ ...prev, pinned: event.target.checked }))}
              />
              Pin note
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              className="rounded-full bg-emerald-500 px-6 py-2 text-sm font-semibold uppercase tracking-wide text-black hover:bg-emerald-400"
            >
              {selectedId ? "Update note" : "Publish note"}
            </button>
            {selectedId && (
              <button
                type="button"
                className="text-sm font-semibold text-slate-300 underline"
                onClick={resetForm}
              >
                Create new note
              </button>
            )}
            {error && <span className="text-sm text-rose-300">{error}</span>}
            {success && <span className="text-sm text-emerald-300">{success}</span>}
          </div>
        </form>
      </section>
    </main>
  );
}
