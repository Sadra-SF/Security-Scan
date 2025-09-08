import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { useAuthStore, clearAuth } from '@state/auth';

export default function AppLayout() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-60 lg:w-64 border-r bg-white hidden md:block">
        <div className="p-4">
          <h1 className="font-bold text-lg">Security Scanner</h1>
        </div>
        <nav className="px-2 py-2 space-y-1">
          <Link className="block px-3 py-3 rounded-lg hover:bg-gray-100 transition-colors font-medium" to="/dashboard">
            📊 Dashboard
          </Link>
          <Link className="block px-3 py-3 rounded-lg hover:bg-gray-100 transition-colors font-medium" to="/targets">
            🎯 Targets
          </Link>
          <Link className="block px-3 py-3 rounded-lg hover:bg-gray-100 transition-colors font-medium" to="/findings">
            🔍 Findings
          </Link>
          <Link className="block px-3 py-3 rounded-lg hover:bg-gray-100 transition-colors font-medium" to="/scans/new">
            ⚡ New Scan
          </Link>
          <Link className="block px-3 py-3 rounded-lg hover:bg-gray-100 transition-colors font-medium" to="/reports">
            📋 Reports
          </Link>
          <Link className="block px-3 py-3 rounded-lg hover:bg-gray-100 transition-colors font-medium" to="/settings/integrations">
            ⚙️ Settings
          </Link>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 border-b flex items-center justify-between px-4 lg:px-6 bg-white">
          <div className="md:hidden">
            <h1 className="font-bold text-lg">Security Scanner</h1>
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <span className="text-sm text-gray-600 hidden sm:block">
              Welcome, {user?.username ?? 'User'}
            </span>
            <button
              type="button"
              className="text-sm px-3 py-2 rounded-lg border hover:bg-gray-50 transition-colors"
              onClick={() => clearAuth()}
            >
              Logout
            </button>
          </div>
        </header>

        {/* Page Content */}
        <section className="flex-1 p-4 lg:p-6 overflow-auto">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </section>
      </main>
    </div>
  );
}