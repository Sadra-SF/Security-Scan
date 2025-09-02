import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useTargets, useCreateTarget, useUpdateTarget, useDeleteTarget } from '@api/hooks/resources';

export default function TargetsList() {
  const { data, isLoading, isError } = useTargets({ page: 1, page_size: 20 });
  const createTarget = useCreateTarget();
  const updateTarget = useUpdateTarget();
  const deleteTarget = useDeleteTarget();
  const [editingId, setEditingId] = useState<number | null>(null);
  const { register: registerCreate, handleSubmit: handleSubmitCreate, reset: resetCreate } = useForm<{ name: string; address: string; type: string }>();
  const { register: registerEdit, handleSubmit: handleSubmitEdit, reset: resetEdit, setValue } = useForm<{ name: string; address: string; type: string }>();

  const onCreate = async (data: { name: string; address: string; type: string }) => {
    try {
      await createTarget.mutateAsync(data);
      resetCreate();
      alert('Target created');
    } catch {
      alert('Failed to create target');
    }
  };

  const onEdit = (target: any) => {
    setEditingId(target.id);
    setValue('name', target.name);
    setValue('address', target.address);
    setValue('type', target.type || '');
  };

  const onUpdate = async (data: { name: string; address: string; type: string }) => {
    if (!editingId) return;
    try {
      await updateTarget.mutateAsync({ id: editingId, payload: data });
      setEditingId(null);
      resetEdit();
      alert('Target updated');
    } catch {
      alert('Failed to update target');
    }
  };

  const onDelete = async (id: number) => {
    if (!confirm('Are you sure?')) return;
    try {
      await deleteTarget.mutateAsync(id);
      alert('Target deleted');
    } catch {
      alert('Failed to delete target');
    }
  };

  if (isLoading) return <div>Loading targets…</div>;
  if (isError) return <div className="text-red-600">Failed to load targets</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Targets</h1>

      <form onSubmit={handleSubmitCreate(onCreate)} className="flex gap-4 items-end">
        <label className="block flex-1">
          <span className="text-sm text-gray-700">Name</span>
          <input {...registerCreate('name', { required: true })} className="mt-1 w-full border rounded px-3 py-2" placeholder="Target name" />
        </label>
        <label className="block flex-1">
          <span className="text-sm text-gray-700">Address</span>
          <input {...registerCreate('address', { required: true })} className="mt-1 w-full border rounded px-3 py-2" placeholder="Target address" />
        </label>
        <label className="block flex-1">
          <span className="text-sm text-gray-700">Type</span>
          <select {...registerCreate('type')} className="mt-1 w-full border rounded px-3 py-2">
            <option value="">Select type</option>
            <option value="web">Web</option>
            <option value="api">API</option>
            <option value="host">Host</option>
          </select>
        </label>
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50" disabled={createTarget.isPending}>
          {createTarget.isPending ? 'Creating…' : 'Create'}
        </button>
      </form>
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
            editingId === t.id ? (
              <tr key={t.id} className="border-b">
                <td className="p-2">
                  <input {...registerEdit('name', { required: true })} className="w-full border rounded px-2 py-1" />
                </td>
                <td className="p-2">
                  <input {...registerEdit('address', { required: true })} className="w-full border rounded px-2 py-1" />
                </td>
                <td className="p-2">
                  <select {...registerEdit('type')} className="w-full border rounded px-2 py-1">
                    <option value="">Select type</option>
                    <option value="web">Web</option>
                    <option value="api">API</option>
                    <option value="host">Host</option>
                  </select>
                </td>
                <td className="p-2">
                  <button type="submit" form="edit-form" className="text-green-600 hover:underline mr-2">Save</button>
                  <button type="button" onClick={() => setEditingId(null)} className="text-gray-600 hover:underline">Cancel</button>
                </td>
              </tr>
            ) : (
              <tr key={t.id} className="border-b">
                <td className="p-2">{t.name}</td>
                <td className="p-2">{t.address}</td>
                <td className="p-2">{t.type ?? '-'}</td>
                <td className="p-2">
                  <Link className="text-blue-600 hover:underline mr-2" to={`/targets/${t.id}`}>
                    View
                  </Link>
                  <button type="button" onClick={() => onEdit(t)} className="text-blue-600 hover:underline mr-2">Edit</button>
                  <button type="button" onClick={() => onDelete(t.id)} className="text-red-600 hover:underline">Delete</button>
                </td>
              </tr>
            )
          )) ?? null}
        </tbody>
      </table>
      <form id="edit-form" onSubmit={handleSubmitEdit(onUpdate)} className="hidden"></form>
    </div>
  );
}