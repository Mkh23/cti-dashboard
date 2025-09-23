'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/auth';
import {
  me,
  adminListUsers,
  adminUpdateUserRole,
  type User,
  type Role,
} from '@/lib/api';

const ROLES = ['admin', 'tech', 'farmer'] as const;

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    (async () => {
      try {
        const token = getToken();
        if (!token) {
          router.replace('/login');
          return;
        }
        const u = await me(token);
        if (u.role !== 'admin') {
          router.replace(u.role === 'tech' ? '/dashboard/tech' : '/dashboard/farmer');
          return;
        }
        const data = await adminListUsers(token);
        setUsers(data);
      } catch (e: any) {
        setErr(e.message || 'Failed to load users');
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  async function onChangeRole(id: number, role: Role) {
    const token = getToken();
    if (!token) {
      router.replace('/login');
      return;
    }
    const updated = await adminUpdateUserRole(token, id, role);
    setUsers(prev => prev.map(u => (u.id === id ? updated : u)));
  }

  if (loading) return <div className="p-6">Loading…</div>;
  if (err) return <div className="p-6 text-red-600">{err}</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Users & Roles</h1>
      <div className="overflow-x-auto">
        <table className="min-w-[600px] w-full border">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-2 text-left border">ID</th>
              <th className="p-2 text-left border">Email</th>
              <th className="p-2 text-left border">Role</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-t">
                <td className="p-2 border">{u.id}</td>
                <td className="p-2 border">{u.email}</td>
                <td className="p-2 border">
                  <select
                    className="border rounded p-1"
                    value={u.role}
                    onChange={e => onChangeRole(u.id, e.target.value as Role)}
                  >
                    {ROLES.map(r => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td className="p-3" colSpan={3}>No users yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
