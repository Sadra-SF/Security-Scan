import React from 'react';
import { useCreateReport, useReports, downloadReport } from '@api/hooks/resources';

export default function Reports() {
  const { data, isLoading, isError } = useReports({ page_size: 20 });
  const createReport = useCreateReport();

  const onDownload = async (id: number) => {
    try {
      const blob = await downloadReport(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // eslint-disable-next-line no-alert
      alert('Failed to download report');
    }
  };

  const onCreate = async () => {
    try {
      await createReport.mutateAsync({ type: 'pdf' });
      // eslint-disable-next-line no-alert
      alert('Report creation started.');
    } catch {
      // eslint-disable-next-line no-alert
      alert('Failed to create report.');
    }
  };

  if (isLoading) return <div>Loading reports…</div>;
  if (isError) return <div className="text-red-600">Failed to load reports</div>;

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Reports</h1>
        <button
          type="button"
          className="px-3 py-1 rounded border hover:bg-gray-50"
          onClick={onCreate}
          disabled={createReport.isPending}
        >
          {createReport.isPending ? 'Creating…' : 'Create Report'}
        </button>
      </header>

      <table className="w-full text-sm border">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left p-2 border-b">ID</th>
            <th className="text-left p-2 border-b">Status</th>
            <th className="text-left p-2 border-b">Type</th>
            <th className="text-left p-2 border-b">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.results?.map((r) => (
            <tr key={r.id} className="border-b">
              <td className="p-2">{r.id}</td>
              <td className="p-2">{r.status}</td>
              <td className="p-2">{r.type ?? '-'}</td>
              <td className="p-2">
                <button
                  type="button"
                  className="text-blue-600 hover:underline"
                  onClick={() => onDownload(r.id)}
                >
                  Download
                </button>
              </td>
            </tr>
          )) ?? null}
        </tbody>
      </table>
    </div>
  );
}