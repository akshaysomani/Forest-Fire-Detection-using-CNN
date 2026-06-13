import { apiRequest } from "@/lib/api-client";

export interface ImageRecord {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  width: number | null;
  height: number | null;
  latitude: number | null;
  longitude: number | null;
  captured_at: string | null;
  camera_make: string | null;
  camera_model: string | null;
  upload_source: string;
  status: string;
  created_at: string;
  retrieval_url?: string;
}

export interface PaginatedImages {
  total: number;
  skip: number;
  limit: number;
  items: ImageRecord[];
}

export const imageService = {
  async uploadImage(file: File, source: string): Promise<ImageRecord> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source", source);

    return apiRequest<ImageRecord>("/images/upload", {
      method: "POST",
      body: formData,
    });
  },

  async bulkUpload(files: File[], source: string): Promise<{ success: boolean; uploaded: string[]; errors: string[] }> {
    const formData = new FormData();
    formData.append("source", source);
    files.forEach((file) => formData.append("files", file));

    return apiRequest<{ success: boolean; uploaded: string[]; errors: string[] }>("/images/bulk-upload", {
      method: "POST",
      body: formData,
    });
  },

  async uploadZip(file: File, source: string): Promise<{ job_id: string; status: string }> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source", source);

    return apiRequest<{ job_id: string; status: string }>("/images/upload-zip", {
      method: "POST",
      body: formData,
    });
  },

  async listImages(params: {
    skip?: number;
    limit?: number;
    owner_id?: string;
    source?: string;
    status?: string;
    search?: string;
  }): Promise<PaginatedImages> {
    return apiRequest<PaginatedImages>("/images", {
      params: params as any,
    });
  },

  async searchImages(params: {
    skip?: number;
    limit?: number;
    min_width?: number;
    max_width?: number;
    min_height?: number;
    max_height?: number;
    min_lat?: number;
    max_lat?: number;
    min_lon?: number;
    max_lon?: number;
    start_date?: string;
    end_date?: string;
    camera?: string;
    source?: string;
    status?: string;
  }): Promise<PaginatedImages> {
    return apiRequest<PaginatedImages>("/images/search", {
      params: params as any,
    });
  },

  async getStatistics(): Promise<any> {
    return apiRequest<any>("/images/statistics");
  },

  async getImage(id: string): Promise<ImageRecord> {
    return apiRequest<ImageRecord>(`/images/${id}`);
  },

  async deleteImage(id: string): Promise<void> {
    return apiRequest<void>(`/images/${id}`, {
      method: "DELETE",
    });
  },
};
