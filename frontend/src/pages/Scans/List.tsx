import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useScans } from '@api/hooks/resources';

const STATUS_COLORS = {
  completed: '#10B981',
  running: '#3B82F6',
  pending: '#F59E0B',
  failed: '#EF4444'
};

export default function ScansList() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');

  const { data, isLoading, isError } = useScans({
    page: currentPage,
    page_size: pageSize,
    search: search || undefined,
    status: statusFilter || undefined
  });

  if (isLoading) return <div className="flex justify-center py-8"><div className="text-gray-600">Loading scans…</div></div>;
  if (isError) return <div className="text-red-600 text-center py-8">Failed to load scans</div>;

  // Calculate statistics for charts
  const statusCounts = data?.results?.reduce((acc, scan) => {
    acc[scan.status] = (acc[scan.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  const pieData = Object.entries(statusCounts).map(([status, count]) => ({
    name: status.charAt(0).toUpperCase() + status.slice(1),
    value: count,
    color: STATUS_COLORS[status as keyof typeof STATUS_COLORS] || '#6B7280'
  }));

  const handleExport = () => {
    const csvContent = [
      ['ID', 'Target', 'Status', 'Created'].join(','),
      ...(data?.results?.map(scan => [
        scan.id,
        scan.target,
        scan.status,
        scan.created_at || ''
      ].join(',')) || [])
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'scans.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Security Scans</h1>
        <div className="flex gap-3">
          <button
            onClick={handleExport}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Export CSV
          </button>
          <Link
            to="/scans/new"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            New Scan
          </Link>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Total Scans</div>
          <div className="text-2xl font-bold">{data?.count || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Completed</div>
          <div className="text-2xl font-bold text-green-600">{statusCounts.completed || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Running</div>
          <div className="text-2xl font-bold text-blue-600">{statusCounts.running || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Failed</div>
          <div className="text-2xl font-bold text-red-600">{statusCounts.failed || 0}</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border">
          <h3 className="text-lg font-medium mb-4">Scan Status Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white p-6 rounded-lg border">
          <h3 className="text-lg font-medium mb-4">Status Overview</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={pieData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3B82F6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              placeholder="Search scans..."
              className="w-full border rounded px-3 py-2"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              className="w-full border rounded px-3 py-2"
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
            <input
              type="date"
              className="w-full border rounded px-3 py-2"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
            <input
              type="date"
              className="w-full border rounded px-3 py-2"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="view"
                value="table"
                checked={viewMode === 'table'}
                onChange={(e) => setViewMode(e.target.value as 'table')}
                className="mr-2"
              />
              Table View
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="view"
                value="cards"
                checked={viewMode === 'cards'}
                onChange={(e) => setViewMode(e.target.value as 'cards')}
                className="mr-2"
              />
              Card View
            </label>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Show:</span>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="border rounded px-2 py-1"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>
      </div>

      {/* Data Display */}
      {viewMode === 'table' ? (
        <div className="bg-white border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-4 border-b">ID</th>
                <th className="text-left p-4 border-b">Target</th>
                <th className="text-left p-4 border-b">Status</th>
                <th className="text-left p-4 border-b">Created</th>
                <th className="text-left p-4 border-b">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.results?.map((scan) => (
                <tr key={scan.id} className="border-b hover:bg-gray-50">
                  <td className="p-4 font-medium">{scan.id}</td>
                  <td className="p-4">{scan.target}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      scan.status === 'completed' ? 'bg-green-100 text-green-800' :
                      scan.status === 'running' ? 'bg-blue-100 text-blue-800' :
                      scan.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {scan.status.charAt(0).toUpperCase() + scan.status.slice(1)}
                    </span>
                  </td>
                  <td className="p-4 text-gray-600">
                    {scan.created_at ? new Date(scan.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="p-4">
                    <Link
                      className="text-blue-600 hover:text-blue-800 font-medium"
                      to={`/scans/${scan.id}`}
                    >
                      View Details →
                    </Link>
                  </td>
                </tr>
              )) ?? null}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.results?.map((scan) => (
            <div key={scan.id} className="bg-white border rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-lg">Scan #{scan.id}</h3>
                  <p className="text-gray-600">Target: {scan.target}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  scan.status === 'completed' ? 'bg-green-100 text-green-800' :
                  scan.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  scan.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {scan.status.charAt(0).toUpperCase() + scan.status.slice(1)}
                </span>
              </div>

              <div className="text-sm text-gray-600 mb-4">
                Created: {scan.created_at ? new Date(scan.created_at).toLocaleDateString() : '-'}
              </div>

              <Link
                className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium"
                to={`/scans/${scan.id}`}
              >
                View Details
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          )) ?? null}
        </div>
      )}

      {/* Pagination */}
      {data && data.count > pageSize && (
        <div className="flex items-center justify-between mt-6">
          <div className="text-sm text-gray-600">
            Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, data.count)} of {data.count} results
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>

            <span className="px-3 py-1 text-sm">
              Page {currentPage} of {Math.ceil(data.count / pageSize)}
            </span>

            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={currentPage >= Math.ceil(data.count / pageSize)}
              className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}