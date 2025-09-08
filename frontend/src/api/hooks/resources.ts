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
  status: z.string().optional(),
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

const Evidence = z.object({
  id: z.string(),
  kind: z.string(),
  file_url: z.string().optional().nullable(),
  storage_url: z.string().optional().nullable(),
  content_type: z.string().optional().nullable(),
  size: z.number().optional().nullable(),
  metadata: z.record(z.any()).optional().default({}),
  correlation_id: z.string().optional().nullable(),
  correlation_type: z.string().optional().nullable(),
  tags: z.array(z.string()).optional().default([]),
  created_at: z.string(),
  correlated_evidence_count: z.number().optional().default(0),
  evidence_chain_length: z.number().optional().default(0)
});
const EvidencePage = Pagination.extend({ results: z.array(Evidence) });

const DashboardSummary = z.object({
  open_by_severity: z.record(z.string(), z.number()).optional().default({}),
  scans_last_7d: z.number().optional().default(0),
  new_last_7d: z.number().optional().default(0),
  top_targets: z.array(z.object({
    id: z.number(),
    name: z.string(),
    open_count: z.number()
  })).optional().default([]),
  compliance_counts: z.record(z.string(), z.number()).optional().default({})
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
export function useCreateTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['targets', 'create'],
    mutationFn: async (payload: { name: string; address: string; type?: string }) => {
      const { data } = await api.post('/api/v1/targets/', payload);
      return Target.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['targets'] });
    }
  });
}
export function useUpdateTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['targets', 'update'],
    mutationFn: async ({ id, payload }: { id: number; payload: { name?: string; address?: string; type?: string } }) => {
      const { data } = await api.patch(`/api/v1/targets/${id}/`, payload);
      return Target.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['targets'] });
    }
  });
}
export function useDeleteTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['targets', 'delete'],
    mutationFn: async (id: number) => {
      await api.delete(`/api/v1/targets/${id}/`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['targets'] });
    }
  });
}

/**
 * Scans
 */
export function useScans(params?: PageParams & { target?: number; status?: string }) {
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
export function useBulkUpdateFindings() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['findings', 'bulk-update'],
    mutationFn: async (payload: { ids: number[]; status: string }) => {
      const { data } = await api.patch('/api/v1/findings/bulk-update/', payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['findings'] });
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

/**
 * Evidence
 */
export function useEvidence(params?: PageParams & { finding?: string; kind?: string; correlation_id?: string }) {
  return useQuery({
    queryKey: ['evidence', params],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/evidence/${toQS(params)}`);
      return EvidencePage.parse(data);
    }
  });
}

export function useEvidenceItem(id?: string) {
  return useQuery({
    enabled: !!id,
    queryKey: ['evidence', 'detail', id],
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/evidence/${id}/`);
      return Evidence.parse(data);
    }
  });
}

export function useEvidenceStats() {
  return useQuery({
    queryKey: ['evidence', 'stats'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/evidence/stats/');
      return data;
    }
  });
}

export function useUploadEvidence() {
  const qc = useQueryClient();
  return useMutation({
    mutationKey: ['evidence', 'upload'],
    mutationFn: async (payload: FormData) => {
      const { data } = await api.post('/api/v1/evidence/upload/', payload, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return Evidence.parse(data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['evidence'] });
    }
  });
}

export async function downloadEvidence(evidenceId: string) {
  const resp = await api.get(`/api/v1/evidence/${evidenceId}/download/`, { responseType: 'blob' });
  return resp.data as Blob;
}

export async function exportFindingsCSV(params?: Record<string, any>) {
  const resp = await api.get('/api/v1/findings/export-csv/', {
    params,
    responseType: 'blob'
  });
  return resp.data as Blob;
}

export function useFindingsTrends() {
  return useQuery({
    queryKey: ['findings', 'trends'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/findings/trends/');
      return data;
    }
  });
}