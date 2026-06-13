import { apiRequest } from "@/lib/api-client";

export interface TrainingRun {
  id: string;
  dataset_id: string;
  status: "pending" | "running" | "completed" | "failed" | "stopped";
  model_name: string;
  hyperparameters: Record<string, any>;
  metrics_history: any[];
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TrainingCheckpoint {
  id: string;
  run_id: string;
  epoch: number;
  val_loss: number;
  val_accuracy: number;
  file_path: string;
  created_at: string;
}

export const trainingService = {
  async startTraining(body: {
    dataset_id: string;
    model_name: string;
    version_str: string;
    hyperparameters: Record<string, any>;
  }): Promise<TrainingRun> {
    return apiRequest<TrainingRun>("/training/start", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async stopTraining(runId: string): Promise<{ status: string; message: string }> {
    return apiRequest<{ status: string; message: string }>(`/training/stop/${runId}`, {
      method: "POST",
    });
  },

  async resumeTraining(runId: string, checkpointId?: string): Promise<TrainingRun> {
    return apiRequest<TrainingRun>("/training/resume", {
      method: "POST",
      params: { run_id: runId, ...(checkpointId && { checkpoint_id: checkpointId }) },
    });
  },

  async getTrainingStatus(runId: string): Promise<TrainingRun> {
    return apiRequest<TrainingRun>(`/training/status/${runId}`);
  },

  async listTrainingRuns(skip = 0, limit = 20): Promise<{ total: number; items: TrainingRun[] }> {
    return apiRequest<{ total: number; items: TrainingRun[] }>("/training/runs", {
      params: { skip, limit },
    });
  },

  async getTrainingMetrics(runId: string): Promise<any[]> {
    return apiRequest<any[]>(`/training/metrics/${runId}`);
  },

  async getTrainingCheckpoints(runId: string): Promise<TrainingCheckpoint[]> {
    return apiRequest<TrainingCheckpoint[]>(`/training/checkpoints/${runId}`);
  },
};
