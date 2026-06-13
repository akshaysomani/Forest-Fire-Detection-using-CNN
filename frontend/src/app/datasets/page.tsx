"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { datasetService, Dataset } from "@/services/datasets";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUiStore } from "@/store/ui-store";
import { Database, Plus, Upload, Folder, Calendar, History, ArrowLeft } from "lucide-react";

export default function DatasetsPage() {
  const queryClient = useQueryClient();
  const { addToast } = useUiStore();

  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // Create Dataset form state
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newCategory, setNewCategory] = useState("");

  // Upload state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // Queries
  const { data: datasetsRes, isLoading: loadingDatasets } = useQuery({
    queryKey: ["datasets-list"],
    queryFn: () => datasetService.listDatasets({ limit: 100 }),
  });

  const { data: categories } = useQuery({
    queryKey: ["dataset-categories"],
    queryFn: datasetService.getCategories,
  });

  const { data: activeDataset } = useQuery({
    queryKey: ["dataset-details", selectedDatasetId],
    queryFn: () => datasetService.getDataset(selectedDatasetId!),
    enabled: !!selectedDatasetId,
  });

  const { data: datasetFiles } = useQuery({
    queryKey: ["dataset-files", selectedDatasetId],
    queryFn: () => datasetService.getDatasetFiles(selectedDatasetId!),
    enabled: !!selectedDatasetId,
  });

  const { data: datasetVersions } = useQuery({
    queryKey: ["dataset-versions", selectedDatasetId],
    queryFn: () => datasetService.getDatasetVersions(selectedDatasetId!),
    enabled: !!selectedDatasetId,
  });

  // Mutations
  const createDatasetMutation = useMutation({
    mutationFn: datasetService.createDataset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["datasets-list"] });
      addToast({
        type: "success",
        title: "Dataset Created",
        message: "Your new dataset family is now ready for upload.",
      });
      setShowCreateModal(false);
      setNewName("");
      setNewDesc("");
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Creation Failed",
        message: err.message || "Failed to create dataset.",
      });
    },
  });

  const handleCreateDataset = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim() || !newCategory) {
      addToast({ type: "warning", title: "Missing Fields", message: "Name and Category are required." });
      return;
    }
    createDatasetMutation.mutate({
      name: newName,
      description: newDesc,
      category_id: newCategory,
    });
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !selectedDatasetId) return;

    setUploading(true);
    try {
      if (uploadFile.name.endsWith(".zip")) {
        await datasetService.uploadZipDataset(selectedDatasetId, uploadFile);
        addToast({
          type: "success",
          title: "ZIP Extraction Triggered",
          message: "The archive is being extracted in the background.",
        });
      } else {
        await datasetService.uploadSingleFile(selectedDatasetId, uploadFile);
        addToast({
          type: "success",
          title: "File Uploaded",
          message: `${uploadFile.name} added to the dataset successfully.`,
        });
      }
      setUploadFile(null);
      queryClient.invalidateQueries({ queryKey: ["dataset-files", selectedDatasetId] });
    } catch (err: any) {
      addToast({
        type: "error",
        title: "Upload Failed",
        message: err.message || "Failed to upload file.",
      });
    } finally {
      setUploading(false);
    }
  };

  if (loadingDatasets) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
        <p className="text-sm font-semibold text-neutral-400">Loading Dataset Catalogs...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center space-x-3">
            <Database className="w-8 h-8 text-emerald-500" />
            <span>DATASET REPOSITORY</span>
          </h1>
          <p className="text-sm text-neutral-400 mt-1">Manage image categories, import annotations, and track dataset versions.</p>
        </div>
        {!selectedDatasetId && (
          <Button variant="primary" onClick={() => setShowCreateModal(true)} className="flex items-center space-x-1.5 self-start">
            <Plus className="w-4 h-4" />
            <span>Create Dataset</span>
          </Button>
        )}
      </div>

      {/* Main Content Layout */}
      {!selectedDatasetId ? (
        // Grid of datasets
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {datasetsRes?.items && datasetsRes.items.length > 0 ? (
            datasetsRes.items.map((ds) => (
              <Card key={ds.id} className="border border-white/5 hover:border-emerald-500/20 transition duration-300">
                <CardHeader className="flex flex-row items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                      <Folder className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <h3 className="font-bold text-neutral-100">{ds.name}</h3>
                      <span className="text-[10px] uppercase font-bold text-emerald-500/80 tracking-wider">
                        Active Snapshot
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-xs text-neutral-400 leading-relaxed min-h-[40px]">
                    {ds.description || "No description provided."}
                  </p>
                  <div className="flex justify-between items-center text-xs text-neutral-500 border-t border-white/5 pt-4">
                    <span className="flex items-center space-x-1.5">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{new Date(ds.created_at).toLocaleDateString()}</span>
                    </span>
                    <Button variant="outline" size="sm" onClick={() => setSelectedDatasetId(ds.id)}>
                      Manage Files
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="col-span-full border border-dashed border-white/10 p-12 text-center">
              <p className="text-neutral-500 text-sm">No datasets generated. Create one to begin uploading training imagery.</p>
            </Card>
          )}
        </div>
      ) : (
        // Detail View of a specific dataset
        <div className="space-y-6">
          {/* Back button */}
          <button
            onClick={() => setSelectedDatasetId(null)}
            className="inline-flex items-center space-x-1.5 text-xs text-neutral-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Repositories</span>
          </button>

          {activeDataset && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Details & Upload */}
              <div className="space-y-6">
                <Card className="border border-white/5">
                  <CardHeader>
                    <h3 className="font-bold text-neutral-200">DATASET INFO</h3>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <span className="text-[10px] text-neutral-500 uppercase font-bold block">NAME</span>
                      <p className="text-sm font-semibold text-neutral-200 mt-0.5">{activeDataset.name}</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-neutral-500 uppercase font-bold block">DESCRIPTION</span>
                      <p className="text-xs text-neutral-400 mt-1 leading-relaxed">{activeDataset.description || "N/A"}</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-neutral-500 uppercase font-bold block">STATUS</span>
                      <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded-full inline-block mt-1 uppercase font-bold">
                        {activeDataset.status}
                      </span>
                    </div>
                  </CardContent>
                </Card>

                {/* File Uploader */}
                <Card className="border border-white/5">
                  <CardHeader>
                    <h3 className="font-bold text-neutral-200">UPLOAD SAMPLES</h3>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleFileUpload} className="space-y-4">
                      <div className="border border-dashed border-white/10 rounded-lg p-6 text-center bg-neutral-900/20">
                        <Upload className="w-8 h-8 text-neutral-600 mx-auto mb-2" />
                        <span className="text-xs text-neutral-400 block font-medium">
                          Select Image or zip file
                        </span>
                        <input
                          type="file"
                          accept=".png,.jpg,.jpeg,.zip"
                          onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                          className="mt-4 text-xs w-full text-center file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-emerald-600/15 file:text-emerald-400 file:cursor-pointer"
                        />
                      </div>
                      <Button variant="primary" type="submit" loading={uploading} className="w-full" disabled={!uploadFile}>
                        Upload to Dataset
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              </div>

              {/* Right Column: Files & Versions */}
              <div className="lg:col-span-2 space-y-6">
                <Card className="border border-white/5">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                      <Folder className="w-4 h-4 text-emerald-400" />
                      <span>DATASET SAMPLES ({datasetFiles?.total || 0})</span>
                    </h3>
                  </CardHeader>
                  <CardContent className="p-0 max-h-[360px] overflow-y-auto">
                    {datasetFiles?.items && datasetFiles.items.length > 0 ? (
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="border-b border-white/5 text-neutral-500 font-semibold uppercase tracking-wider bg-neutral-950/40">
                            <th className="px-6 py-3">FILE</th>
                            <th className="px-6 py-3">SIZE</th>
                            <th className="px-6 py-3">UPLOAD DATE</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {datasetFiles.items.map((file) => (
                            <tr key={file.id} className="hover:bg-white/5 transition">
                              <td className="px-6 py-3 text-neutral-200 font-semibold truncate max-w-[180px]">{file.filename}</td>
                              <td className="px-6 py-3 text-neutral-400">{(file.file_size / 1024).toFixed(1)} KB</td>
                              <td className="px-6 py-3 text-neutral-500">{new Date(file.created_at).toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p className="text-center py-12 text-sm text-neutral-600 font-medium">
                        No files currently uploaded to this dataset directory.
                      </p>
                    )}
                  </CardContent>
                </Card>

                {/* Historical Versions */}
                <Card className="border border-white/5">
                  <CardHeader>
                    <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                      <History className="w-4 h-4 text-emerald-400" />
                      <span>VERSION HISTORY SNAPSHOTS</span>
                    </h3>
                  </CardHeader>
                  <CardContent className="p-0">
                    {datasetVersions && datasetVersions.length > 0 ? (
                      <div className="divide-y divide-white/5">
                        {datasetVersions.map((ver) => (
                          <div key={ver.id} className="flex justify-between items-center px-6 py-4">
                            <div>
                              <span className="font-bold text-sm text-neutral-200 block">
                                v{ver.version_str}
                              </span>
                              <p className="text-xs text-neutral-400 mt-0.5">{ver.description}</p>
                            </div>
                            <span className="text-xs text-neutral-500 font-medium">
                              {new Date(ver.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center py-10 text-sm text-neutral-600 font-medium">
                        No historical versions snapshots recorded.
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create Dataset Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-[480px] border border-white/10 shadow-glass">
            <CardHeader>
              <h3 className="text-lg font-extrabold text-white">Create Dataset Repository</h3>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateDataset} className="space-y-4">
                <Input
                  label="Dataset Name"
                  placeholder="e.g. Pine Ridge CCTV Scans"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
                <Input
                  label="Description"
                  placeholder="Summarize the imagery and source..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
                
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">
                    Category Type
                  </label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full px-4 py-2.5 bg-neutral-900 border border-white/10 rounded-lg text-neutral-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="">Select Category...</option>
                    {categories?.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex justify-end space-x-3 pt-4 border-t border-white/5 mt-6">
                  <Button variant="outline" type="button" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" type="submit">
                    Create Catalog
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
