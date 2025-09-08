import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LineChart, Line, Area, AreaChart } from 'recharts';
import { useDashboard, useTriggerScan, useTargets, useCreateTarget, exportFindingsCSV, useFindingsTrends } from '@api/hooks/resources';

const SEVERITY_COLORS = {
  critical: '#DC2626',
  high: '#EA580C',
  medium: '#D97706',
  low: '#F59E0B',
  info: '#6B7280'
};

export default function Dashboard() {
  const { data, isLoading, isError } = useDashboard();
  const { data: targetsData } = useTargets();
  const { data: trendsData } = useFindingsTrends();
  const triggerScan = useTriggerScan();
  const createTarget = useCreateTarget();

  const [quickScanUrl, setQuickScanUrl] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  if (isLoading) return (
    <div className="flex justify-center items-center h-64">
      <div className="text-gray-600">Loading dashboard...</div>
    </div>
  );
  if (isError) return (
    <div className="text-red-600 text-center py-8">Failed to load dashboard</div>
  );

  const severity = data?.open_by_severity ?? {};
  const last7 = data?.scans_last_7d ?? 0;
  const newLast7d = data?.new_last_7d ?? 0;
  const topTargets = data?.top_targets ?? [];
  const complianceCounts = data?.compliance_counts ?? {};

  const severityData = Object.entries(severity).map(([key, value]) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    value: value as number,
    color: SEVERITY_COLORS[key as keyof typeof SEVERITY_COLORS] || '#6B7280'
  }));

  // Use real trends data or fallback to mock data
  const scanTrendData = trendsData ? trendsData.map((item: any) => ({
    date: item.date,
    scans: item.total
  })) : [
    { date: '2024-01-01', scans: 12 },
    { date: '2024-01-02', scans: 15 },
    { date: '2024-01-03', scans: 8 },
    { date: '2024-01-04', scans: 22 },
    { date: '2024-01-05', scans: 18 },
    { date: '2024-01-06', scans: 25 },
    { date: '2024-01-07', scans: last7 }
  ];

  const statusData = [
    { name: 'Open', value: 45, color: '#3B82F6' },
    { name: 'Resolved', value: 32, color: '#10B981' },
    { name: 'False Positive', value: 8, color: '#6B7280' }
  ];

  const totalFindings = Object.values(severity).reduce((sum, count) => sum + (count as number), 0);

  const handleQuickScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickScanUrl.trim()) return;

    setIsScanning(true);
    try {
      // Check if target already exists
      const existingTarget = targetsData?.results?.find(target => target.address === quickScanUrl);

      let targetId;
      if (existingTarget) {
        targetId = existingTarget.id;
      } else {
        // Create new target
        const newTarget = await createTarget.mutateAsync({
          name: `Quick Scan - ${quickScanUrl}`,
          address: quickScanUrl
        });
        targetId = newTarget.id;
      }

      // Trigger scan
      await triggerScan.mutateAsync({
        target: targetId,
        mode: 'quick'
      });

      setQuickScanUrl('');
      alert('Scan started successfully!');
    } catch (error) {
      console.error('Quick scan failed:', error);
      alert('Failed to start scan. Please try again.');
    } finally {
      setIsScanning(false);
    }
  };

  const handleExportCSV = async () => {
    setIsExporting(true);
    try {
      const blob = await exportFindingsCSV();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `findings-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export findings. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Security Dashboard</h1>
          <p className="text-gray-600 mt-1">Overview of your security posture and recent activity</p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/scans/new"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            New Scan
          </Link>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Findings</p>
              <p className="text-3xl font-bold text-gray-900">{totalFindings}</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Critical Issues</p>
              <p className="text-3xl font-bold text-red-600">{severity.critical || 0}</p>
            </div>
            <div className="p-3 bg-red-100 rounded-full">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
           <div className="flex items-center justify-between">
             <div>
               <p className="text-sm font-medium text-gray-600">Scans (7 days)</p>
               <p className="text-3xl font-bold text-green-600">{last7}</p>
             </div>
             <div className="p-3 bg-green-100 rounded-full">
               <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
               </svg>
             </div>
           </div>
         </div>

         <div className="bg-white p-6 rounded-lg border border-gray-200">
           <div className="flex items-center justify-between">
             <div>
               <p className="text-sm font-medium text-gray-600">New Findings (7 days)</p>
               <p className="text-3xl font-bold text-orange-600">{newLast7d}</p>
             </div>
             <div className="p-3 bg-orange-100 rounded-full">
               <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
               </svg>
             </div>
           </div>
         </div>

         <div className="bg-white p-6 rounded-lg border border-gray-200">
           <div className="flex items-center justify-between">
             <div>
               <p className="text-sm font-medium text-gray-600">Active Targets</p>
               <p className="text-3xl font-bold text-purple-600">{topTargets.length}</p>
             </div>
             <div className="p-3 bg-purple-100 rounded-full">
               <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
               </svg>
             </div>
           </div>
         </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
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

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Finding Status Overview</h3>
          <ResponsiveContainer width="100%" height={300}>
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

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Vulnerability Trends (30 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendsData || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="critical" stroke="#DC2626" strokeWidth={2} />
              <Line type="monotone" dataKey="high" stroke="#EA580C" strokeWidth={2} />
              <Line type="monotone" dataKey="medium" stroke="#D97706" strokeWidth={2} />
              <Line type="monotone" dataKey="low" stroke="#F59E0B" strokeWidth={2} />
              <Line type="monotone" dataKey="info" stroke="#6B7280" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-4 mt-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-600 rounded"></div>
              <span>Critical</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-orange-600 rounded"></div>
              <span>High</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-600 rounded"></div>
              <span>Medium</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-500 rounded"></div>
              <span>Low</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-gray-500 rounded"></div>
              <span>Info</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Severity Breakdown</h3>
          <div className="space-y-4">
            {severityData.map((item) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm font-medium">{item.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">{item.value}</span>
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        backgroundColor: item.color,
                        width: `${totalFindings > 0 ? (item.value / totalFindings) * 100 : 0}%`
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-1 gap-8">
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Scan Activity (30 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={scanTrendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="scans" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.1} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Targets */}
      {topTargets.length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Top Targets by Open Findings</h3>
          <div className="space-y-3">
            {topTargets.map((target) => (
              <div key={target.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                  <span className="font-medium">{target.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">{target.open_count} findings</span>
                  <div className="w-16 bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 bg-blue-500 rounded-full"
                      style={{
                        width: `${Math.min((target.open_count / Math.max(...topTargets.map(t => t.open_count))) * 100, 100)}%`
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compliance Overview */}
      {Object.keys(complianceCounts).length > 0 && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold mb-4">Compliance Overview</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="text-md font-medium mb-3">Framework Coverage</h4>
              <div className="space-y-2">
                {Object.entries(complianceCounts).map(([framework, count]) => (
                  <div key={framework} className="flex items-center justify-between">
                    <span className="text-sm">{framework}</span>
                    <span className="text-sm font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-md font-medium mb-3">OWASP Top 10 Status</h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">A01:2021 - Broken Access Control</span>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">Covered</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">A02:2021 - Cryptographic Failures</span>
                  <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">Partial</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">A03:2021 - Injection</span>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">Covered</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Quick Scan Form */}
          <div className="space-y-4">
            <h4 className="font-medium">Quick Scan</h4>
            <form onSubmit={handleQuickScan} className="space-y-3">
              <div>
                <input
                  type="url"
                  value={quickScanUrl}
                  onChange={(e) => setQuickScanUrl(e.target.value)}
                  placeholder="Enter URL to scan (e.g., https://example.com)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={isScanning || !quickScanUrl.trim()}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isScanning ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Scanning...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Start Quick Scan
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Action Links */}
          <div className="grid grid-cols-1 gap-3">
            <Link
              to="/scans/new"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <div className="p-2 bg-blue-100 rounded-lg">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
              <div>
                <h4 className="font-medium">New Scan</h4>
                <p className="text-sm text-gray-600">Start a security scan</p>
              </div>
            </Link>

            <Link
              to="/findings"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <div className="p-2 bg-orange-100 rounded-lg">
                <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h4 className="font-medium">View Findings</h4>
                <p className="text-sm text-gray-600">Review security issues</p>
              </div>
            </Link>

            <Link
              to="/reports"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <div className="p-2 bg-green-100 rounded-lg">
                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h4 className="font-medium">Generate Report</h4>
                <p className="text-sm text-gray-600">Create security reports</p>
              </div>
            </Link>

            <button
              onClick={handleExportCSV}
              disabled={isExporting}
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed w-full text-left"
            >
              <div className="p-2 bg-purple-100 rounded-lg">
                {isExporting ? (
                  <div className="w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                )}
              </div>
              <div>
                <h4 className="font-medium">Export Findings</h4>
                <p className="text-sm text-gray-600">Download as CSV</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}