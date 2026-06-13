"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { incidentService } from "@/services/incidents";
import { alertService } from "@/services/alerts";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUiStore } from "@/store/ui-store";
import { ShieldAlert, Plus, Shield, Users, MapPin, CheckCircle, MessageSquare } from "lucide-react";

export default function OperationsPage() {
  const queryClient = useQueryClient();
  const { addToast } = useUiStore();

  const [activeTab, setActiveTab] = useState<"incidents" | "alerts">("incidents");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);

  // Manual incident form state
  const [descInput, setDescInput] = useState("");
  const [sevInput, setSevInput] = useState("medium");
  const [latInput, setLatInput] = useState("");
  const [lngInput, setLngInput] = useState("");

  // Sitrep update form state
  const [updateMessage, setUpdateMessage] = useState("");
  const [submittingUpdate, setSubmittingUpdate] = useState(false);

  // Queries
  const { data: incidentsRes, isLoading: loadingIncidents } = useQuery({
    queryKey: ["incidents-list"],
    queryFn: () => incidentService.listIncidents({ limit: 100 }),
  });

  const { data: alertsRes, isLoading: loadingAlerts } = useQuery({
    queryKey: ["alerts-list"],
    queryFn: () => alertService.listAlerts({ limit: 100 }),
  });

  const { data: activeIncidentDetails } = useQuery({
    queryKey: ["incident-details", selectedIncidentId],
    queryFn: () => incidentService.getIncidentById(selectedIncidentId!),
    enabled: !!selectedIncidentId,
  });

  const { data: responseTeams } = useQuery({
    queryKey: ["response-teams-list"],
    queryFn: incidentService.listResponseTeams,
  });

  // Mutations
  const createIncidentMutation = useMutation({
    mutationFn: incidentService.createIncident,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents-list"] });
      addToast({
        type: "success",
        title: "Incident Reported",
        message: "A new emergency incident has been successfully logged.",
      });
      setShowCreateModal(false);
      setDescInput("");
      setLatInput("");
      setLngInput("");
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Report Failed",
        message: err.message || "Failed to log incident.",
      });
    },
  });

  const acknowledgeAlertMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) => alertService.acknowledgeAlert(id, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts-list"] });
      addToast({ type: "success", title: "Alert Acknowledged", message: "Alert status updated successfully." });
    },
  });

  const resolveAlertMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) => alertService.resolveAlert(id, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts-list"] });
      addToast({ type: "success", title: "Alert Resolved", message: "Alert marked as resolved." });
    },
  });

  const handleCreateIncident = (e: React.FormEvent) => {
    e.preventDefault();
    if (!descInput.trim() || !latInput || !lngInput) {
      addToast({ type: "warning", title: "Incomplete details", message: "Please provide coordinates and description." });
      return;
    }
    createIncidentMutation.mutate({
      description: descInput,
      severity: sevInput,
      latitude: parseFloat(latInput),
      longitude: parseFloat(lngInput),
    });
  };

  const handleAddSitrep = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updateMessage.trim() || !selectedIncidentId) return;

    setSubmittingUpdate(true);
    try {
      await incidentService.addSitrepUpdate(selectedIncidentId, updateMessage);
      setUpdateMessage("");
      queryClient.invalidateQueries({ queryKey: ["incident-details", selectedIncidentId] });
      addToast({ type: "success", title: "Sitrep Added", message: "Situation report logged successfully." });
    } catch (err: any) {
      addToast({ type: "error", title: "Failed", message: err.message || "Failed to add update." });
    } finally {
      setSubmittingUpdate(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center space-x-3">
            <ShieldAlert className="w-8 h-8 text-rose-500" />
            <span>OPERATIONS CONTROL CENTER</span>
          </h1>
          <p className="text-sm text-neutral-400 mt-1">
            Dispatch response squads, acknowledge neural warnings, and logs incident sitreps.
          </p>
        </div>
        <Button variant="danger" onClick={() => setShowCreateModal(true)} className="flex items-center space-x-1.5 self-start">
          <Plus className="w-4 h-4" />
          <span>Report Emergency</span>
        </Button>
      </div>

      {/* Tabs Menu */}
      <div className="flex space-x-2 border-b border-white/5 pb-0.5">
        <button
          onClick={() => setActiveTab("incidents")}
          className={`px-4 py-2 text-sm font-semibold tracking-wider uppercase transition border-b-2 ${
            activeTab === "incidents"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-neutral-500 hover:text-neutral-300"
          }`}
        >
          Active Incidents ({incidentsRes?.total_count || 0})
        </button>
        <button
          onClick={() => setActiveTab("alerts")}
          className={`px-4 py-2 text-sm font-semibold tracking-wider uppercase transition border-b-2 ${
            activeTab === "alerts"
              ? "border-rose-500 text-rose-400"
              : "border-transparent text-neutral-500 hover:text-neutral-300"
          }`}
        >
          Neural Warnings ({alertsRes?.total_count || 0})
        </button>
      </div>

      {/* Dynamic Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {activeTab === "incidents" ? (
            <Card className="border border-white/5">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs md:text-sm">
                    <thead>
                      <tr className="border-b border-white/5 text-neutral-500 font-semibold uppercase tracking-wider bg-neutral-950/40">
                        <th className="px-6 py-4">DESCRIPTION</th>
                        <th className="px-6 py-4">SEVERITY</th>
                        <th className="px-6 py-4">STATUS</th>
                        <th className="px-6 py-4">REPORT DATE</th>
                        <th className="px-6 py-4 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-sm">
                      {incidentsRes?.incidents && incidentsRes.incidents.length > 0 ? (
                        incidentsRes.incidents.map((inc) => (
                          <tr key={inc.id} className="hover:bg-white/5 transition">
                            <td className="px-6 py-4 font-medium text-neutral-200 truncate max-w-[200px]">{inc.description}</td>
                            <td className="px-6 py-4">
                              <span
                                className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                                  inc.severity === "critical"
                                    ? "bg-rose-500/10 text-rose-400 border border-rose-500/20 animate-pulse"
                                    : inc.severity === "high"
                                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                    : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                }`}
                              >
                                {inc.severity}
                              </span>
                            </td>
                            <td className="px-6 py-4 capitalize text-neutral-400 text-xs font-semibold">{inc.status}</td>
                            <td className="px-6 py-4 text-neutral-500 text-xs">{new Date(inc.created_at).toLocaleDateString()}</td>
                            <td className="px-6 py-4 text-right">
                              <Button variant="outline" size="sm" onClick={() => setSelectedIncidentId(inc.id)}>
                                View Sitrep
                              </Button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} className="px-6 py-12 text-center text-sm text-neutral-600 font-medium">
                            No emergency incidents are currently active.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-white/5">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs md:text-sm">
                    <thead>
                      <tr className="border-b border-white/5 text-neutral-500 font-semibold uppercase tracking-wider bg-neutral-950/40">
                        <th className="px-6 py-4">WARNING MESSAGE</th>
                        <th className="px-6 py-4">SEVERITY</th>
                        <th className="px-6 py-4">STATUS</th>
                        <th className="px-6 py-4 text-right">ACTIONS</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-sm">
                      {alertsRes?.alerts && alertsRes.alerts.length > 0 ? (
                        alertsRes.alerts.map((al) => (
                          <tr key={al.id} className="hover:bg-white/5 transition">
                            <td className="px-6 py-4 font-medium text-neutral-200">{al.message}</td>
                            <td className="px-6 py-4">
                              <span className="text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded font-bold uppercase">
                                {al.severity}
                              </span>
                            </td>
                            <td className="px-6 py-4 capitalize text-neutral-400 text-xs font-semibold">{al.status}</td>
                            <td className="px-6 py-4 text-right space-x-2">
                              {al.status === "active" && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => acknowledgeAlertMutation.mutate({ id: al.id, notes: "Acknowledge alert" })}
                                >
                                  Ack
                                </Button>
                              )}
                              {al.status !== "resolved" && (
                                <Button
                                  variant="primary"
                                  size="sm"
                                  onClick={() => resolveAlertMutation.mutate({ id: al.id, notes: "Resolve alert" })}
                                >
                                  Resolve
                                </Button>
                              )}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="px-6 py-12 text-center text-sm text-neutral-600 font-medium">
                            No neural alert triggers recorded.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right sidebars */}
        <div className="space-y-6">
          {selectedIncidentId && activeIncidentDetails ? (
            <Card className="border border-white/5 flex flex-col justify-between h-[550px]">
              <CardHeader className="border-b border-white/5">
                <h3 className="font-bold text-neutral-200">INCIDENT REPORT SHEETS</h3>
                <p className="text-[10px] text-neutral-500 font-mono mt-0.5">{selectedIncidentId}</p>
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto space-y-4 pt-4">
                <div className="bg-neutral-900/40 border border-white/5 rounded-lg p-4 space-y-2 text-xs">
                  <div className="flex items-center space-x-2 text-neutral-300 font-semibold">
                    <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Coordinates Reference</span>
                  </div>
                  <p className="text-neutral-400 font-semibold pl-5">
                    {activeIncidentDetails.latitude.toFixed(4)}, {activeIncidentDetails.longitude.toFixed(4)}
                  </p>
                </div>

                {/* Sitreps history */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-1.5 text-xs font-bold text-neutral-400">
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>SITUATION LOG UPDATES ({activeIncidentDetails.updates?.length || 0})</span>
                  </div>
                  <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1">
                    {activeIncidentDetails.updates && activeIncidentDetails.updates.length > 0 ? (
                      activeIncidentDetails.updates.map((up: any) => (
                        <div key={up.id} className="p-3 bg-neutral-900/40 border border-white/5 rounded-lg text-xs">
                          <p className="text-neutral-300 leading-relaxed font-semibold">{up.message}</p>
                          <span className="text-[10px] text-neutral-500 block mt-1.5">
                            {new Date(up.created_at).toLocaleString()}
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-neutral-600 font-semibold py-4 text-center">
                        No updates recorded for this incident.
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
              {/* Sitrep submission form */}
              <div className="p-4 border-t border-white/5">
                <form onSubmit={handleAddSitrep} className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Log a new update..."
                    value={updateMessage}
                    onChange={(e) => setUpdateMessage(e.target.value)}
                    className="flex-1 px-3 py-2 bg-neutral-900 border border-white/10 rounded-lg text-xs text-neutral-200 focus:outline-none focus:border-emerald-500"
                  />
                  <Button variant="outline" type="submit" loading={submittingUpdate} size="sm" disabled={!updateMessage.trim()}>
                    Log
                  </Button>
                </form>
              </div>
            </Card>
          ) : (
            <Card className="border border-white/5 p-6 text-center">
              <Shield className="w-10 h-10 text-neutral-600 mx-auto mb-3" />
              <p className="text-sm text-neutral-500">Select an incident view link to see sitrep details and logs.</p>
            </Card>
          )}

          {/* Dispatch Availability Panel */}
          <Card className="border border-white/5">
            <CardHeader>
              <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                <Users className="w-4 h-4 text-emerald-400" />
                <span>RESPONSE TEAMS DISPATCH</span>
              </h3>
            </CardHeader>
            <CardContent className="p-0">
              {responseTeams && responseTeams.length > 0 ? (
                <div className="divide-y divide-white/5 text-xs">
                  {responseTeams.map((team) => (
                    <div key={team.id} className="p-4 flex justify-between items-center hover:bg-white/5 transition">
                      <div>
                        <span className="font-semibold text-neutral-200">{team.name}</span>
                        <span className="block text-[10px] text-neutral-500 mt-0.5">{team.specialty}</span>
                      </div>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-bold uppercase">
                        {team.status}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-10 text-sm text-neutral-600 font-medium">
                  No registered response squads available.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Manual Emergency Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="w-full max-w-[480px] border border-white/10 shadow-glass">
            <CardHeader>
              <h3 className="text-lg font-extrabold text-white">Log Emergency Incident</h3>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateIncident} className="space-y-4">
                <Input
                  label="Description"
                  placeholder="e.g. Active smoke plume observed near campsite..."
                  value={descInput}
                  onChange={(e) => setDescInput(e.target.value)}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Latitude"
                    placeholder="37.7749"
                    value={latInput}
                    onChange={(e) => setLatInput(e.target.value)}
                  />
                  <Input
                    label="Longitude"
                    placeholder="-122.4194"
                    value={lngInput}
                    onChange={(e) => setLngInput(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">
                    Severity Level
                  </label>
                  <select
                    value={sevInput}
                    onChange={(e) => setSevInput(e.target.value)}
                    className="w-full px-4 py-2.5 bg-neutral-900 border border-white/10 rounded-lg text-neutral-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="low">Low Risk</option>
                    <option value="medium">Medium Risk</option>
                    <option value="high">High Risk</option>
                    <option value="critical">Critical Risk</option>
                  </select>
                </div>

                <div className="flex justify-end space-x-3 pt-4 border-t border-white/5 mt-6">
                  <Button variant="outline" type="button" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="danger" type="submit">
                    Dispatch Squads
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
