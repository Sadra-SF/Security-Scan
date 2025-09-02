import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useScans } from '@api/hooks/resources';

export default function ScansList() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const { data, isLoading, isError } = useScans({
    page_size: 20,
    search: search || undefined,
    status: statusFilter || undefined
  });

  if (isLoading) return <div>Loading scans…</div>;
  if (isError) return <div className="text-red-600">Failed to load scans</div>;

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Scans</h1>
        <Link
          to="/scans/new"
          className="px-3 py-1 rounded border bg-blue-600 text-white hover:bg-blue-700"
        >
          New Scan
        </Link>
      </header>

      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search scans..."
          className="border rounded px-3 py-2 flex-1"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="border rounded px-3 py-2"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <table className="w-full text-sm border">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left p-2 border-b">ID</th>
            <th className="text-left p-2 border-b">Target</th>
            <th className="text-left p-2 border-b">Status</th>
            <th className="text-left p-2 border-b">Created</th>
            <th className="text-left p-2 border-b">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.results?.map((scan) => (
            <tr key={scan.id} className="border-b">
              <td className="p-2">{scan.id}</td>
              <td className="p-2">{scan.target}</td>
              <td className="p-2">
                <span className={`px-2 py-1 rounded text-xs ${
                  scan.status === 'completed' ? 'bg-green-100 text-green-800' :
                  scan.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  scan.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {scan.status}
                </span>
              </td>
              <td className="p-2">{scan.created_at ? new Date(scan.created_at).toLocaleDateString() : '-'}</td>
              <td className="p-2">
                <Link className="text-blue-600 hover:underline" to={`/scans/${scan.id}`}>
                  View Details
                </Link>
              </td>
            </tr>
          )) ?? null}
        </tbody>
      </table>
    </div>
  );
}