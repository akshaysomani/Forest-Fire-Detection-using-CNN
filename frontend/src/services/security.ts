import { apiRequest } from "@/lib/api-client";

export interface SecurityEvent {
  id: string;
  event_type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  ip_address: string | null;
  user_id: string | null;
  created_at: string;
}

export interface CompliancePolicy {
  id: string;
  name: string;
  framework: "GDPR" | "SOC2";
  status: "passed" | "failed" | "unchecked";
  last_checked_at: string | null;
  score: number;
}

export interface AccessReviewCampaign {
  id: string;
  name: string;
  target_role: string;
  status: "active" | "completed";
  created_by: string;
  created_at: string;
  completed_at: string | null;
}

export interface ThreatReport {
  active_threats: number;
  blocked_ips_count: number;
  blocked_ips_list: string[];
  sql_injection_attempts: number;
  xss_attempts: number;
  brute_force_attempts: number;
  suspicious_activities_count: number;
}

export interface GovernanceDashboard {
  risk_score: number;
  overall_compliance_percentage: number;
  access_reviews_completion_percentage: number;
  pending_approvals_count: number;
}

export const securityService = {
  async getSecurityAudit(): Promise<any> {
    return apiRequest<any>("/security/audit");
  },

  async getSecurityEvents(params: { severity?: string; event_type?: string; skip?: number; limit?: number }): Promise<SecurityEvent[]> {
    return apiRequest<SecurityEvent[]>("/security/events", { params: params as any });
  },

  async getComplianceStatus(): Promise<CompliancePolicy[]> {
    return apiRequest<CompliancePolicy[]>("/security/compliance");
  },

  async runComplianceCheck(policyName: string): Promise<CompliancePolicy> {
    return apiRequest<CompliancePolicy>(`/security/compliance/run/${policyName}`, {
      method: "POST",
    });
  },

  async getAccessReviews(): Promise<AccessReviewCampaign[]> {
    return apiRequest<AccessReviewCampaign[]>("/security/access-reviews");
  },

  async createAccessReviewCampaign(body: { name: string; target_role: string }): Promise<AccessReviewCampaign> {
    return apiRequest<AccessReviewCampaign>("/security/access-reviews", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async submitAccessReviewDecision(
    campaignId: string,
    body: { user_id: string; role_id: string; decision: "certify" | "revoke"; justification: string }
  ): Promise<any> {
    return apiRequest<any>(`/security/access-reviews/${campaignId}/decisions`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async rotateSecrets(key: string): Promise<{ key: string; last_rotated_at: string; status: string }> {
    return apiRequest<{ key: string; last_rotated_at: string; status: string }>("/security/rotate-secrets", {
      method: "POST",
      body: JSON.stringify({ key }),
    });
  },

  async getThreats(): Promise<ThreatReport> {
    return apiRequest<ThreatReport>("/security/threats");
  },

  async getGovernanceSummary(): Promise<GovernanceDashboard> {
    return apiRequest<GovernanceDashboard>("/security/governance");
  },
};
