import { apiRequest } from "@/lib/api-client";

export interface Alert {
  id: string;
  detection_id: string | null;
  severity: "Critical" | "High" | "Medium" | "Low" | "Informational";
  status: "active" | "acknowledged" | "resolved" | "escalated";
  message: string;
  payload: Record<string, any>;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  acknowledged_by_id: string | null;
  resolved_by_id: string | null;
}

export interface AlertDetails extends Alert {
  notifications: any[];
  audit_logs: any[];
}

export interface AlertPreference {
  id: string;
  channel: "email" | "sms" | "webhook" | "push";
  enabled: boolean;
  min_severity: "Critical" | "High" | "Medium" | "Low" | "Informational";
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
}

export interface AlertPreferenceUpdate {
  channel: "email" | "sms" | "webhook" | "push";
  enabled: boolean;
  min_severity: "Critical" | "High" | "Medium" | "Low" | "Informational";
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
}

export interface AlertHistoryResponse {
  alerts: Alert[];
  total_count: number;
}

export interface AlertAuditHistoryResponse {
  logs: any[];
  total_count: number;
}

export const alertService = {
  async triggerManualAlert(body: { detection_id: string; severity: string; message: string; payload?: any }): Promise<Alert> {
    return apiRequest<Alert>("/alerts", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listAlerts(params: {
    skip?: number;
    limit?: number;
    status?: string;
    severity?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<AlertHistoryResponse> {
    return apiRequest<AlertHistoryResponse>("/alerts", {
      params: params as any,
    });
  },

  async getAuditHistory(skip = 0, limit = 100, alertId?: string): Promise<AlertAuditHistoryResponse> {
    return apiRequest<AlertAuditHistoryResponse>("/alerts/history", {
      params: { skip, limit, ...(alertId && { alert_id: alertId }) },
    });
  },

  async getStatistics(): Promise<any> {
    return apiRequest<any>("/alerts/statistics");
  },

  async getMyPreferences(): Promise<AlertPreference[]> {
    return apiRequest<AlertPreference[]>("/alerts/preferences");
  },

  async updateMyPreferences(body: AlertPreferenceUpdate[]): Promise<AlertPreference[]> {
    return apiRequest<AlertPreference[]>("/alerts/preferences", {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  async getAlertById(id: string): Promise<AlertDetails> {
    return apiRequest<AlertDetails>(`/alerts/${id}`);
  },

  async acknowledgeAlert(id: string, notes: string): Promise<Alert> {
    return apiRequest<Alert>(`/alerts/${id}/acknowledge`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
  },

  async resolveAlert(id: string, notes: string): Promise<Alert> {
    return apiRequest<Alert>(`/alerts/${id}/resolve`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
  },
};
