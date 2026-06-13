import { apiRequest } from "@/lib/api-client";

export interface KPISummary {
  total_alerts: number;
  unacknowledged_alerts: number;
  average_ack_time_seconds: number | null;
  average_resolve_time_seconds: number | null;
  total_incidents: number;
  resolved_incidents: number;
  average_containment_time_seconds: number | null;
  total_detections: number;
  fire_ratio: number;
  false_alarm_rate: number;
  calculated_at: string;
}

export interface TrendItem {
  date_bucket: string;
  value: number;
}

export interface TrendResponse {
  kpi_name: string;
  trends: TrendItem[];
}

export interface ReportDefinition {
  id: string;
  name: string;
  report_type: string;
  frequency: string;
  recipients: string[];
  parameters: Record<string, any>;
  created_at: string;
}

export interface ReportExecution {
  id: string;
  definition_id: string | null;
  report_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  format: "PDF" | "CSV" | "XLSX" | "JSON";
  file_path: string | null;
  started_at: string;
  completed_at: string | null;
  triggered_by: string;
}

export interface ExecutiveDashboard {
  incident_counts_by_severity: Record<string, number>;
  active_incidents_count: number;
  alerts_count_last_24h: number;
  sla_compliance_rate: number;
  regional_activity: Record<string, number>;
  updated_at: string;
}

export const analyticsService = {
  async getKPIs(bypassCache = false): Promise<KPISummary> {
    return apiRequest<KPISummary>("/analytics/kpis", {
      params: { bypass_cache: bypassCache },
    });
  },

  async getTrends(kpiName: string, days = 30): Promise<TrendResponse> {
    return apiRequest<TrendResponse>("/analytics/trends", {
      params: { kpi_name: kpiName, days },
    });
  },

  async listReportDefinitions(skip = 0, limit = 100): Promise<ReportDefinition[]> {
    return apiRequest<ReportDefinition[]>("/analytics/reports", {
      params: { skip, limit },
    });
  },

  async createReportDefinition(body: {
    name: string;
    report_type: string;
    frequency: string;
    recipients: string[];
    parameters?: Record<string, any>;
  }): Promise<ReportDefinition> {
    return apiRequest<ReportDefinition>("/analytics/reports/definitions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async generateReportAdhoc(body: { report_type: string; format: "PDF" | "CSV" | "XLSX" | "JSON"; parameters?: Record<string, any> }): Promise<ReportExecution> {
    return apiRequest<ReportExecution>("/analytics/reports/generate", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async getReportExecution(id: string): Promise<ReportExecution> {
    return apiRequest<ReportExecution>(`/analytics/reports/${id}`);
  },

  async downloadReport(executionId: string): Promise<Blob> {
    const response = await fetch(`/api/v1/analytics/export?execution_id=${executionId}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("wildfire-auth-storage") ? JSON.parse(localStorage.getItem("wildfire-auth-storage")!).state.accessToken : ""}`,
      },
    });

    if (!response.ok) {
      throw new Error("Failed to download report");
    }

    return response.blob();
  },

  async getExecutiveDashboard(bypassCache = false): Promise<ExecutiveDashboard> {
    return apiRequest<ExecutiveDashboard>("/analytics/executive-dashboard", {
      params: { bypass_cache: bypassCache },
    });
  },
};
