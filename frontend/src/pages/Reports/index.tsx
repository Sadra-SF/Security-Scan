import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useCreateReport, useReports, downloadReport } from '@api/hooks/resources';

type ReportFormData = {
  type: string;
  template: string;
  title: string;
  includeFindings: boolean;
  includeScans: boolean;
  dateRange: string;
  severityFilter: string;
};

const REPORT_TEMPLATES = [
  { id: 'executive', name: 'Executive Summary', description: 'High-level overview for management' },
  { id: 'technical', name: 'Technical Report', description: 'Detailed technical findings' },
  { id: 'compliance', name: 'Compliance Report', description: 'Compliance-focused analysis' },
  { id: 'trending', name: 'Security Trends', description: 'Historical security trends' }
];

export default function Reports() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedReports, setSelectedReports] = useState<number[]>([]);

  const { data, isLoading, isError } = useReports({
    page: currentPage,
    page_size: 20,
    search: search || undefined
  });
  const createReport = useCreateReport();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ReportFormData>({
    defaultValues: {
      type: 'pdf',
      template: 'executive',
      title: '',
      includeFindings: true,
      includeScans: true,
      dateRange: '30',
      severityFilter: 'all'
    }
  });

  const onDownload = async (id: number, type?: string) => {
    try {
      const blob = await downloadReport(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = type === 'html' ? 'html' : type === 'markdown' ? 'md' : 'pdf';
      a.download = `security-report-${id}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Failed to download report');
    }
  };

  const onCreate = async (formData: ReportFormData) => {
    try {
      await createReport.mutateAsync({
        type: formData.type,
        template: formData.template,
        title: formData.title || `Security Report - ${new Date().toLocaleDateString()}`,
        include_findings: formData.includeFindings,
        include_scans: formData.includeScans,
        date_range: formData.dateRange,
        severity_filter: formData.severityFilter
      });
      setShowCreateForm(false);
      reset();
    } catch {
      alert('Failed to create report.');
    }
  };

  const handleSelectReport = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedReports(prev => [...prev, id]);
    } else {
      setSelectedReports(prev => prev.filter(r => r !== id));
    }
  };

  const handleBulkDownload = async () => {
    for (const id of selectedReports) {
      await onDownload(id);
    }
    setSelectedReports([]);
  };

  if (isLoading) return (
    <div className="flex justify-center py-8">
      <div className="text-gray-600">Loading reports...</div>
    </div>
  );
  if (isError) return (
    <div className="text-red-600 text-center py-8">Failed to load reports</div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Security Reports</h1>
          <p className="text-gray-600 mt-1">Generate and manage security reports</p>
        </div>
        <div className="flex gap-3">
          {selectedReports.length > 0 && (
            <button
              onClick={handleBulkDownload}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Download Selected ({selectedReports.length})
            </button>
          )}
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Generate Report
          </button>
        </div>
      </div>

      {/* Create Report Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Generate New Report</h2>
              <button
                onClick={() => setShowCreateForm(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit(onCreate)} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Report Title</label>
                  <input
                    {...register('title')}
                    className="w-full border rounded px-3 py-2"
                    placeholder="Enter report title"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
                  <select {...register('type')} className="w-full border rounded px-3 py-2">
                    <option value="pdf">PDF Document</option>
                    <option value="html">HTML Web Page</option>
                    <option value="markdown">Markdown Text</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Report Template</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {REPORT_TEMPLATES.map((template) => (
                    <label key={template.id} className="flex items-start space-x-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                      <input
                        type="radio"
                        {...register('template')}
                        value={template.id}
                        className="mt-1"
                      />
                      <div>
                        <div className="font-medium">{template.name}</div>
                        <div className="text-sm text-gray-600">{template.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Date Range</label>
                  <select {...register('dateRange')} className="w-full border rounded px-3 py-2">
                    <option value="7">Last 7 days</option>
                    <option value="30">Last 30 days</option>
                    <option value="90">Last 90 days</option>
                    <option value="365">Last year</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Severity Filter</label>
                  <select {...register('severityFilter')} className="w-full border rounded px-3 py-2">
                    <option value="all">All Severities</option>
                    <option value="critical">Critical & High</option>
                    <option value="high">High & Medium</option>
                    <option value="medium">Medium & Low</option>
                  </select>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    {...register('includeFindings')}
                    className="rounded"
                  />
                  <label className="ml-2 text-sm">Include vulnerability findings</label>
                </div>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    {...register('includeScans')}
                    className="rounded"
                  />
                  <label className="ml-2 text-sm">Include scan results</label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  disabled={createReport.isPending}
                >
                  {createReport.isPending ? 'Generating...' : 'Generate Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border">
        <div className="flex gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search reports..."
              className="w-full border rounded px-3 py-2"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="border rounded px-3 py-2"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Reports Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-4 border-b">
                <input
                  type="checkbox"
                  checked={selectedReports.length === data?.results?.length && data.results.length > 0}
                  onChange={(e) => {
                    if (selectedReports.length === data?.results?.length) {
                      setSelectedReports([]);
                    } else {
                      setSelectedReports(data?.results?.map(r => r.id) || []);
                    }
                  }}
                />
              </th>
              <th className="text-left p-4 border-b">ID</th>
              <th className="text-left p-4 border-b">Title</th>
              <th className="text-left p-4 border-b">Status</th>
              <th className="text-left p-4 border-b">Type</th>
              <th className="text-left p-4 border-b">Created</th>
              <th className="text-left p-4 border-b">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.results?.map((report) => (
              <tr key={report.id} className="border-b hover:bg-gray-50">
                <td className="p-4">
                  <input
                    type="checkbox"
                    checked={selectedReports.includes(report.id)}
                    onChange={(e) => handleSelectReport(report.id, e.target.checked)}
                  />
                </td>
                <td className="p-4 font-medium">#{report.id}</td>
                <td className="p-4">Security Report #{report.id}</td>
                <td className="p-4">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    report.status === 'completed' ? 'bg-green-100 text-green-800' :
                    report.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {report.status.charAt(0).toUpperCase() + report.status.slice(1)}
                  </span>
                </td>
                <td className="p-4">{report.type?.toUpperCase() || 'PDF'}</td>
                <td className="p-4 text-gray-600">-</td>
                <td className="p-4">
                  <div className="flex gap-2">
                    <button
                      onClick={() => onDownload(report.id, report.type || undefined)}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                      disabled={report.status !== 'completed'}
                    >
                      Download
                    </button>
                  </div>
                </td>
              </tr>
            )) ?? null}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.count > 20 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Showing {((currentPage - 1) * 20) + 1} to {Math.min(currentPage * 20, data.count)} of {data.count} reports
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm">Page {currentPage}</span>
            <button
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={currentPage * 20 >= data.count}
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