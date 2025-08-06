import React from 'react';
import { useParams } from 'react-router-dom';
import { useTarget, useScans, useFindings, useTestConnection, useTriggerScan } from '@api/hooks/resources';

export default function TargetDetail() {
  const params = useParams();
  const id = Number(params.id);
  const { data: target, isLoading, isError } = useTarget(id);
  const { data: scans } = useScans({ target: id, page_size: 10 });
  const { data: findings } = useFindings({ page_size: 10, search: String(id) });
  const testConn = useTestConnection();
  const trigger = useTriggerScan();

  if (isLoading) return <div>Loading target…</div>;
  if (isError || !target) return <div className="text-red-600">Failed to load target</div>;

  const onTest = async () => {
    try {
      await testConn.mutateAsync(id);
      // eslint-disable-next-line no-alert
      alert('Connection OK (or check backend response).');
    } catch {
      // eslint-disable-next-line no-alert
      alert('Connection test failed.');
    }
  };
  const onTrigger = async () => {
    try {
      await trigger.mutateAsync({ target: id, mode: 'quick' });
      // eslint-disable-next-line no-alert
      alert('Scan triggered.');
    } catch {
      // eslint-disable-next-line no-alert
      alert('Failed to trigger scan.');
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{target.name}</h1>
          <div className="text-sm text-gray-600">{target.address}</div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="px-3 py-1 rounded border hover:bg-gray-50"
            onClick={onTest}
            disabled={testConn.isPending}
          >
            {testConn.isPending ? 'Testing…' : 'Test Connection'}
          </button>
          <button
            type="button"
            className="px-3 py-1 rounded border hover:bg-gray-50"
            onClick={onTrigger}
            disabled={trigger.isPending}
          >
            {trigger.isPending ? 'Triggering…' : 'Trigger Scan'}
          </button>
        </div>
      </header>

      <section>
        <h2 className="font-medium mb-2">Recent Scans</h2>
        <ul className="space-y-1">
          {scans?.results?.map((s) => (
            <li key={s.id} className="text-sm">
              #{s.id} — {s.status}
            </li>
          )) ?? <li className="text-sm text-gray-500">No scans</li>}
        </ul>
      </section>

      <section>
        <h2 className="font-medium mb-2">Recent Findings</h2>
        <ul className="space-y-1">
          {findings?.results?.map((f) => (
            <li key={f.id} className="text-sm">
              [{f.severity}] {f.title}
            </li>
          )) ?? <li className="text-sm text-gray-500">No findings</li>}
        </ul>
      </section>
    </div>
  );
}