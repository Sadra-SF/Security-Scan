import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { api } from '@api/client';

/**
 * Zod schemas (simplified) to do light runtime validation.
 * Adjust shapes as your backend serializers evolve.
 */
const Pagination = z.object({
  count: z.number(),
  next: z.string().nullable().optional(),
  previous: z.string().nullable().optional(),
  results: z.array(z.any())
});

const Target = z.object({
  id: z.number(),
  name: z.string(),
  address: z.string(),
  type: z.string().optional().nullable()
});
const TargetsPage = Pagination.extend({ results: z.array(Target) });

const Scan = z.object({
  id: z.number(),
  target: z.number(),
  status: z.string(),
  created_at: z.string().optional().nullable()
});
const ScansPage = Pagination.extend({ results: z.array(Scan) });

const Finding = z.object({
  id: z.number(),
  severity: z.string(),
  title: z.string(),
  target: z.number().optional().nullable(),
  last_seen: z.string().optional().nullable()
});
const FindingsPage = Pagination.extend({ results: z.array(Finding) });

const Report = z.object({
  id: z.number(),
  status: z.string(),
  type: z.string().optional().nullable()
});
const ReportsPage = Pagination.extend({ results: z.array(Report) });

const DashboardSummary = z.object({
  severity_counts: z.record(z.string(), z.number()).optional().default({}),
  scans_last_7d: z.number().optional().default(0)
});

/**
 * Query helpers
 */
type PageParams = { page?: number; page_size?: number; search?: string };

function toQS(params?: Record<string, any>) {
  const u = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') u.set(k, String(v));
  });
  const s = u.toString();
  return s ? `?${s}` : '';
}

/**
 * Dashboard
 */
export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/findings/dashboard-summary');
      return DashboardSummary.parse(data);
    }
  });
}

/**
 * Targets
 */
export function useTargets(params?: PageParams) {
  return useQuery({
    queryKey: ['targets', params],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/targets/${toQS(params)}`);
      return TargetsPage.parse(data);
    }
  });
}
export function useTarget(id?: number | string) {
  return useQuery({
    enabled: !!id,
    queryKey: ['targets', 'detail', id],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/targets/${id}/`);
      return Target.parse(data);
    }
  });
}
export function useTestConnection() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['targets', 'test-connection'],
    mutationFn: async (id: number | string) => {
      const { data } = await api.post(`/api/v1/targets/${id}/test-connection/`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['targets'] });
    }
  });
}

/**
 * Scans
 */
export function useScans(params?: PageParams & { target?: number }) {
  return useQuery({
    queryKey: ['scans', params],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/scans/${toQS(params)}`);
      return ScansPage.parse(data);
    }
  });
}
export function useScan(id?: number | string) {
  return useQuery({
    enabled: !!id,
    queryKey: ['scans', 'detail', id],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/scans/${id}/`);
      return Scan.parse(data);
    }
  });
}
export function useTriggerScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['scans', 'trigger'],
    mutationFn: async (payload: { target: number; mode?: string }) => {
      const { data } = await api.post('/api/v1/scans/trigger/', payload);
      return Scan.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scans'] });
    }
  });
}

/**
 * Findings
 */
export function useFindings(params?: PageParams & { severity?: string; status?: string }) {
  return useQuery({
    queryKey: ['findings', params],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/findings/${toQS(params)}`);
      return FindingsPage.parse(data);
    }
  });
}

/**
 * Reports
 */
export function useReports(params?: PageParams) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/reports/${toQS(params)}`);
      return ReportsPage.parse(data);
    }
  });
}
export function useCreateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['reports', 'create'],
    mutationFn: async (payload: Record<string, any>) => {
      const { data } = await api.post('/api/v1/reports/', payload);
      return Report.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reports'] });
    }
  });
}
export async function downloadReport(reportId: number | string) {
  const resp = await api.get(`/api/v1/reports/${reportId}/download/`, { responseType: 'blob' });
  return resp.data as Blob;
}