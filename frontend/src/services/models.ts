import { apiRequest } from "@/lib/api-client";

export interface ModelFamily {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  owner_id: string;
}

export interface ModelVersion {
  id: string;
  model_id: string;
  version_str: string;
  training_run_id: string | null;
  checkpoint_id: string | null;
  stage: "development" | "staging" | "production" | "archived";
  description: string | null;
  release_notes: string | null;
  created_at: string;
  metrics: Record<string, number>;
  hyperparameters: Record<string, any>;
}

export interface ModelVersionDetail extends ModelVersion {
  artifacts: any[];
  deployments: any[];
  lifecycle_events: any[];
  approvals: any[];
}

export interface ModelDeployment {
  id: string;
  model_version_id: string;
  environment: "staging" | "production";
  status: "active" | "inactive";
  deployed_at: string;
  undeployed_at: string | null;
  deployed_by: string;
}

export interface PaginatedModels {
  total: number;
  skip: number;
  limit: number;
  items: ModelFamily[];
}

export const modelService = {
  async createModelFamily(body: { name: string; description?: string }): Promise<ModelFamily> {
    return apiRequest<ModelFamily>("/models", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listModels(skip = 0, limit = 20): Promise<PaginatedModels> {
    return apiRequest<PaginatedModels>("/models", {
      params: { skip, limit },
    });
  },

  async listVersions(params: {
    model_id?: string;
    version_a?: string;
    version_b?: string;
    skip?: number;
    limit?: number;
  }): Promise<any> {
    return apiRequest<any>("/models/versions", {
      params: params as any,
    });
  },

  async getVersionDetails(versionId: string): Promise<ModelVersionDetail> {
    return apiRequest<ModelVersionDetail>(`/models/versions/${versionId}`);
  },

  async createModelVersion(
    body: { model_id: string; training_run_id?: string; checkpoint_id?: string; description?: string; release_notes?: string },
    incrementType = "patch"
  ): Promise<ModelVersion> {
    return apiRequest<ModelVersion>("/models/versions", {
      method: "POST",
      params: { increment_type: incrementType },
      body: JSON.stringify(body),
    });
  },

  async requestApproval(body: { model_version_id: string; target_stage: string; request_notes: string }): Promise<any> {
    return apiRequest<any>("/models/approve/request", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async reviewApproval(body: { approval_id: string; status: "approved" | "rejected"; review_notes: string }): Promise<any> {
    return apiRequest<any>("/models/approve", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async deployModel(body: { model_version_id: string; environment: "staging" | "production"; metrics?: Record<string, number> }): Promise<any> {
    return apiRequest<any>("/models/deploy", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async rollbackDeployment(body: { model_id: string; environment: "staging" | "production" }): Promise<any> {
    return apiRequest<any>("/models/rollback", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async getLifecycleHistory(modelVersionId: string): Promise<any[]> {
    return apiRequest<any[]>("/models/history", {
      params: { model_version_id: modelVersionId },
    });
  },

  async getArtifacts(modelVersionId: string): Promise<any[]> {
    return apiRequest<any[]>("/models/artifacts", {
      params: { model_version_id: modelVersionId },
    });
  },

  async getObservabilityMetrics(): Promise<any> {
    return apiRequest<any>("/models/observability/metrics");
  },

  async getModelFamily(id: string): Promise<ModelFamily> {
    return apiRequest<ModelFamily>(`/models/${id}`);
  },
};
