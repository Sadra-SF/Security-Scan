import React, { useState } from 'react';
import { useTargets, useTriggerScan } from '@api/hooks/resources';

export default function NewScan() {
  const [selectedTarget, setSelectedTarget] = useState<number | ''>('');
  const [mode, setMode] = useState<string>('quick');
  const trigger = useTriggerScan();
  const { data: targets, isLoading } = useTargets({ page_size: 100 });

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTarget) return;
    try {
      await trigger.mutateAsync({ target: Number(selectedTarget), mode });
      // eslint-disable-next-line no-alert
      alert('Scan triggered');
    } catch {
      // eslint-disable-next-line no-alert
      alert('Failed to trigger scan');
    }
  };

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-semibold mb-4">New Scan</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block">
          <span className="text-sm text-gray-700">Target</span>
          <select
            className="mt-1 w-full border rounded px-3 py-2"
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(Number(e.target.value))}
            disabled={isLoading}
          >
            <option value="">Select target…</option>
            {targets?.results?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} — {t.address}
              </option>
            )) ?? null}
          </select>
        </label>

        <label className="block">
          <span className="text-sm text-gray-700">Mode</span>
          <select
            className="mt-1 w-full border rounded px-3 py-2"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="quick">Quick</option>
            <option value="full">Full</option>
          </select>
        </label>

        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          disabled={!selectedTarget || trigger.isPending}
        >
          {trigger.isPending ? 'Triggering…' : 'Trigger Scan'}
        </button>
      </form>
    </div>
  );
}