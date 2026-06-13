import { apiRequest } from "@/lib/api-client";

export interface Incident {
  id: string;
  alert_id: string | null;
  reporter_id: string;
  status: "reported" | "investigating" | "active" | "contained" | "resolved" | "false_alarm";
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  latitude: number;
  longitude: number;
  created_at: string;
  updated_at: string;
}

export interface IncidentDetails extends Incident {
  events: any[];
  updates: any[];
  assignments: any[];
}

export interface ResponseTeam {
  id: string;
  name: string;
  specialty: string;
  status: "active" | "inactive";
  created_at: string;
}

export interface ResponseTeamDetails extends ResponseTeam {
  members: any[];
}

export interface IncidentAssignment {
  id: string;
  incident_id: string;
  team_id: string;
  assigned_by: string;
  status: "assigned" | "accepted" | "rejected" | "completed";
  notes: string | null;
  assigned_at: string;
}

export interface IncidentHistoryResponse {
  incidents: Incident[];
  total_count: number;
}

export const incidentService = {
  async createIncident(body: { alert_id?: string; description: string; severity: string; latitude: number; longitude: number }): Promise<Incident> {
    return apiRequest<Incident>("/incidents", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listIncidents(params: {
    skip?: number;
    limit?: number;
    status?: string;
    severity?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<IncidentHistoryResponse> {
    return apiRequest<IncidentHistoryResponse>("/incidents", {
      params: params as any,
    });
  },

  async getIncidentById(id: string): Promise<IncidentDetails> {
    return apiRequest<IncidentDetails>(`/incidents/${id}`);
  },

  async transitionStatus(id: string, status: string, reason: string): Promise<Incident> {
    return apiRequest<Incident>(`/incidents/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, reason }),
    });
  },

  async escalateIncident(id: string, reason: string): Promise<Incident> {
    return apiRequest<Incident>(`/incidents/${id}/escalate`, {
      method: "PATCH",
      body: JSON.stringify({ reason }),
    });
  },

  async assignTeam(id: string, teamId: string): Promise<IncidentAssignment> {
    return apiRequest<IncidentAssignment>(`/incidents/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ team_id: teamId }),
    });
  },

  async acceptAssignment(assignmentId: string): Promise<IncidentAssignment> {
    return apiRequest<IncidentAssignment>(`/incidents/assignments/${assignmentId}/accept`, {
      method: "POST",
    });
  },

  async rejectAssignment(assignmentId: string, reason: string): Promise<IncidentAssignment> {
    return apiRequest<IncidentAssignment>(`/incidents/assignments/${assignmentId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  async addSitrepUpdate(id: string, message: string, mediaPath?: string): Promise<any> {
    return apiRequest<any>(`/incidents/${id}/updates`, {
      method: "POST",
      body: JSON.stringify({ message, media_path: mediaPath }),
    });
  },

  async listResponseTeams(): Promise<ResponseTeamDetails[]> {
    return apiRequest<ResponseTeamDetails[]>("/incidents/response-teams");
  },

  async createResponseTeam(name: string, specialty: string): Promise<ResponseTeam> {
    return apiRequest<ResponseTeam>("/incidents/response-teams", {
      method: "POST",
      body: JSON.stringify({ name, specialty }),
    });
  },

  async addTeamMember(teamId: string, userId: string, role: string): Promise<any> {
    return apiRequest<any>(`/incidents/response-teams/${teamId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, role }),
    });
  },

  async toggleMemberAvailability(memberId: string, isAvailable: boolean): Promise<any> {
    return apiRequest<any>(`/incidents/response-teams/members/${memberId}/availability`, {
      method: "PATCH",
      params: { is_available: isAvailable },
    });
  },
};
