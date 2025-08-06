import React from 'react';
import { Link } from 'react-router-dom';
import { useTargets } from '@api/hooks/resources';

export default function TargetsList() {
  const { data, isLoading, isError } = useTargets({ page: 1, page_size: 20 });

  if (isLoading) return <div>Loading targets…</div>;
  if (isError) return <div className="text-red-600">Failed to load targets</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Targets</h1>
      <table className="w-full text-sm border">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left p-2 border-b">Name</th>
            <th className="text-left p-2 border-b">Address</th>
            <th className="text-left p-2 border-b">Type</th>
            <th className="text-left p-2 border-b">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.results?.map((t) => (
            <tr key={t.id} className="border-b">
              <td className="p-2">{t.name}</td>
              <td className="p-2">{t.address}</td>
              <td className="p-2">{t.type ?? '-'}</td>
              <td className="p-2">
                <Link className="text-blue-600 hover:underline" to={`/targets/${t.id}`}>
                  View
                </Link>
              </td>
            </tr>
          )) ?? null}
        </tbody>
      </table>
    </div>
  );
}