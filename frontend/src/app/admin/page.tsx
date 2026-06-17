"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { securityService } from "@/services/security";
import { modelService } from "@/services/models";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/store/ui-store";
import { ShieldCheck, ShieldAlert, Cpu, Award, RefreshCw, AlertTriangle, Key } from "lucide-react";

export default function AdminPage() {
  const queryClient = useQueryClient();
  const { addToast } = useUiStore();

  const [activeTab, setActiveTab] = useState<"governance" | "registry" | "threats">("governance");

  // Queries
  const { data: gov, isLoading: loadingGov } = useQuery({
    queryKey: ["gov-dashboard"],
    queryFn: securityService.getGovernanceSummary,
  });

  const { data: threats } = useQuery({
    queryKey: ["threats-status"],
    queryFn: securityService.getThreats,
  });

  const { data: modelsRes } = useQuery({
    queryKey: ["models-list"],
    queryFn: () => modelService.listModels(0, 50),
  });

  // Mutations
  const rotateSecretsMutation = useMutation({
    mutationFn: securityService.rotateSecrets,
    onSuccess: (data) => {
      addToast({
        type: "success",
        title: "Credential Rotated",
        message: `Successfully updated token encryption keys for key: ${data.key}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["gov-dashboard"] });
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Rotation Failed",
        message: err.message || "Failed to rotate secret.",
      });
    },
  });

  const runAuditMutation = useMutation({
    mutationFn: securityService.getSecurityAudit,
    onSuccess: (data) => {
      addToast({
        type: "success",
        title: "Audit Scan Completed",
        message: `Completed identity audit. Risk score: ${data.overall_risk || "Low"}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["gov-dashboard"] });
    },
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center space-x-3">
            <ShieldCheck className="w-8 h-8 text-emerald-500" />
            <span>IDENTITY SECURITY & GOVERNANCE PANEL</span>
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Rotate cryptographic credentials, audit user permission drift, and monitor MLOps registries.
          </p>
        </div>
        <div className="flex space-x-2 self-start">
          <Button
            variant="outline"
            size="sm"
            onClick={() => runAuditMutation.mutate()}
            loading={runAuditMutation.isPending}
          >
            Audit Permissions
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => rotateSecretsMutation.mutate("JWT_SECRET_KEY")}
            loading={rotateSecretsMutation.isPending}
          >
            Rotate JWT Secret
          </Button>
        </div>
      </div>

      {/* Tabs Menu */}
      <div className="flex space-x-2 border-b border-white/5 pb-0.5">
        {["governance", "registry", "threats"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as any)}
            className={`px-4 py-2 text-sm font-semibold tracking-wider uppercase transition border-b-2 ${
              activeTab === tab
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {tab} Control
          </button>
        ))}
      </div>

      {/* Dynamic Content */}
      {activeTab === "governance" && (
        <div className="space-y-6">
          {/* KPI summaries */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="border border-white/5">
              <CardContent className="p-6">
                <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                  SYSTEM RISK SCORE
                </span>
                <h3 className="text-2xl font-black text-white mt-1">
                  {gov ? `${gov.risk_score}/10` : "0/10"}
                </h3>
                <p className="text-xs text-neutral-500 mt-1">Weighted system vulnerabilities score.</p>
              </CardContent>
            </Card>

            <Card className="border border-white/5">
              <CardContent className="p-6">
                <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                  SOC2/GDPR COMPLIANCE
                </span>
                <h3 className="text-2xl font-black text-white mt-1">
                  {gov ? `${gov.overall_compliance_percentage}%` : "0%"}
                </h3>
                <p className="text-xs text-neutral-500 mt-1">Overall verification policy matches.</p>
              </CardContent>
            </Card>

            <Card className="border border-white/5">
              <CardContent className="p-6">
                <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                  ACCESS REVIEWS COMPLETED
                </span>
                <h3 className="text-2xl font-black text-white mt-1">
                  {gov ? `${gov.access_reviews_completion_percentage}%` : "0%"}
                </h3>
                <p className="text-xs text-neutral-500 mt-1">User role evaluations certification level.</p>
              </CardContent>
            </Card>

            <Card className="border border-white/5">
              <CardContent className="p-6">
                <span className="text-[10px] text-neutral-500 uppercase font-bold block">
                  PENDING MODEL PROMOTIONS
                </span>
                <h3 className="text-2xl font-black text-white mt-1">
                  {gov ? gov.pending_approvals_count : 0}
                </h3>
                <p className="text-xs text-neutral-500 mt-1">Promotion review requests pending in registry.</p>
              </CardContent>
            </Card>
          </div>

          {/* Credentials Status info */}
          <Card className="border border-white/5">
            <CardHeader>
              <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                <Key className="w-4 h-4 text-emerald-400" />
                <span>CRYPTOGRAPHIC CREDENTIAL STATUS</span>
              </h3>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-left border-collapse text-xs md:text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-neutral-500 font-semibold uppercase tracking-wider bg-neutral-950/40">
                    <th className="px-6 py-4">KEY NAME</th>
                    <th className="px-6 py-4">ALGORITHM</th>
                    <th className="px-6 py-4">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-sm">
                  <tr className="hover:bg-white/5 transition">
                    <td className="px-6 py-4 font-medium text-neutral-200">JWT_SECRET_KEY</td>
                    <td className="px-6 py-4 font-mono text-xs">HS256</td>
                    <td className="px-6 py-4">
                      <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded-full font-bold">
                        ACTIVE
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === "registry" && (
        <Card className="border border-white/5">
          <CardHeader>
            <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <span>MODEL REGISTRY FAMILY CATALOG</span>
            </h3>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-left border-collapse text-xs md:text-sm">
              <thead>
                <tr className="border-b border-white/5 text-neutral-500 font-semibold uppercase tracking-wider bg-neutral-950/40">
                  <th className="px-6 py-4">MODEL FAMILY NAME</th>
                  <th className="px-6 py-4">DESCRIPTION</th>
                  <th className="px-6 py-4">CREATION DATE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-sm">
                {modelsRes?.items && modelsRes.items.length > 0 ? (
                  modelsRes.items.map((model) => (
                    <tr key={model.id} className="hover:bg-white/5 transition">
                      <td className="px-6 py-4 font-medium text-neutral-200">{model.name}</td>
                      <td className="px-6 py-4 text-neutral-400">{model.description || "N/A"}</td>
                      <td className="px-6 py-4 text-neutral-500 text-xs">{new Date(model.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={3} className="px-6 py-12 text-center text-sm text-neutral-600 font-medium">
                      No model definitions recorded in registry.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {activeTab === "threats" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2 border border-white/5">
            <CardHeader>
              <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                <span>SIEM THREAT DETECTION VIOLATIONS</span>
              </h3>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-left border-collapse text-xs md:text-sm">
                <thead>
                  <tr className="border-b border-white/5 text-neutral-500 font-semibold uppercase tracking-wider bg-neutral-950/40">
                    <th className="px-6 py-4">THREAT SIGNATURE TYPE</th>
                    <th className="px-6 py-4">VIOLATIONS COUNT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-sm">
                  {threats ? (
                    <>
                      <tr className="hover:bg-white/5 transition">
                        <td className="px-6 py-4 font-medium text-neutral-200">SQL Injection attempts</td>
                        <td className="px-6 py-4 font-bold text-neutral-300">{threats.sql_injection_attempts}</td>
                      </tr>
                      <tr className="hover:bg-white/5 transition">
                        <td className="px-6 py-4 font-medium text-neutral-200">Cross-Site Scripting (XSS)</td>
                        <td className="px-6 py-4 font-bold text-neutral-300">{threats.xss_attempts}</td>
                      </tr>
                      <tr className="hover:bg-white/5 transition">
                        <td className="px-6 py-4 font-medium text-neutral-200">Brute force authorization logins</td>
                        <td className="px-6 py-4 font-bold text-neutral-300">{threats.brute_force_attempts}</td>
                      </tr>
                    </>
                  ) : (
                    <tr>
                      <td colSpan={2} className="px-6 py-12 text-center text-sm text-neutral-600 font-medium">
                        No threat signature telemetry compiled.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Blocked IP Table */}
          <Card className="border border-white/5">
            <CardHeader>
              <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                <AlertTriangle className="w-4 h-4 text-rose-500" />
                <span>FIREWALL BLOCKED CLIENTS</span>
              </h3>
            </CardHeader>
            <CardContent className="p-4">
              {threats?.blocked_ips_list && threats.blocked_ips_list.length > 0 ? (
                <div className="space-y-2">
                  {threats.blocked_ips_list.map((ip) => (
                    <div key={ip} className="p-3 bg-neutral-900 border border-white/5 rounded-lg text-xs font-mono text-neutral-300 flex justify-between items-center">
                      <span>{ip}</span>
                      <span className="text-[10px] uppercase font-bold text-rose-500 tracking-wider">Blocked</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-10 text-xs text-neutral-600 font-semibold leading-relaxed">
                  No malicious IP ranges blocked in active session tables.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
