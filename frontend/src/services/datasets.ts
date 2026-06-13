import { apiRequest } from "@/lib/api-client";

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  category_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  owner_id: string;
}

export interface DatasetCategory {
  id: string;
  name: string;
  description: string | null;
}

export interface DatasetLabel {
  id: string;
  name: string;
  description: string | null;
}

export interface DatasetFile {
  id: string;
  dataset_id: string;
  filename: string;
  filepath: string;
  file_size: number;
  mime_type: string;
  label_id: string | null;
  created_at: string;
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version_str: string;
  description: string | null;
  archive_path: string | null;
  created_at: string;
}

export interface PaginatedDatasets {
  total: number;
  skip: number;
  limit: number;
  items: Dataset[];
}

export interface PaginatedFiles {
  total: number;
  skip: number;
  limit: number;
  items: DatasetFile[];
}

export const datasetService = {
  async createDataset(body: { name: string; description?: string; category_id: string }): Promise<Dataset> {
    return apiRequest<Dataset>("/datasets", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listDatasets(params: {
    skip?: number;
    limit?: number;
    category_id?: string;
    status?: string;
    search?: string;
  }): Promise<PaginatedDatasets> {
    return apiRequest<PaginatedDatasets>("/datasets", {
      params: params as any,
    });
  },

  async getCategories(): Promise<DatasetCategory[]> {
    return apiRequest<DatasetCategory[]>("/datasets/categories");
  },

  async getLabels(): Promise<DatasetLabel[]> {
    return apiRequest<DatasetLabel[]>("/datasets/labels");
  },

  async getDataset(id: string): Promise<Dataset> {
    return apiRequest<Dataset>(`/datasets/${id}`);
  },

  async updateDataset(id: string, body: { name?: string; description?: string }): Promise<Dataset> {
    return apiRequest<Dataset>(`/datasets/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  async deleteDataset(id: string): Promise<void> {
    return apiRequest<void>(`/datasets/${id}`, {
      method: "DELETE",
    });
  },

  async uploadSingleFile(datasetId: string, file: File, labelId?: string): Promise<DatasetFile> {
    const formData = new FormData();
    formData.append("dataset_id", datasetId);
    formData.append("file", file);
    if (labelId) formData.append("label_id", labelId);

    return apiRequest<DatasetFile>("/datasets/upload", {
      method: "POST",
      body: formData,
    });
  },

  async uploadBulkFiles(datasetId: string, files: File[]): Promise<{ success: boolean; uploaded_count: number }> {
    const formData = new FormData();
    formData.append("dataset_id", datasetId);
    files.forEach((file) => formData.append("files", file));

    return apiRequest<{ success: boolean; uploaded_count: number }>("/datasets/bulk-upload", {
      method: "POST",
      body: formData,
    });
  },

  async uploadZipDataset(datasetId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append("dataset_id", datasetId);
    formData.append("file", file);

    return apiRequest<any>("/datasets/zip-upload", {
      method: "POST",
      body: formData,
    });
  },

  async getZipUploadStatus(historyId: string): Promise<any> {
    return apiRequest<any>(`/datasets/uploads/${historyId}`);
  },

  async getDatasetFiles(id: string, skip = 0, limit = 50): Promise<PaginatedFiles> {
    return apiRequest<PaginatedFiles>(`/datasets/${id}/files`, {
      params: { skip, limit },
    });
  },

  async getDatasetVersions(id: string): Promise<DatasetVersion[]> {
    return apiRequest<DatasetVersion[]>(`/datasets/${id}/versions`);
  },

  async createDatasetVersion(id: string, versionStr: string, description: string): Promise<DatasetVersion> {
    return apiRequest<DatasetVersion>(`/datasets/${id}/versions`, {
      method: "POST",
      body: JSON.stringify({ version_str: versionStr, description }),
    });
  },

  async rollbackDataset(id: string, versionStr: string): Promise<any> {
    return apiRequest<any>(`/datasets/${id}/rollback`, {
      method: "POST",
      body: JSON.stringify({ version_str: versionStr }),
    });
  },

  async assignLabels(id: string, fileIds: string[], labelId: string): Promise<{ status: string; updated_count: number }> {
    return apiRequest<{ status: string; updated_count: number }>(`/datasets/${id}/labels`, {
      method: "POST",
      body: JSON.stringify({ file_ids: fileIds, label_id: labelId }),
    });
  },
};
