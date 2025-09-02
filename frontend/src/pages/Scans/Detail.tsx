import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useScan, useTarget, useFindings } from '@api/hooks/resources';

export default function ScanDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: scan, isLoading: scanLoading, isError: scanError } = useScan(id);
  const { data: target } = useTarget(scan?.target);
  const { data: findings } = useFindings({ target: scan?.target });

  if (scanLoading) return <div>Loading scan details…</div>;
  if (scanError || !scan) return <div className="text-red-600">Failed to load scan</div>;

  const progress = scan.status === 'running' ? 50 : scan.status === 'completed' ? 100 : 0;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Scan #{scan.id}</h1>
        <Link to="/scans" className="text-blue-600 hover:underline">
          Back to Scans
        </Link>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Status</label>
            <span className={`px-2 py-1 rounded text-sm ${
              scan.status === 'completed' ? 'bg-green-100 text-green-800' :
              scan.status === 'running' ? 'bg-blue-100 text-blue-800' :
              scan.status === 'failed' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {scan.status}
            </span>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Target</label>
            <p>{target ? `${target.name} (${target.address})` : `ID: ${scan.target}`}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Created</label>
            <p>{scan.created_at ? new Date(scan.created_at).toLocaleString() : '-'}</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Progress</label>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-600 mt-1">{progress}% complete</p>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-4">Findings</h2>
        {findings?.results?.length ? (
          <table className="w-full text-sm border">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-2 border-b">Severity</th>
                <th className="text-left p-2 border-b">Title</th>
                <th className="text-left p-2 border-b">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {findings.results.map((finding) => (
                <tr key={finding.id} className="border-b">
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
                  <td className="p-2">{finding.last_seen ? new Date(finding.last_seen).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-600">No findings found for this scan.</p>
        )}
      </div>
    </div>
  );
}