"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { predictionService, SinglePredictionResult } from "@/services/predictions";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUiStore } from "@/store/ui-store";
import { BrainCircuit, Upload, HelpCircle, FileText, CheckCircle, ShieldAlert } from "lucide-react";

export default function PredictionsPage() {
  const queryClient = useQueryClient();
  const { addToast } = useUiStore();

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [result, setResult] = useState<SinglePredictionResult | null>(null);

  // Queries
  const { data: historyRes, isLoading: loadingHistory } = useQuery({
    queryKey: ["predictions-history"],
    queryFn: () => predictionService.listPredictions(0, 100),
  });

  // Mutations
  const predictMutation = useMutation({
    mutationFn: ({ file, lat, lon }: { file: File; lat?: number; lon?: number }) =>
      predictionService.predictSingle(file, lat, lon),
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["predictions-history"] });
      addToast({
        type: "success",
        title: "Inference Completed",
        message: `Prediction: ${data.detection.prediction_label.toUpperCase()} (${(data.detection.confidence * 100).toFixed(1)}% confidence)`,
      });
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Prediction Failed",
        message: err.message || "Failed to analyze image.",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    predictMutation.mutate({
      file: uploadFile,
      lat: latitude ? parseFloat(latitude) : undefined,
      lon: longitude ? parseFloat(longitude) : undefined,
    });
  };

  const clearForm = () => {
    setUploadFile(null);
    setLatitude("");
    setLongitude("");
    setResult(null);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center space-x-3">
          <BrainCircuit className="w-8 h-8 text-emerald-500" />
          <span>CNN INFERENCE STUDIO</span>
        </h1>
        <p className="text-sm text-neutral-400 mt-1">
          Perform real-time forest fire classifications using our trained CNN neural network weights.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Inference Form & Results */}
        <div className="lg:col-span-2 space-y-6">
          {!result ? (
            // Upload Form
            <Card className="border border-white/5">
              <CardHeader>
                <h3 className="font-bold text-neutral-200">INFERENCE SAMPLE PIPELINE</h3>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Image input */}
                  <div className="border border-dashed border-white/10 rounded-xl p-8 text-center bg-neutral-900/20">
                    <Upload className="w-10 h-10 text-neutral-600 mx-auto mb-3" />
                    <h5 className="text-sm font-semibold text-neutral-300">Drag & Drop Image Here</h5>
                    <p className="text-xs text-neutral-500 mt-1">Accepts PNG, JPG, or JPEG (Max 10MB)</p>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="mt-6 text-xs w-full text-center file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-600/10 file:text-emerald-400 file:cursor-pointer"
                    />
                  </div>

                  {/* Geolocation Fields */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      label="Latitude Coordinate"
                      placeholder="e.g. 37.7749"
                      value={latitude}
                      onChange={(e) => setLatitude(e.target.value)}
                    />
                    <Input
                      label="Longitude Coordinate"
                      placeholder="e.g. -122.4194"
                      value={longitude}
                      onChange={(e) => setLongitude(e.target.value)}
                    />
                  </div>

                  <Button
                    variant="primary"
                    type="submit"
                    loading={predictMutation.isPending}
                    className="w-full py-3"
                    disabled={!uploadFile}
                  >
                    Execute Prediction Analysis
                  </Button>
                </form>
              </CardContent>
            </Card>
          ) : (
            // Results Panel
            <Card className="border border-white/5 bg-gradient-to-b from-neutral-900/60 to-neutral-950/60">
              <CardHeader className="flex flex-row items-center justify-between border-b border-white/5">
                <h3 className="font-bold text-neutral-200">INFERENCE SUITE CLASSIFICATION REPORT</h3>
                <Button variant="outline" size="sm" onClick={clearForm}>
                  Analyze Another Image
                </Button>
              </CardHeader>
              <CardContent className="space-y-6 pt-6">
                {/* Result Indicator Badge */}
                <div className="flex flex-col md:flex-row items-center justify-between bg-neutral-900/40 p-6 rounded-xl border border-white/5 gap-4">
                  <div className="flex items-center space-x-4">
                    <div
                      className={`w-14 h-14 rounded-full flex items-center justify-center font-bold text-white text-base ${
                        result.detection.prediction_label === "fire"
                          ? "bg-rose-500/10 text-rose-500 border border-rose-500/20 animate-pulse"
                          : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                      }`}
                    >
                      {result.detection.prediction_label === "fire" ? (
                        <ShieldAlert className="w-7 h-7" />
                      ) : (
                        <CheckCircle className="w-7 h-7" />
                      )}
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Prediction Output
                      </h4>
                      <h2 className="text-xl font-black text-white mt-0.5">
                        {result.detection.prediction_label.toUpperCase()} DETECTED
                      </h2>
                    </div>
                  </div>
                  <div className="text-center md:text-right">
                    <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                      Model Confidence
                    </h4>
                    <span className="text-2xl font-black text-white block mt-0.5">
                      {(result.detection.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Risk and SLA telemetry */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-neutral-950/40 border border-white/5 rounded-xl p-4">
                    <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                      Incident Threat Level
                    </span>
                    <span
                      className={`text-sm font-bold uppercase mt-1 inline-block capitalize ${
                        result.risk_level === "critical" || result.risk_level === "high"
                          ? "text-rose-400"
                          : result.risk_level === "medium"
                          ? "text-amber-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {result.risk_level} Threat
                    </span>
                  </div>
                  <div className="bg-neutral-950/40 border border-white/5 rounded-xl p-4">
                    <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                      Inference Processing Speed
                    </span>
                    <span className="text-sm font-bold text-neutral-200 mt-1 inline-block">
                      {result.processing_duration_seconds.toFixed(3)} Seconds (SLA Compliant)
                    </span>
                  </div>
                </div>

                {/* Probability Distribution Meters */}
                <div className="space-y-4">
                  <h4 className="text-xs font-bold uppercase text-neutral-400">Probability Vector</h4>
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold text-neutral-400">
                        <span>FIRE MODEL PROBABILITY</span>
                        <span>{(result.probabilities.fire * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-3 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                        <div
                          className="h-full bg-rose-500 rounded-full"
                          style={{ width: `${result.probabilities.fire * 100}%` }}
                        />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold text-neutral-400">
                        <span>NON-FIRE MODEL PROBABILITY</span>
                        <span>{(result.probabilities["non-fire"] * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-3 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${result.probabilities["non-fire"] * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: History Feed */}
        <div className="space-y-6">
          <Card className="border border-white/5 h-[620px] flex flex-col justify-between">
            <CardHeader className="border-b border-white/5 flex flex-row items-center justify-between">
              <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                <FileText className="w-4 h-4 text-emerald-400" />
                <span>INFERENCE HISTORY LOG</span>
              </h3>
            </CardHeader>
            <CardContent className="p-0 overflow-y-auto flex-1">
              {loadingHistory ? (
                <div className="flex items-center justify-center h-full">
                  <div className="w-6 h-6 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
                </div>
              ) : historyRes?.items && historyRes.items.length > 0 ? (
                <div className="divide-y divide-white/5">
                  {historyRes.items.map((item) => (
                    <div key={item.id} className="p-4 hover:bg-white/5 transition flex items-center justify-between">
                      <div>
                        <span className="text-xs font-bold text-neutral-200">
                          {item.id.substring(0, 8).toUpperCase()}
                        </span>
                        <div className="flex items-center space-x-1.5 mt-0.5">
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                              item.prediction_label === "fire"
                                ? "bg-rose-500/10 text-rose-400"
                                : "bg-emerald-500/10 text-emerald-400"
                            }`}
                          >
                            {item.prediction_label}
                          </span>
                          <span className="text-[10px] text-neutral-500">
                            {(item.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <span className="text-[10px] text-neutral-500">
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-12 text-sm text-neutral-600 font-medium">
                  No historical pipeline runs logged.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
