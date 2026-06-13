import { apiRequest } from "@/lib/api-client";

export interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  logger: string;
  correlation_id: string | null;
  metadata_json: Record<string, any> | null;
}

export interface MetricEntry {
  id: string;
  name: string;
  value: number;
  timestamp: string;
  labels_json: Record<string, any> | null;
}

export interface TraceSpan {
  id: string;
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  name: string;
  service_name: string;
  start_time: string;
  end_time: string;
  duration_ms: number;
  status: string;
  error_message: string | null;
  metadata_json: Record<string, any> | null;
}

export const observabilityService = {
  async getMetrics(params: { name?: string; skip?: number; limit?: number }): Promise<{ live: any; historical: { total: number; items: MetricEntry[] } }> {
    return apiRequest<{ live: any; historical: { total: number; items: MetricEntry[] } }>("/observability/metrics", { params: params as any });
  },

  async getLogs(params: {
    level?: string;
    logger_name?: string;
    correlation_id?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<{ total: number; items: LogEntry[] }> {
    return apiRequest<{ total: number; items: LogEntry[] }>("/observability/logs", { params: params as any });
  },

  async getTraces(traceId?: string, limit = 20): Promise<any> {
    const params: any = { limit };
    if (traceId) params.trace_id = traceId;
    return apiRequest<any>("/observability/traces", { params });
  },

  async getPlatformHealth(): Promise<any> {
    return apiRequest<any>("/observability/health");
  },

  async getSLOCompliance(): Promise<any> {
    return apiRequest<any>("/observability/slo");
  },

  async getReliabilityDashboard(): Promise<any> {
    return apiRequest<any>("/observability/reliability");
  },

  async getPerformanceAnalytics(endpoint?: string, hours = 24): Promise<any> {
    const params: any = { hours };
    if (endpoint) params.endpoint = endpoint;
    return apiRequest<any>("/observability/performance", { params });
  },
};
