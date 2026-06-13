"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/store/ui-store";
import { BarChart3, Download, RefreshCw, TrendingUp, Calendar, AlertCircle } from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export default function AnalyticsPage() {
  const queryClient = useQueryClient();
  const { addToast } = useUiStore();

  const [selectedMetric, setSelectedMetric] = useState("total_alerts");
  const [selectedDays, setSelectedDays] = useState(30);
  const [reportFormat, setReportFormat] = useState<"PDF" | "CSV" | "JSON">("PDF");
  const [generating, setGenerating] = useState(false);

  // Queries
  const { data: kpis, isLoading: loadingKpis } = useQuery({
    queryKey: ["analytics-kpis"],
    queryFn: () => analyticsService.getKPIs(true),
  });

  const { data: trends, isLoading: loadingTrends } = useQuery({
    queryKey: ["analytics-trends", selectedMetric, selectedDays],
    queryFn: () => analyticsService.getTrends(selectedMetric, selectedDays),
  });

  const { data: reportDefinitions } = useQuery({
    queryKey: ["report-definitions"],
    queryFn: () => analyticsService.listReportDefinitions(0, 100),
  });

  // Mutations
  const generateReportMutation = useMutation({
    mutationFn: analyticsService.generateReportAdhoc,
    onSuccess: (data) => {
      addToast({
        type: "success",
        title: "Report Queued",
        message: `Ad-hoc report execution ID: ${data.id.substring(0, 8)} started in format: ${data.format}.`,
      });
      // Start polling status or check back
      queryClient.invalidateQueries({ queryKey: ["report-definitions"] });
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Generation Failed",
        message: err.message || "Failed to trigger report compilation.",
      });
    },
  });

  const handleGenerateReport = (e: React.FormEvent) => {
    e.preventDefault();
    generateReportMutation.mutate({
      report_type: "incident_summary",
      format: reportFormat as any,
      parameters: { days: selectedDays },
    });
  };

  const downloadCompletedReport = async (executionId: string) => {
    try {
      addToast({ type: "info", title: "Download started", message: "Fetching report binary..." });
      const blob = await analyticsService.downloadReport(executionId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `ignisai-report-${executionId.substring(0, 8)}.${reportFormat.toLowerCase()}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      addToast({ type: "success", title: "Download Complete", message: "File exported successfully." });
    } catch (err: any) {
      addToast({ type: "error", title: "Download Failed", message: err.message || "Failed to download file." });
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center space-x-3">
            <BarChart3 className="w-8 h-8 text-emerald-500" />
            <span>BUSINESS INTELLIGENCE & ANALYTICS</span>
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Analyze historical containment speeds, false alarms ratios, and download audit sheets.
          </p>
        </div>
        <button
          onClick={() => queryClient.invalidateQueries()}
          className="p-2 border border-white/5 bg-neutral-900 rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white transition flex items-center space-x-1.5 self-start text-xs font-semibold uppercase tracking-wider"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border border-white/5">
          <CardContent className="p-6">
            <span className="text-[10px] text-neutral-500 uppercase font-bold block">
              False Alarm Rating (FAR)
            </span>
            <h3 className="text-2xl font-black text-white mt-1">
              {kpis ? `${(kpis.false_alarm_rate * 100).toFixed(1)}%` : "0.0%"}
            </h3>
            <p className="text-xs text-neutral-500 mt-1">Ratio of false alarm triggers in prediction sets.</p>
          </CardContent>
        </Card>

        <Card className="border border-white/5">
          <CardContent className="p-6">
            <span className="text-[10px] text-neutral-500 uppercase font-bold block">
              Wildfire Containment Speeds
            </span>
            <h3 className="text-2xl font-black text-white mt-1">
              {kpis?.average_containment_time_seconds
                ? `${(kpis.average_containment_time_seconds / 60).toFixed(0)} mins`
                : "N/A"}
            </h3>
            <p className="text-xs text-neutral-500 mt-1">Average time elapsed between reports and contained.</p>
          </CardContent>
        </Card>

        <Card className="border border-white/5">
          <CardContent className="p-6">
            <span className="text-[10px] text-neutral-500 uppercase font-bold block">
              SLA Alert Ack Speed
            </span>
            <h3 className="text-2xl font-black text-white mt-1">
              {kpis?.average_ack_time_seconds
                ? `${kpis.average_ack_time_seconds.toFixed(0)} secs`
                : "N/A"}
            </h3>
            <p className="text-xs text-neutral-500 mt-1">Dispatch acknowledgement latency target.</p>
          </CardContent>
        </Card>
      </div>

      {/* Trend charting panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 border border-white/5">
          <CardHeader className="flex flex-row items-center justify-between border-b border-white/5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-400 flex items-center space-x-1.5">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span>METRIC TIME-SERIES VISUALIZER</span>
            </h4>
            <div className="flex space-x-2 text-xs">
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="bg-neutral-900 border border-white/5 px-2.5 py-1 rounded text-neutral-300"
              >
                <option value="total_alerts">System Alerts volume</option>
                <option value="fire_detections">Wildfire Hotspots count</option>
                <option value="total_incidents">Emergency Incidents count</option>
              </select>
              <select
                value={selectedDays}
                onChange={(e) => setSelectedDays(Number(e.target.value))}
                className="bg-neutral-900 border border-white/5 px-2.5 py-1 rounded text-neutral-300"
              >
                <option value={7}>Last 7 Days</option>
                <option value={30}>Last 30 Days</option>
                <option value={90}>Last 90 Days</option>
              </select>
            </div>
          </CardHeader>
          <CardContent className="h-[320px] w-full pt-6 pr-6">
            {trends?.trends && trends.trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends.trends}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                  <XAxis dataKey="date_bucket" stroke="#555" fontSize={10} />
                  <YAxis stroke="#555" fontSize={10} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#121212", border: "1px solid #333", borderRadius: 8 }}
                    labelStyle={{ color: "#888" }}
                  />
                  <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#colorValue)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm font-semibold text-neutral-600">
                No trend metrics logged for the selected coordinates search window.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Generate Report Form */}
        <Card className="border border-white/5 flex flex-col justify-between">
          <CardHeader>
            <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-400 flex items-center space-x-1.5">
              <Calendar className="w-4 h-4 text-emerald-400" />
              <span>EXPORT REPORT SUMMARY</span>
            </h4>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-xs text-neutral-400 leading-relaxed">
              Queue an ad-hoc compiled PDF analysis of wildfire events, containing charts, SLA speeds, and incident resolution times.
            </p>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Format</label>
                <div className="grid grid-cols-3 gap-2">
                  {["PDF", "CSV", "JSON"].map((fmt) => (
                    <button
                      key={fmt}
                      type="button"
                      onClick={() => setReportFormat(fmt as any)}
                      className={`px-3 py-2 rounded-lg text-xs font-semibold border transition ${
                        reportFormat === fmt
                          ? "bg-emerald-600/10 text-emerald-400 border-emerald-500/40"
                          : "bg-neutral-900 border-white/5 text-neutral-400 hover:text-white"
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>
              <Button
                variant="primary"
                onClick={handleGenerateReport}
                loading={generateReportMutation.isPending}
                className="w-full py-3"
              >
                Compile Report
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Report definitions or executions list */}
      <Card className="border border-white/5">
        <CardHeader>
          <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-400 flex items-center space-x-1.5">
            <Download className="w-4 h-4 text-emerald-400" />
            <span>COMPLETED EXECUTIONS REGISTRY</span>
          </h4>
        </CardHeader>
        <CardContent className="p-0">
          {reportDefinitions && reportDefinitions.length > 0 ? (
            <div className="divide-y divide-white/5 text-xs md:text-sm">
              {reportDefinitions.map((report) => (
                <div key={report.id} className="px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <span className="font-bold text-neutral-200 block">{report.name}</span>
                    <span className="block text-xs text-neutral-500 mt-0.5">
                      Type: {report.report_type} | Frequency: {report.frequency}
                    </span>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => downloadCompletedReport(report.id)}>
                    Download File
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-10 text-sm text-neutral-600 font-medium">
              No historical report compile runs cataloged in database storage.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
