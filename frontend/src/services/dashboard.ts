import { apiRequest } from "@/lib/api-client";

export interface DashboardOverview {
  total_predictions: number;
  fire_detections: number;
  active_alerts: number;
  active_incidents: number;
  model_accuracy: number;
  recent_alerts: any[];
}

export interface DashboardStatistics {
  daily_detections: { date: string; count: number }[];
  model_performance: { threshold: number; precision: number; recall: number }[];
  confidence_distribution: { bin: string; count: number }[];
}

export interface RecentActivity {
  activities: {
    id: string;
    user_id: string | null;
    username: string | null;
    action: string;
    resource_type: string;
    resource_id: string | null;
    ip_address: string | null;
    details: string | null;
    created_at: string;
  }[];
  total_count: number;
}

export interface SystemSummary {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  db_latency: number;
  active_sessions: number;
  uptime_seconds: number;
  services_status: Record<string, "up" | "down">;
}

export interface UserSummary {
  total_users: number;
  verified_users: number;
  active_users: number;
  role_distribution: Record<string, number>;
}

export const dashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    return apiRequest<DashboardOverview>("/dashboard/overview");
  },

  async getStatistics(): Promise<DashboardStatistics> {
    return apiRequest<DashboardStatistics>("/dashboard/statistics");
  },

  async getRecentActivity(skip = 0, limit = 25): Promise<RecentActivity> {
    return apiRequest<RecentActivity>("/dashboard/recent-activity", {
      params: { skip, limit },
    });
  },

  async getSystemSummary(): Promise<SystemSummary> {
    return apiRequest<SystemSummary>("/dashboard/system-summary");
  },

  async getUserSummary(): Promise<UserSummary> {
    return apiRequest<UserSummary>("/dashboard/user-summary");
  },
};
