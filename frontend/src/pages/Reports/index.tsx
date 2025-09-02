import React from 'react';
import { useForm } from 'react-hook-form';
import { useCreateReport, useReports, downloadReport } from '@api/hooks/resources';

export default function Reports() {
  const { data, isLoading, isError } = useReports({ page_size: 20 });
  const createReport = useCreateReport();
  const { register, handleSubmit, formState: { errors } } = useForm<{ type: string }>({
    defaultValues: { type: 'pdf' }
  });

  const onDownload = async (id: number, type?: string) => {
    try {
      const blob = await downloadReport(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = type === 'html' ? 'html' : type === 'markdown' ? 'md' : 'pdf';
      a.download = `report-${id}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // eslint-disable-next-line no-alert
      alert('Failed to download report');
    }
  };

  const onCreate = async (data: { type: string }) => {
    try {
      await createReport.mutateAsync(data);
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
        <form onSubmit={handleSubmit(onCreate)} className="flex items-center gap-2">
          <select
            {...register('type')}
            className="border rounded px-3 py-1"
          >
            <option value="pdf">PDF</option>
            <option value="html">HTML</option>
            <option value="markdown">Markdown</option>
          </select>
          <button
            type="submit"
            className="px-3 py-1 rounded border hover:bg-gray-50 disabled:opacity-50"
            disabled={createReport.isPending}
          >
            {createReport.isPending ? 'Creating…' : 'Create Report'}
          </button>
        </form>
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
                  onClick={() => onDownload(r.id, r.type || undefined)}
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