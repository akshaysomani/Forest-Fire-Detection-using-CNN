"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth-store";
import { useUiStore } from "@/store/ui-store";
import { authService } from "@/services/auth";
import { alertService, AlertPreferenceUpdate } from "@/services/alerts";
import { predictionService, SinglePredictionResult } from "@/services/predictions";
import { dashboardService } from "@/services/dashboard";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Flame,
  ShieldAlert,
  Brain,
  Layers,
  Cpu,
  Database,
  History,
  User as UserIcon,
  Settings as SettingsIcon,
  Upload,
  Globe,
  CheckCircle,
  Terminal,
  RefreshCw,
  LogOut,
  Bell,
  Clock,
  MapPin,
  FileImage,
  AlertCircle
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
  const queryClient = useQueryClient();
  const { user, setUser } = useAuthStore();
  const { addToast } = useUiStore();

  const isSuperAdmin = user?.roles?.some((r) => r.name.toLowerCase() === "super admin");
  const [dashboardView, setDashboardView] = useState<"admin" | "user">("admin");

  // Keep state for selected tab in User view
  const [userTab, setUserTab] = useState<"profile" | "predictions" | "settings">("predictions");

  // Set default view on load
  useEffect(() => {
    if (user) {
      if (isSuperAdmin) {
        setDashboardView("admin");
      } else {
        setDashboardView("user");
      }
    }
  }, [user, isSuperAdmin]);

  // Admin Dashboard Queries
  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: dashboardService.getOverview,
    enabled: dashboardView === "admin",
  });

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ["dashboard-statistics"],
    queryFn: dashboardService.getStatistics,
    enabled: dashboardView === "admin",
  });

  const { data: systemSummary } = useQuery({
    queryKey: ["system-summary"],
    queryFn: dashboardService.getSystemSummary,
    refetchInterval: 10000,
    enabled: dashboardView === "admin",
  });

  const loading = dashboardView === "admin" && (loadingOverview || loadingStats);

  // User Dashboard Profile States & Mutations
  const [usernameInput, setUsernameInput] = useState(user?.username || "");
  const [emailInput, setEmailInput] = useState(user?.email || "");
  const [profileImgInput, setProfileImgInput] = useState(user?.profile_image_url || "");

  // Track profile update changes when user object shifts
  useEffect(() => {
    if (user) {
      setUsernameInput(user.username);
      setEmailInput(user.email);
      setProfileImgInput(user.profile_image_url || "");
    }
  }, [user]);

  const updateProfileMutation = useMutation({
    mutationFn: (data: { username: string; email: string; profile_image_url?: string }) =>
      authService.updateProfile(data),
    onSuccess: (updatedUser) => {
      setUser(updatedUser);
      addToast({
        type: "success",
        title: "Profile Refreshed",
        message: "Your agent details have been successfully modified.",
      });
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Update Rejected",
        message: err.message || "Failed to update profile.",
      });
    },
  });

  const handleUpdateProfile = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfileMutation.mutate({
      username: usernameInput,
      email: emailInput,
      profile_image_url: profileImgInput || undefined,
    });
  };

  // Sessions Query & Mutation
  const { data: sessions, refetch: refetchSessions } = useQuery({
    queryKey: ["user-sessions"],
    queryFn: authService.getSessions,
    enabled: dashboardView === "user" && userTab === "profile",
  });

  const revokeSessionMutation = useMutation({
    mutationFn: authService.revokeSession,
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Session Terminated",
        message: "Remote device access has been successfully revoked.",
      });
      refetchSessions();
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Revocation Failed",
        message: err.message || "Failed to terminate session.",
      });
    },
  });

  // User Dashboard Predictions States & Drag-Drop
  const [dragOver, setDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [latCoord, setLatCoord] = useState("");
  const [lonCoord, setLonCoord] = useState("");
  const [predResult, setPredResult] = useState<SinglePredictionResult | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const { data: personalHistory, isLoading: loadingPersonalHistory } = useQuery({
    queryKey: ["user-personal-history"],
    queryFn: () => predictionService.listPredictions(0, 10),
    enabled: dashboardView === "user" && userTab === "predictions",
  });

  const userPredictMutation = useMutation({
    mutationFn: ({ file, lat, lon }: { file: File; lat?: number; lon?: number }) =>
      predictionService.predictSingle(file, lat, lon),
    onMutate: () => {
      setUploadProgress(20);
      const timer = setInterval(() => {
        setUploadProgress((p) => (p < 90 ? p + 15 : p));
      }, 150);
      return { timer };
    },
    onSuccess: (data, variables, context) => {
      clearInterval(context?.timer);
      setUploadProgress(100);
      setPredResult(data);
      queryClient.invalidateQueries({ queryKey: ["user-personal-history"] });
      addToast({
        type: "success",
        title: "Analysis Successful",
        message: `Inference Label: ${data.detection.prediction_label.toUpperCase()} (${(data.detection.confidence * 100).toFixed(1)}%)`,
      });
    },
    onError: (err: any, variables, context) => {
      clearInterval(context?.timer);
      setUploadProgress(0);
      addToast({
        type: "error",
        title: "Analysis Failed",
        message: err.message || "Prediction request could not be processed.",
      });
    },
  });

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    processSelectedFile(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    processSelectedFile(file);
  };

  const processSelectedFile = (file?: File) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      addToast({ type: "error", title: "Invalid File Type", message: "Only PNG, JPG, or JPEG images are accepted." });
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      addToast({ type: "error", title: "File Too Large", message: "Maximum file size limit is 10MB." });
      return;
    }
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setPredResult(null);
    setUploadProgress(0);
  };

  const triggerLocalPrediction = () => {
    if (!selectedFile) return;
    userPredictMutation.mutate({
      file: selectedFile,
      lat: latCoord ? parseFloat(latCoord) : undefined,
      lon: lonCoord ? parseFloat(lonCoord) : undefined,
    });
  };

  const clearInferenceZone = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setPredResult(null);
    setLatCoord("");
    setLonCoord("");
    setUploadProgress(0);
  };

  // User Dashboard Alert Settings Query & Updates
  const { data: preferences, refetch: refetchPreferences } = useQuery({
    queryKey: ["user-alert-preferences"],
    queryFn: alertService.getMyPreferences,
    enabled: dashboardView === "user" && userTab === "settings",
  });

  const [channelEmail, setChannelEmail] = useState(false);
  const [channelSms, setChannelSms] = useState(false);
  const [channelPush, setChannelPush] = useState(false);
  const [channelWebhook, setChannelWebhook] = useState(false);
  const [minSeverity, setMinSeverity] = useState<"Critical" | "High" | "Medium" | "Low" | "Informational">("Medium");
  const [quietHoursStart, setQuietHoursStart] = useState("");
  const [quietHoursEnd, setQuietHoursEnd] = useState("");

  // Sync state variables once preferences query finishes loaded
  useEffect(() => {
    if (preferences) {
      const emailPref = preferences.find((p) => p.channel === "email");
      const smsPref = preferences.find((p) => p.channel === "sms");
      const pushPref = preferences.find((p) => p.channel === "push");
      const webhookPref = preferences.find((p) => p.channel === "webhook");

      setChannelEmail(!!emailPref?.enabled);
      setChannelSms(!!smsPref?.enabled);
      setChannelPush(!!pushPref?.enabled);
      setChannelWebhook(!!webhookPref?.enabled);

      const mainPref = emailPref || smsPref || pushPref || webhookPref;
      if (mainPref) {
        setMinSeverity(mainPref.min_severity);
        setQuietHoursStart(mainPref.quiet_hours_start || "");
        setQuietHoursEnd(mainPref.quiet_hours_end || "");
      }
    }
  }, [preferences]);

  const updateAlertPreferencesMutation = useMutation({
    mutationFn: (body: AlertPreferenceUpdate[]) => alertService.updateMyPreferences(body),
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Preferences Saved",
        message: "Your alert dispatch filters have been successfully updated.",
      });
      refetchPreferences();
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Save Failed",
        message: err.message || "Failed to update alert preferences.",
      });
    },
  });

  const handleSavePreferences = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: AlertPreferenceUpdate[] = [
      { channel: "email", enabled: channelEmail, min_severity: minSeverity, quiet_hours_start: quietHoursStart || null, quiet_hours_end: quietHoursEnd || null },
      { channel: "sms", enabled: channelSms, min_severity: minSeverity, quiet_hours_start: quietHoursStart || null, quiet_hours_end: quietHoursEnd || null },
      { channel: "push", enabled: channelPush, min_severity: minSeverity, quiet_hours_start: quietHoursStart || null, quiet_hours_end: quietHoursEnd || null },
      { channel: "webhook", enabled: channelWebhook, min_severity: minSeverity, quiet_hours_start: quietHoursStart || null, quiet_hours_end: quietHoursEnd || null },
    ];
    updateAlertPreferencesMutation.mutate(payload);
  };

  const renderAdminDashboard = () => {
    const trendData = stats?.daily_detections ?? [];
    const confidenceData = stats?.confidence_distribution ?? [];

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

    if (loadingOverview || loadingStats) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
          <div className="w-8 h-8 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
          <p className="text-sm font-semibold text-neutral-400">Syncing telemetry data...</p>
        </div>
      );
    }

    return (
      <div className="space-y-8">
        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {cardItems.map((item, idx) => {
            const Icon = item.icon;
            return (
              <Card key={idx} className="border border-white/5 shadow-glass p-5 flex flex-col space-y-4 relative overflow-hidden">
                {/* Subtle glow behind icon */}
                <div className={`absolute top-0 right-0 w-24 h-24 rounded-full opacity-20 blur-2xl -translate-y-6 translate-x-6 ${item.bg}`} />
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${item.bg} shrink-0`}>
                  <Icon className={`w-5 h-5 ${item.color}`} />
                </div>
                <div>
                  <h3 className="text-3xl font-black text-white tabular-nums">{item.value}</h3>
                  <p className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mt-1 leading-tight">{item.title}</p>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Detection Trends */}
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

          {/* Model Confidence */}
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

        {/* Telemetry and Logs */}
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
                  <span className={systemSummary.cpu_usage_percent > 80 ? "text-rose-500" : "text-emerald-400"}>
                    {systemSummary.cpu_usage_percent}%
                  </span>
                </div>
                <div className="h-2.5 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      systemSummary.cpu_usage_percent > 80 ? "bg-rose-500" : "bg-emerald-500"
                    }`}
                    style={{ width: `${systemSummary.cpu_usage_percent}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold text-neutral-400">
                  <span>SYSTEM MEMORY LOAD</span>
                  <span className={systemSummary.memory_usage.percentage_used > 80 ? "text-rose-500" : "text-emerald-400"}>
                    {systemSummary.memory_usage.percentage_used}%
                  </span>
                </div>
                <div className="h-2.5 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      systemSummary.memory_usage.percentage_used > 80 ? "bg-rose-500" : "bg-emerald-500"
                    }`}
                    style={{ width: `${systemSummary.memory_usage.percentage_used}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold text-neutral-400">
                  <span>STORAGE DEPOT STATUS</span>
                  <span>{systemSummary.storage_usage.percentage_used}%</span>
                </div>
                <div className="h-2.5 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                    style={{ width: `${systemSummary.storage_usage.percentage_used}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Real-time Alerts log */}
        <Card className="border border-white/5">
          <CardHeader>
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
                        <td className="px-6 py-4 text-xs text-neutral-400 capitalize">{alert.status}</td>
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
  };

  const renderUserDashboard = () => {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Navigation Sidebar inside Dashboard */}
        <div className="lg:col-span-1 space-y-2">
          <Card className="border border-white/5 p-4 flex flex-col space-y-1 bg-neutral-900/10 backdrop-blur">
            <button
              onClick={() => setUserTab("predictions")}
              className={`flex items-center space-x-2.5 px-4 py-3 rounded-lg text-sm font-semibold transition ${
                userTab === "predictions"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-neutral-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <Brain className="w-4 h-4" />
              <span>Inference Sandbox</span>
            </button>
            <button
              onClick={() => setUserTab("profile")}
              className={`flex items-center space-x-2.5 px-4 py-3 rounded-lg text-sm font-semibold transition ${
                userTab === "profile"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-neutral-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <UserIcon className="w-4 h-4" />
              <span>Personal Profile</span>
            </button>
            <button
              onClick={() => setUserTab("settings")}
              className={`flex items-center space-x-2.5 px-4 py-3 rounded-lg text-sm font-semibold transition ${
                userTab === "settings"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-neutral-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <SettingsIcon className="w-4 h-4" />
              <span>Preferences</span>
            </button>
          </Card>

          {/* Profile Overview Widget — with prominent role badges */}
          <Card className="border border-white/5 p-5 flex flex-col items-center text-center space-y-3 bg-neutral-900/15">
            {/* Avatar */}
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-800 flex items-center justify-center font-black text-white text-2xl uppercase border border-emerald-500/30 shadow-lg">
                {user?.username?.[0] || "U"}
              </div>
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 border-2 border-neutral-950 flex items-center justify-center">
                <CheckCircle className="w-3 h-3 text-white" />
              </div>
            </div>

            {/* Name + email */}
            <div>
              <h3 className="font-bold text-white tracking-wide text-base">{user?.username}</h3>
              <p className="text-[11px] text-neutral-500 font-medium mt-0.5 truncate max-w-[180px]">{user?.email}</p>
            </div>

            {/* Role badges — prominently shown */}
            <div className="w-full pt-2 border-t border-white/5">
              <p className="text-[9px] uppercase tracking-widest text-neutral-600 font-bold mb-2">Assigned Role</p>
              <div className="flex flex-wrap gap-1.5 justify-center">
                {user?.roles && user.roles.length > 0 ? (
                  user.roles.map((r) => {
                    const roleColors: Record<string, string> = {
                      "Super Admin": "bg-purple-500/15 text-purple-300 border-purple-500/30",
                      "Forest Officer": "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
                      "Emergency Response Officer": "bg-rose-500/15 text-rose-300 border-rose-500/30",
                      "Research Analyst": "bg-amber-500/15 text-amber-300 border-amber-500/30",
                      "Viewer": "bg-sky-500/15 text-sky-300 border-sky-500/30",
                    };
                    const colorClass = roleColors[r.name] ?? "bg-neutral-800 text-neutral-300 border-white/10";
                    return (
                      <span
                        key={r.id}
                        className={`text-[10px] font-bold px-2.5 py-1 rounded-full border uppercase tracking-wide ${colorClass}`}
                      >
                        {r.name}
                      </span>
                    );
                  })
                ) : (
                  <span className="text-[10px] text-neutral-600 font-medium">No role assigned</span>
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Dynamic Panels */}
        <div className="lg:col-span-3 space-y-6">
          {userTab === "profile" && (
            <div className="space-y-6">
              {/* Profile details form */}
              <Card className="border border-white/5">
                <CardHeader>
                  <h3 className="font-bold text-neutral-200">EDIT PROFILE PARAMETERS</h3>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleUpdateProfile} className="space-y-4">
                    <Input
                      label="Agent Username"
                      placeholder="e.g. ranger_william"
                      value={usernameInput}
                      onChange={(e) => setUsernameInput(e.target.value)}
                    />
                    <Input
                      label="Email Clearance Address"
                      placeholder="e.g. william@forestry.gov"
                      type="email"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                    />
                    <Input
                      label="Avatar Image Path"
                      placeholder="e.g. https://domain.com/avatar.jpg"
                      value={profileImgInput}
                      onChange={(e) => setProfileImgInput(e.target.value)}
                    />
                    <Button
                      variant="primary"
                      type="submit"
                      loading={updateProfileMutation.isPending}
                      className="px-6 py-2.5"
                    >
                      Update Profile Details
                    </Button>
                  </form>
                </CardContent>
              </Card>

              {/* Active Sessions list */}
              <Card className="border border-white/5">
                <CardHeader>
                  <h3 className="font-bold text-neutral-200">AUTHENTICATED CONCURRENT SESSIONS</h3>
                </CardHeader>
                <CardContent className="p-0">
                  {sessions && sessions.length > 0 ? (
                    <div className="divide-y divide-white/5 text-sm">
                      {sessions.map((s) => (
                        <div key={s.id} className="p-4 flex items-center justify-between hover:bg-white/5 transition">
                          <div>
                            <span className="font-semibold text-neutral-200 font-mono text-xs">
                              {s.ip_address || "Unknown IP"}
                            </span>
                            <span className="block text-[10px] text-neutral-500 mt-1 max-w-[400px] truncate">
                              {s.user_agent || "Generic Browser API"}
                            </span>
                            <span className="text-[10px] text-neutral-400 block mt-0.5">
                              Activity: {new Date(s.last_activity_at).toLocaleString()}
                            </span>
                          </div>
                          {s.is_active ? (
                            <span className="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded font-bold uppercase">
                              Active
                            </span>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-rose-500 hover:text-rose-400 hover:bg-rose-500/5 text-xs py-1"
                              onClick={() => revokeSessionMutation.mutate(s.id)}
                            >
                              Revoke
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center py-8 text-neutral-600 text-xs font-semibold">
                      No other connected device terminals detected.
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {userTab === "predictions" && (
            <div className="space-y-6">
              {/* Interactive local prediction drop area */}
              <Card className="border border-white/5">
                <CardHeader>
                  <h3 className="font-bold text-neutral-200">PRE-CRITICAL INFERENCE RUNNER</h3>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Drag-Drop Container */}
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleFileDrop}
                    className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                      dragOver
                        ? "border-emerald-500 bg-emerald-500/5 shadow-inner"
                        : "border-white/10 bg-neutral-900/20 hover:border-emerald-500/30"
                    }`}
                  >
                    {!previewUrl ? (
                      <div className="space-y-2">
                        <Upload className="w-10 h-10 text-neutral-600 mx-auto" />
                        <h4 className="text-sm font-semibold text-neutral-300">Drag image here or click select</h4>
                        <p className="text-xs text-neutral-500">Supports PNG, JPG, or JPEG (Max 10MB)</p>
                        <input
                          type="file"
                          accept="image/*"
                          onChange={handleFileChange}
                          className="hidden"
                          id="dash-file-picker"
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          type="button"
                          onClick={() => document.getElementById("dash-file-picker")?.click()}
                          className="mt-2 text-xs"
                        >
                          Choose File
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="relative max-w-[240px] mx-auto rounded-lg overflow-hidden border border-white/15">
                          <img src={previewUrl} alt="Preview file" className="w-full h-auto object-cover max-h-[160px]" />
                        </div>
                        <div className="text-xs text-neutral-400 font-semibold truncate max-w-[320px] mx-auto">
                          File: {selectedFile?.name}
                        </div>
                        {uploadProgress > 0 && (
                          <div className="w-full max-w-[280px] mx-auto space-y-1">
                            <div className="flex justify-between text-[10px] text-neutral-500 font-bold uppercase">
                              <span>Analyzing Frame</span>
                              <span>{uploadProgress}%</span>
                            </div>
                            <div className="h-2 bg-neutral-900 rounded-full overflow-hidden border border-white/5">
                              <div className="h-full bg-emerald-500 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                            </div>
                          </div>
                        )}
                        <div className="flex justify-center space-x-2">
                          <Button
                            variant="primary"
                            size="sm"
                            type="button"
                            onClick={triggerLocalPrediction}
                            loading={userPredictMutation.isPending}
                            disabled={userPredictMutation.isPending}
                          >
                            Analyze Wildfire Risk
                          </Button>
                          <Button variant="outline" size="sm" type="button" onClick={clearInferenceZone}>
                            Remove
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Geolocation Fields */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      label="Optional Latitude"
                      placeholder="e.g. 37.7749"
                      value={latCoord}
                      onChange={(e) => setLatCoord(e.target.value)}
                    />
                    <Input
                      label="Optional Longitude"
                      placeholder="e.g. -122.4194"
                      value={lonCoord}
                      onChange={(e) => setLonCoord(e.target.value)}
                    />
                  </div>

                  {/* Results Panel */}
                  {predResult && (
                    <div className="p-5 rounded-xl border border-white/5 bg-neutral-900/20 space-y-4 animate-fadeIn">
                      <div className="flex items-center justify-between border-b border-white/5 pb-4">
                        <div className="flex items-center space-x-3.5">
                          <div
                            className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white text-xs ${
                              predResult.detection.prediction_label === "fire"
                                ? "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                                : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                            }`}
                          >
                            {predResult.detection.prediction_label === "fire" ? (
                              <ShieldAlert className="w-5 h-5" />
                            ) : (
                              <CheckCircle className="w-5 h-5" />
                            )}
                          </div>
                          <div>
                            <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                              CNN Classifier Output
                            </span>
                            <span className="font-extrabold text-white text-base">
                              {predResult.detection.prediction_label.toUpperCase()} IDENTIFIED
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                            Confidence Index
                          </span>
                          <span className="font-extrabold text-white text-base">
                            {(predResult.detection.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div className="bg-neutral-950/20 p-3 rounded-lg border border-white/5">
                          <span className="text-[9px] text-neutral-500 font-bold block uppercase">Risk Level</span>
                          <span className="font-bold text-white capitalize mt-0.5 inline-block">{predResult.risk_level} Threat</span>
                        </div>
                        <div className="bg-neutral-950/20 p-3 rounded-lg border border-white/5">
                          <span className="text-[9px] text-neutral-500 font-bold block uppercase">Latency Speed</span>
                          <span className="font-bold text-white mt-0.5 inline-block">
                            {predResult.processing_duration_seconds.toFixed(3)}s
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Personal Prediction history */}
              <Card className="border border-white/5">
                <CardHeader>
                  <h3 className="font-bold text-neutral-200">PERSONAL INFERENCE HISTORY</h3>
                </CardHeader>
                <CardContent className="p-0 max-h-[300px] overflow-y-auto">
                  {loadingPersonalHistory ? (
                    <div className="py-8 flex justify-center">
                      <div className="w-6 h-6 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
                    </div>
                  ) : personalHistory?.items && personalHistory.items.length > 0 ? (
                    <table className="w-full text-left border-collapse text-xs md:text-sm">
                      <thead>
                        <tr className="border-b border-white/5 text-neutral-500 font-semibold uppercase bg-neutral-950/40">
                          <th className="px-6 py-3">FILE</th>
                          <th className="px-6 py-3">LABEL</th>
                          <th className="px-6 py-3">CONFIDENCE</th>
                          <th className="px-6 py-3">TIMESTAMP</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 text-xs text-neutral-300">
                        {personalHistory.items.map((h) => (
                          <tr key={h.id} className="hover:bg-white/5 transition">
                            <td className="px-6 py-3 font-semibold font-mono text-neutral-200 truncate max-w-[120px]">
                              {h.image_id}
                            </td>
                            <td className="px-6 py-3">
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                                  h.prediction_label === "fire"
                                    ? "bg-rose-500/10 text-rose-400"
                                    : "bg-emerald-500/10 text-emerald-400"
                                }`}
                              >
                                {h.prediction_label}
                              </span>
                            </td>
                            <td className="px-6 py-3 font-bold">{(h.confidence * 100).toFixed(1)}%</td>
                            <td className="px-6 py-3 text-neutral-500">
                              {new Date(h.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="text-center py-10 text-neutral-600 text-xs font-semibold">
                      No CNN inferences recorded yet from this terminal.
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {userTab === "settings" && (
            <Card className="border border-white/5">
              <CardHeader>
                <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                  <Bell className="w-5 h-5 text-emerald-500" />
                  <span>EMERGENCY DISPATCH PREFERENCES</span>
                </h3>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSavePreferences} className="space-y-6">
                  {/* Channel selections */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-500">
                      NOTIFICATION DELIVERY CHANNELS
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        { label: "Email Alerts", val: channelEmail, set: setChannelEmail },
                        { label: "SMS Texts", val: channelSms, set: setChannelSms },
                        { label: "Push Feeds", val: channelPush, set: setChannelPush },
                        { label: "Webhook Hooks", val: channelWebhook, set: setChannelWebhook },
                      ].map((item, idx) => (
                        <label
                          key={idx}
                          className={`flex flex-col items-center justify-center p-4 rounded-xl border cursor-pointer select-none transition ${
                            item.val
                              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                              : "bg-neutral-900/20 border-white/5 text-neutral-400 hover:bg-white/5"
                          }`}
                        >
                          <input
                            type="checkbox"
                            className="hidden"
                            checked={item.val}
                            onChange={(e) => item.set(e.target.checked)}
                          />
                          <span className="text-xs font-semibold">{item.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Filter configurations */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Minimum severity */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold uppercase tracking-wider text-neutral-500 block">
                        MINIMUM ALERT SEVERITY THRESHOLD
                      </label>
                      <select
                        value={minSeverity}
                        onChange={(e: any) => setMinSeverity(e.target.value)}
                        className="w-full px-4 py-2.5 bg-neutral-900 border border-white/10 rounded-lg text-neutral-200 focus:outline-none focus:border-emerald-500"
                      >
                        {["Informational", "Low", "Medium", "High", "Critical"].map((sev) => (
                          <option key={sev} value={sev}>
                            {sev} Alerts
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Quiet Hours */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold uppercase tracking-wider text-neutral-500 block">
                        QUIET HOURS SILENCING
                      </label>
                      <div className="grid grid-cols-2 gap-3">
                        <Input
                          placeholder="e.g. 22:00"
                          value={quietHoursStart}
                          onChange={(e) => setQuietHoursStart(e.target.value)}
                        />
                        <Input
                          placeholder="e.g. 06:00"
                          value={quietHoursEnd}
                          onChange={(e) => setQuietHoursEnd(e.target.value)}
                        />
                      </div>
                      <p className="text-[10px] text-neutral-500 italic mt-1">
                        Formats are strictly 24h standard (e.g. HH:MM). Alerts are silenced in quiet intervals.
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="primary"
                    type="submit"
                    loading={updateAlertPreferencesMutation.isPending}
                    className="px-6 py-2.5 border border-emerald-500/20"
                  >
                    Save Preferences
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
        <p className="text-sm font-semibold text-neutral-400">Loading Dashboard Analytics...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header operations toggle for super admin */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            IGNISAI Dashboard
          </h1>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <p className="text-xs text-neutral-500 uppercase tracking-wider font-semibold">
              {dashboardView === "admin"
                ? "Operations Control Center"
                : "Command Center & Sandbox"}
            </p>
            {/* Role badge in header */}
            {user?.roles && user.roles.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {user.roles.map((r) => {
                  const roleColors: Record<string, string> = {
                    "Super Admin": "bg-purple-500/20 text-purple-300 border-purple-500/30",
                    "Forest Officer": "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
                    "Emergency Response Officer": "bg-rose-500/20 text-rose-300 border-rose-500/30",
                    "Research Analyst": "bg-amber-500/20 text-amber-300 border-amber-500/30",
                    "Viewer": "bg-sky-500/20 text-sky-300 border-sky-500/30",
                  };
                  const colorClass = roleColors[r.name] ?? "bg-neutral-800 text-neutral-300 border-white/10";
                  return (
                    <span key={r.id} className={`text-[9px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wide ${colorClass}`}>
                      {r.name}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {isSuperAdmin && (
          <div className="flex space-x-2 bg-neutral-900 p-1 border border-white/5 rounded-xl">
            <button
              onClick={() => setDashboardView("admin")}
              className={`px-4 py-2 text-xs uppercase font-bold tracking-wider rounded-lg transition ${
                dashboardView === "admin"
                  ? "bg-emerald-600 text-white"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              System Operations
            </button>
            <button
              onClick={() => setDashboardView("user")}
              className={`px-4 py-2 text-xs uppercase font-bold tracking-wider rounded-lg transition ${
                dashboardView === "user"
                  ? "bg-emerald-600 text-white"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              Agent View
            </button>
          </div>
        )}
      </div>

      {/* Conditional Dashboard Rendering */}
      {dashboardView === "admin" ? renderAdminDashboard() : renderUserDashboard()}
    </div>
  );
}
