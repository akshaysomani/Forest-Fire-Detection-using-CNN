import { apiRequest } from "@/lib/api-client";

export interface Detection {
  id: string;
  image_id: string;
  prediction_label: "fire" | "non-fire";
  confidence: number;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
}

export interface SinglePredictionResult {
  detection: Detection;
  risk_level: "low" | "medium" | "high" | "critical";
  probabilities: {
    "non-fire": number;
    fire: number;
  };
  processing_duration_seconds: number;
}

export interface PaginatedPredictions {
  total: number;
  skip: number;
  limit: number;
  items: Detection[];
}

export interface PredictionStatistics {
  total_predictions: number;
  fire_predictions_count: number;
  non_fire_predictions_count: number;
  average_confidence: number;
  average_latency_seconds: number;
}

export const predictionService = {
  async predictSingle(file: File, latitude?: number, longitude?: number): Promise<SinglePredictionResult> {
    const formData = new FormData();
    formData.append("file", file);
    if (latitude !== undefined) formData.append("latitude", String(latitude));
    if (longitude !== undefined) formData.append("longitude", String(longitude));

    return apiRequest<SinglePredictionResult>("/predictions", {
      method: "POST",
      body: formData,
    });
  },

  async predictBatch(files: File[]): Promise<{ success: boolean; message: string; job_id: string; total_images: number }> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    return apiRequest<{ success: boolean; message: string; job_id: string; total_images: number }>("/predictions/batch", {
      method: "POST",
      body: formData,
    });
  },

  async getBatchStatus(jobId: string): Promise<{ job_id: string; status: "pending" | "processing" | "completed" | "failed"; progress: number; results?: any[] }> {
    return apiRequest<{ job_id: string; status: "pending" | "processing" | "completed" | "failed"; progress: number; results?: any[] }>(`/predictions/batch/${jobId}`);
  },

  async listPredictions(skip = 0, limit = 100): Promise<PaginatedPredictions> {
    return apiRequest<PaginatedPredictions>("/predictions", {
      params: { skip, limit },
    });
  },

  async searchHistory(params: {
    skip?: number;
    limit?: number;
    label?: "fire" | "non-fire";
    min_confidence?: number;
    start_date?: string;
    end_date?: string;
  }): Promise<PaginatedPredictions> {
    return apiRequest<PaginatedPredictions>("/predictions/history", {
      params: params as any,
    });
  },

  async getStatistics(): Promise<PredictionStatistics> {
    return apiRequest<PredictionStatistics>("/predictions/statistics");
  },

  async getPredictionById(id: string): Promise<Detection> {
    return apiRequest<Detection>(`/predictions/${id}`);
  },
};
