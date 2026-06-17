"use client";

import { useEffect, useState } from "react";
import { usersService, User } from "@/services/users";

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchUsers() {
      try {
        const response = await usersService.getAll();
        setUsers(response.data);
      } catch (err: any) {
        setError(err.message || "Failed to fetch users");
      } finally {
        setLoading(false);
      }
    }
    fetchUsers();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-zinc-400 text-lg">Loading users…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="bg-red-950/40 border border-red-800/50 rounded-xl p-8 max-w-md text-center">
          <div className="text-red-400 text-5xl mb-4">⚠</div>
          <h2 className="text-xl font-semibold text-red-300 mb-2">
            Connection Error
          </h2>
          <p className="text-zinc-400">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-10 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">
          Database Users
        </h1>
        <p className="text-zinc-400">
          Fetched from PostgreSQL via the Node.js/Express API •{" "}
          <span className="text-orange-400 font-medium">
            {users.length} user{users.length !== 1 ? "s" : ""}
          </span>
        </p>
      </div>

      {/* Table */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl overflow-hidden backdrop-blur-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-zinc-800/50">
                <th className="px-6 py-4 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  ID
                </th>
                <th className="px-6 py-4 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-4 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-4 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-4 text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {users.map((user) => (
                <tr
                  key={user.id}
                  className="hover:bg-zinc-800/30 transition-colors"
                >
                  <td className="px-6 py-4 text-sm text-zinc-500 font-mono">
                    {user.id}
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-white font-medium">{user.name}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-zinc-300">
                    {user.email}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        user.role === "admin"
                          ? "bg-orange-500/20 text-orange-300"
                          : user.role === "analyst"
                          ? "bg-blue-500/20 text-blue-300"
                          : "bg-zinc-700/50 text-zinc-300"
                      }`}
                    >
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-zinc-500">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
