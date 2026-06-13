"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { dashboardService } from "@/services/dashboard";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import {
  Flame,
  ShieldAlert,
  Brain,
  Layers,
  Cpu,
  Database,
  History,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";

export default function DashboardPage() {
  // Queries
  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: dashboardService.getOverview,
  });

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ["dashboard-statistics"],
    queryFn: dashboardService.getStatistics,
  });

  const { data: systemSummary } = useQuery({
    queryKey: ["system-summary"],
    queryFn: dashboardService.getSystemSummary,
    refetchInterval: 10000, // Refetch every 10s for real-time monitoring
  });

  const loading = loadingOverview || loadingStats;

  const cardItems = [
    {
      title: "Total CNN Inferences",
      value: overview?.total_predictions ?? 0,
      icon: Brain,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    {
      title: "Wildfire Hotspots Detected",
      value: overview?.fire_detections ?? 0,
      icon: Flame,
      color: "text-rose-500 animate-pulse",
      bg: "bg-rose-500/10",
    },
    {
      title: "Active Safety Alerts",
      value: overview?.active_alerts ?? 0,
      icon: ShieldAlert,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
    },
    {
      title: "Active Emergencies",
      value: overview?.active_incidents ?? 0,
      icon: Layers,
      color: "text-sky-400",
      bg: "bg-sky-500/10",
    },
  ];

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
        <p className="text-sm font-semibold text-neutral-400">Loading Dashboard Analytics...</p>
      </div>
    );
  }

  // Format line chart data
  const trendData = stats?.daily_detections ?? [];
  const confidenceData = stats?.confidence_distribution ?? [];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">OPERATIONS DASHBOARD</h1>
        <p className="text-sm text-neutral-400 mt-1">Real-time Wildfire Surveillance Monitoring & ML Infrastructure Status.</p>
      </div>

      {/* Grid of Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cardItems.map((item, idx) => {
          const Icon = item.icon;
          return (
            <Card key={idx} className="border border-white/5 shadow-glass flex items-center p-6 space-x-5">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${item.bg}`}>
                <Icon className={`w-6 h-6 ${item.color}`} />
              </div>
              <div>
                <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">{item.title}</p>
                <h3 className="text-2xl font-black text-white mt-1">{item.value}</h3>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Detection Trends (2/3 width) */}
        <Card className="lg:col-span-2 border border-white/5">
          <CardHeader>
            <h4 className="text-sm font-bold uppercase tracking-wider text-neutral-400">DAILY DETECTION TRENDS</h4>
          </CardHeader>
          <CardContent className="h-[300px] w-full pr-6">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                  <XAxis dataKey="date" stroke="#666" fontSize={11} />
                  <YAxis stroke="#666" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#121212", border: "1px solid #333", borderRadius: 8 }}
                    labelStyle={{ color: "#888", fontWeight: "bold" }}
                  />
                  <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={3} dot={{ fill: "#10b981" }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm font-medium text-neutral-600">
                No recent detection trends recorded.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Model Confidence (1/3 width) */}
        <Card className="border border-white/5">
          <CardHeader>
            <h4 className="text-sm font-bold uppercase tracking-wider text-neutral-400">CONFIDENCE DISTRIBUTION</h4>
          </CardHeader>
          <CardContent className="h-[300px] w-full">
            {confidenceData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={confidenceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                  <XAxis dataKey="bin" stroke="#666" fontSize={11} />
                  <YAxis stroke="#666" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#121212", border: "1px solid #333", borderRadius: 8 }}
                    labelStyle={{ color: "#888", fontWeight: "bold" }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm font-medium text-neutral-600">
                No historical distribution metrics available.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* System Health Indicators */}
      {systemSummary && (
        <Card className="border border-white/5">
          <CardHeader>
            <h4 className="text-sm font-bold uppercase tracking-wider text-neutral-400 flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <span>INFRASTRUCTURE TELEMETRY & SYSTEM SCORES</span>
            </h4>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-neutral-400">
                <span>CPU CORES UTILIZATION</span>
                <span className={systemSummary.cpu_usage > 80 ? "text-rose-500" : "text-emerald-400"}>
                  {systemSummary.cpu_usage}%
                </span>
              </div>
              <div className="h-2.5 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    systemSummary.cpu_usage > 80 ? "bg-rose-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${systemSummary.cpu_usage}%` }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-neutral-400">
                <span>SYSTEM MEMORY LOAD</span>
                <span className={systemSummary.memory_usage > 80 ? "text-rose-500" : "text-emerald-400"}>
                  {systemSummary.memory_usage}%
                </span>
              </div>
              <div className="h-2.5 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    systemSummary.memory_usage > 80 ? "bg-rose-500" : "bg-emerald-500"
                  }`}
                  style={{ width: `${systemSummary.memory_usage}%` }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold text-neutral-400">
                <span>STORAGE DEPOT STATUS</span>
                <span>{systemSummary.disk_usage}%</span>
              </div>
              <div className="h-2.5 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                  style={{ width: `${systemSummary.disk_usage}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Alerts List */}
      <Card className="border border-white/5">
        <CardHeader className="flex flex-row items-center justify-between">
          <h4 className="text-sm font-bold uppercase tracking-wider text-neutral-400 flex items-center space-x-2">
            <History className="w-4 h-4 text-rose-500" />
            <span>REAL-TIME DETECTOR LOG FEED</span>
          </h4>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 text-xs font-semibold text-neutral-500 bg-neutral-950/40">
                  <th className="px-6 py-4">ALERT DETAILS</th>
                  <th className="px-6 py-4">SEVERITY</th>
                  <th className="px-6 py-4">STATUS</th>
                  <th className="px-6 py-4">DETECTION DATE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-sm">
                {overview?.recent_alerts && overview.recent_alerts.length > 0 ? (
                  overview.recent_alerts.map((alert: any) => (
                    <tr key={alert.id} className="hover:bg-white/5 transition">
                      <td className="px-6 py-4 font-medium text-neutral-200">{alert.message}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                            alert.severity === "Critical"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                              : alert.severity === "High"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          }`}
                        >
                          {alert.severity}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs text-neutral-400 capitalize">{alert.status}</span>
                      </td>
                      <td className="px-6 py-4 text-neutral-500 text-xs">
                        {new Date(alert.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-sm text-neutral-600 font-medium">
                      No active alerts logged within the detection window.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
