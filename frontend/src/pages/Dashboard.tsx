import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { useDashboard } from '@api/hooks/resources';

export default function Dashboard() {
  const { data, isLoading, isError } = useDashboard();

  if (isLoading) return <div>Loading dashboard…</div>;
  if (isError) return <div className="text-red-600">Failed to load dashboard</div>;

  const severity = data?.severity_counts ?? {};
  const last7 = data?.scans_last_7d ?? 0;

  const pieData = Object.entries(severity).map(([key, value]) => ({
    name: key,
    value: value as number
  }));

  const COLORS = ['#FF8042', '#FFBB28', '#00C49F', '#0088FE', '#8884D8'];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(severity).map(([sev, count]) => (
          <div key={sev} className="p-4 border rounded bg-white">
            <div className="text-xs uppercase text-gray-500">{sev}</div>
            <div className="text-2xl font-bold">{count}</div>
          </div>
        ))}
        <div className="p-4 border rounded bg-white">
          <div className="text-xs uppercase text-gray-500">Scans (7d)</div>
          <div className="text-2xl font-bold">{last7}</div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4">Vulnerability Distribution</h2>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${percent ? (percent * 100).toFixed(0) : 0}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {pieData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}