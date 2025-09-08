import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useFindings, useBulkUpdateFindings } from '@api/hooks/resources';

const SEVERITY_COLORS = {
  critical: '#DC2626',
  high: '#EA580C',
  medium: '#D97706',
  low: '#F59E0B',
  info: '#6B7280'
};

export default function FindingsList() {
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkStatus, setBulkStatus] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');

  const { data, isLoading, isError } = useFindings({
    page: currentPage,
    page_size: pageSize,
    search: search || undefined,
    severity: severityFilter || undefined,
    status: statusFilter || undefined
  });

  const bulkUpdate = useBulkUpdateFindings();

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(data?.results?.map(f => f.id) || []);
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelect = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedIds(prev => [...prev, id]);
    } else {
      setSelectedIds(prev => prev.filter(i => i !== id));
    }
  };

  const handleBulkUpdate = async () => {
    if (!bulkStatus || selectedIds.length === 0) return;
    try {
      await bulkUpdate.mutateAsync({ ids: selectedIds, status: bulkStatus });
      setSelectedIds([]);
      setBulkStatus('');
    } catch {
      alert('Failed to update findings');
    }
  };

  const handleExport = () => {
    const csvContent = [
      ['ID', 'Title', 'Severity', 'Status', 'Last Seen'].join(','),
      ...(data?.results?.map(finding => [
        finding.id,
        `"${finding.title}"`,
        finding.severity,
        finding.status || 'open',
        finding.last_seen || ''
      ].join(',')) || [])
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'findings.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (isLoading) return <div className="flex justify-center py-8"><div className="text-gray-600">Loading findings…</div></div>;
  if (isError) return <div className="text-red-600 text-center py-8">Failed to load findings</div>;

  // Calculate statistics for charts
  const severityCounts = data?.results?.reduce((acc, finding) => {
    acc[finding.severity] = (acc[finding.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  const statusCounts = data?.results?.reduce((acc, finding) => {
    const status = finding.status || 'open';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  const severityData = Object.entries(severityCounts).map(([severity, count]) => ({
    name: severity.charAt(0).toUpperCase() + severity.slice(1),
    value: count,
    color: SEVERITY_COLORS[severity as keyof typeof SEVERITY_COLORS] || '#6B7280'
  }));

  const statusData = Object.entries(statusCounts).map(([status, count]) => ({
    name: status.charAt(0).toUpperCase() + status.slice(1),
    value: count
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Security Findings</h1>
        <div className="flex gap-3">
          <button
            onClick={handleExport}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Export CSV
          </button>
          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2">
              <select
                className="border rounded px-3 py-2"
                value={bulkStatus}
                onChange={(e) => setBulkStatus(e.target.value)}
              >
                <option value="">Select status</option>
                <option value="open">Open</option>
                <option value="resolved">Resolved</option>
                <option value="false_positive">False Positive</option>
              </select>
              <button
                type="button"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                onClick={handleBulkUpdate}
                disabled={bulkUpdate.isPending || !bulkStatus}
              >
                {bulkUpdate.isPending ? 'Updating…' : 'Update Selected'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Total Findings</div>
          <div className="text-2xl font-bold">{data?.count || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Critical</div>
          <div className="text-2xl font-bold text-red-600">{severityCounts.critical || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">High</div>
          <div className="text-2xl font-bold text-orange-600">{severityCounts.high || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Medium</div>
          <div className="text-2xl font-bold text-yellow-600">{severityCounts.medium || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-sm text-gray-600">Open</div>
          <div className="text-2xl font-bold text-blue-600">{statusCounts.open || 0}</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg border">
          <h3 className="text-lg font-medium mb-4">Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {severityData.map((entry, index) => (
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
            <BarChart data={statusData}>
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              placeholder="Search findings..."
              className="w-full border rounded px-3 py-2"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False Positive</option>
            </select>
          </div>
          <div className="flex items-end">
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
                Table
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
                Cards
              </label>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            {selectedIds.length > 0 && `${selectedIds.length} findings selected`}
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
                <th className="p-4 border-b">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === data?.results?.length && data.results.length > 0}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                  />
                </th>
                <th className="text-left p-4 border-b">ID</th>
                <th className="text-left p-4 border-b">Severity</th>
                <th className="text-left p-4 border-b">Title</th>
                <th className="text-left p-4 border-b">Status</th>
                <th className="text-left p-4 border-b">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {data?.results?.map((finding) => (
                <tr key={finding.id} className="border-b hover:bg-gray-50">
                  <td className="p-4">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(finding.id)}
                      onChange={(e) => handleSelect(finding.id, e.target.checked)}
                    />
                  </td>
                  <td className="p-4 font-medium">#{finding.id}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      finding.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      finding.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                      finding.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      finding.severity === 'low' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {finding.severity.charAt(0).toUpperCase() + finding.severity.slice(1)}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="max-w-xs truncate" title={finding.title}>
                      {finding.title}
                    </div>
                  </td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      finding.status === 'resolved' ? 'bg-green-100 text-green-800' :
                      finding.status === 'false_positive' ? 'bg-gray-100 text-gray-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {(finding.status || 'open').replace('_', ' ').charAt(0).toUpperCase() + (finding.status || 'open').slice(1)}
                    </span>
                  </td>
                  <td className="p-4 text-gray-600">
                    {finding.last_seen ? new Date(finding.last_seen).toLocaleDateString() : '-'}
                  </td>
                </tr>
              )) ?? null}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.results?.map((finding) => (
            <div key={finding.id} className="bg-white border rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-lg">#{finding.id}</h3>
                  <p className="text-gray-600 text-sm truncate" title={finding.title}>
                    {finding.title}
                  </p>
                </div>
                <div className="flex flex-col gap-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium self-start ${
                    finding.severity === 'critical' ? 'bg-red-100 text-red-800' :
                    finding.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                    finding.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    finding.severity === 'low' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {finding.severity.charAt(0).toUpperCase() + finding.severity.slice(1)}
                  </span>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(finding.id)}
                    onChange={(e) => handleSelect(finding.id, e.target.checked)}
                    className="rounded"
                  />
                </div>
              </div>

              <div className="space-y-2 text-sm text-gray-600">
                <div>Status: <span className={`px-2 py-1 rounded text-xs font-medium ${
                  finding.status === 'resolved' ? 'bg-green-100 text-green-800' :
                  finding.status === 'false_positive' ? 'bg-gray-100 text-gray-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {(finding.status || 'open').replace('_', ' ')}
                </span></div>
                <div>Last Seen: {finding.last_seen ? new Date(finding.last_seen).toLocaleDateString() : '-'}</div>
              </div>
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