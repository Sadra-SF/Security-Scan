import React, { useState } from 'react';
import { useFindings, useBulkUpdateFindings } from '@api/hooks/resources';

export default function FindingsList() {
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkStatus, setBulkStatus] = useState('');

  const { data, isLoading, isError } = useFindings({
    page_size: 20,
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
      alert('Findings updated successfully');
    } catch {
      alert('Failed to update findings');
    }
  };

  if (isLoading) return <div>Loading findings…</div>;
  if (isError) return <div className="text-red-600">Failed to load findings</div>;

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Findings</h1>
        {selectedIds.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              className="border rounded px-3 py-1"
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
              className="px-3 py-1 rounded border bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              onClick={handleBulkUpdate}
              disabled={bulkUpdate.isPending || !bulkStatus}
            >
              {bulkUpdate.isPending ? 'Updating…' : 'Update Selected'}
            </button>
          </div>
        )}
      </header>

      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search findings..."
          className="border rounded px-3 py-2 flex-1"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="border rounded px-3 py-2"
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
        <select
          className="border rounded px-3 py-2"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="false_positive">False Positive</option>
        </select>
      </div>

      <table className="w-full text-sm border">
        <thead className="bg-gray-50">
          <tr>
            <th className="p-2 border-b">
              <input
                type="checkbox"
                checked={selectedIds.length === data?.results?.length && data.results.length > 0}
                onChange={(e) => handleSelectAll(e.target.checked)}
              />
            </th>
            <th className="text-left p-2 border-b">ID</th>
            <th className="text-left p-2 border-b">Severity</th>
            <th className="text-left p-2 border-b">Title</th>
            <th className="text-left p-2 border-b">Status</th>
            <th className="text-left p-2 border-b">Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {data?.results?.map((finding) => (
            <tr key={finding.id} className="border-b">
              <td className="p-2">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(finding.id)}
                  onChange={(e) => handleSelect(finding.id, e.target.checked)}
                />
              </td>
              <td className="p-2">{finding.id}</td>
              <td className="p-2">
                <span className={`px-2 py-1 rounded text-xs ${
                  finding.severity === 'critical' ? 'bg-red-100 text-red-800' :
                  finding.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                  finding.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-green-100 text-green-800'
                }`}>
                  {finding.severity}
                </span>
              </td>
              <td className="p-2">{finding.title}</td>
              <td className="p-2">{finding.status || 'open'}</td>
              <td className="p-2">{finding.last_seen ? new Date(finding.last_seen).toLocaleDateString() : '-'}</td>
            </tr>
          )) ?? null}
        </tbody>
      </table>
    </div>
  );
}