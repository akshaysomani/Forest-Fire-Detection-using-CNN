"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { gisService } from "@/services/gis";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Map, Layers, ShieldAlert, Crosshair, HelpCircle } from "lucide-react";

// Load Map component dynamically with SSR disabled to prevent Leaflet window issues
const MapComponent = dynamic(() => import("@/components/gis/map-component"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[500px] flex items-center justify-center bg-neutral-900 border border-white/5 rounded-xl">
      <div className="flex flex-col items-center space-y-3">
        <div className="w-8 h-8 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
        <span className="text-xs font-semibold text-neutral-400">Loading Geospatial Engine...</span>
      </div>
    </div>
  ),
});

export default function GISPage() {
  const [latInput, setLatInput] = useState("");
  const [lngInput, setLngInput] = useState("");
  const [intelResult, setIntelResult] = useState<any>(null);
  const [searching, setSearching] = useState(false);

  // Queries
  const { data: fireLocations } = useQuery({
    queryKey: ["active-fire-locations"],
    queryFn: gisService.listActiveFireLocations,
  });

  const { data: geofences } = useQuery({
    queryKey: ["active-geofences"],
    queryFn: () => gisService.listGeofences(0, 100),
  });

  const handleCoordinateLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!latInput || !lngInput) return;

    setSearching(true);
    try {
      const res = await gisService.getCoordinateIntelligence(
        parseFloat(latInput),
        parseFloat(lngInput)
      );
      setIntelResult(res);
    } catch (err) {
      setIntelResult({ error: "Failed to compile coordinate intelligence context." });
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center space-x-3">
          <Map className="w-8 h-8 text-emerald-500" />
          <span>GEOSPATIAL INTELLIGENCE HUB</span>
        </h1>
        <p className="text-sm text-neutral-400 mt-1">
          Monitor containment rings, active warning buffers, and geofencing grids.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map View Container */}
        <div className="lg:col-span-2 h-[600px]">
          <MapComponent
            fireLocations={fireLocations || []}
            geofences={geofences?.items || []}
          />
        </div>

        {/* Intelligence Sidebars */}
        <div className="space-y-6">
          {/* Spatial Lookup Card */}
          <Card className="border border-white/5">
            <CardHeader>
              <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                <Crosshair className="w-4 h-4 text-emerald-400" />
                <span>COORDINATE INTELLIGENCE SCAN</span>
              </h3>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCoordinateLookup} className="space-y-4">
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
                <Button variant="primary" type="submit" loading={searching} className="w-full">
                  Scan Coordinates
                </Button>
              </form>

              {intelResult && (
                <div className="mt-6 p-4 rounded-lg bg-neutral-900/40 border border-white/5 text-xs space-y-3">
                  {intelResult.error ? (
                    <span className="text-rose-400 font-semibold">{intelResult.error}</span>
                  ) : (
                    <>
                      <div className="flex justify-between">
                        <span className="text-neutral-500 font-medium">CONTAINMENT ZONE:</span>
                        <span className="font-semibold text-neutral-200">{intelResult.containment_zone || "None"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-500 font-medium">RISK SCORE:</span>
                        <span
                          className={`font-bold ${
                            intelResult.risk_level === "High" ? "text-rose-400" : "text-emerald-400"
                          }`}
                        >
                          {intelResult.risk_score ?? "Low"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-500 font-medium">GEOFENCE BREACH:</span>
                        <span className="font-semibold text-neutral-200">
                          {intelResult.geofence_breached ? "⚠️ BREACH" : "NORMAL"}
                        </span>
                      </div>
                    </>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Active Hotspots list */}
          <Card className="border border-white/5 max-h-[300px] overflow-y-auto">
            <CardHeader>
              <h3 className="font-bold text-neutral-200 flex items-center space-x-1.5">
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                <span>HOTSPOT GEOLOCATIONS</span>
              </h3>
            </CardHeader>
            <CardContent className="p-0">
              {fireLocations && fireLocations.length > 0 ? (
                <div className="divide-y divide-white/5 text-xs">
                  {fireLocations.map((fire) => (
                    <div key={fire.id} className="p-4 flex justify-between items-center hover:bg-white/5 transition">
                      <div>
                        <span className="font-semibold text-neutral-200">{fire.location?.name}</span>
                        <span className="block text-[10px] text-neutral-500 mt-0.5">
                          {fire.location?.latitude.toFixed(4)}, {fire.location?.longitude.toFixed(4)}
                        </span>
                      </div>
                      <span className="text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 rounded font-bold uppercase">
                        Active
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center py-10 text-sm text-neutral-600 font-medium">
                  No active fire locations recorded on the coordinate grid.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
