import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { useAuthStore, clearAuth } from '@state/auth';

export default function AppLayout() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 border-r bg-white">
        <div className="p-4 font-bold">Security Scanner</div>
        <nav className="px-2 py-2 space-y-1 text-sm">
          <Link className="block px-3 py-2 rounded hover:bg-gray-100" to="/dashboard">Dashboard</Link>
          <Link className="block px-3 py-2 rounded hover:bg-gray-100" to="/targets">Targets</Link>
          <Link className="block px-3 py-2 rounded hover:bg-gray-100" to="/findings">Findings</Link>
          <Link className="block px-3 py-2 rounded hover:bg-gray-100" to="/scans/new">New Scan</Link>
          <Link className="block px-3 py-2 rounded hover:bg-gray-100" to="/reports">Reports</Link>
          <Link className="block px-3 py-2 rounded hover:bg-gray-100" to="/settings/integrations">Settings & Integrations</Link>
        </nav>
      </aside>
      <main className="flex-1 flex flex-col">
        <header className="h-12 border-b flex items-center justify-between px-4 bg-white">
          <div />
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{user?.username ?? 'Anonymous'}</span>
            <button
              type="button"
              className="text-sm px-3 py-1 rounded border hover:bg-gray-50"
              onClick={() => clearAuth()}
            >
              Logout
            </button>
          </div>
        </header>
        <section className="p-4">
          <Outlet />
        </section>
      </main>
    </div>
  );
}