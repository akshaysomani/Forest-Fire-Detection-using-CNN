"use client";

import React from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, Polygon } from "react-leaflet";
import L from "leaflet";

// Standard icon configuration override for webpack module issues in Leaflet
const iconUrl = "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png";
const shadowUrl = "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png";
const DefaultIcon = L.icon({
  iconUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  tooltipAnchor: [16, -28],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

interface MapComponentProps {
  fireLocations?: any[];
  regions?: any[];
  geofences?: any[];
}

export default function MapComponent({ fireLocations = [], regions = [], geofences = [] }: MapComponentProps) {
  const defaultCenter: [number, number] = [37.7749, -122.4194]; // Default Yosemite/California-like center

  return (
    <div className="w-full h-full min-h-[500px] rounded-xl overflow-hidden border border-white/5 relative z-10">
      <MapContainer center={defaultCenter} zoom={6} scrollWheelZoom={true} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Render Active Fire Hotspots */}
        {fireLocations.map((fire) => {
          const lat = fire.location?.latitude;
          const lng = fire.location?.longitude;
          if (lat === undefined || lng === undefined) return null;

          const alert = fire.alert;
          const detection = alert?.detection;
          const severity = alert?.severity || "Medium";
          const message = alert?.message || "Wildfire alert registered at coordinate grid.";
          const confidence = detection?.confidence;
          const timestamp = alert?.created_at || fire.created_at;

          // Color coding for severity badges
          const severityColors: Record<string, string> = {
            Critical: "bg-rose-500/10 text-rose-600 border border-rose-500/30",
            High: "bg-amber-500/10 text-amber-600 border border-amber-500/30",
            Medium: "bg-yellow-500/10 text-yellow-600 border border-yellow-500/30",
            Low: "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30",
          };
          const badgeClass = severityColors[severity] || severityColors.Medium;

          return (
            <React.Fragment key={fire.id}>
              <Marker position={[lat, lng]}>
                <Popup>
                  <div className="text-neutral-900 text-xs p-1 space-y-2 min-w-[200px]">
                    <div className="flex items-center justify-between border-b border-neutral-100 pb-1.5">
                      <span className="font-extrabold text-rose-600 tracking-wide">🔥 ACTIVE FIRE</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-black uppercase ${badgeClass}`}>
                        {severity}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <p className="font-semibold text-neutral-800 leading-normal">{message}</p>
                      <p className="text-[10px] text-neutral-500">
                        <span className="font-medium text-neutral-400 uppercase">Station:</span> {fire.location?.name}
                      </p>
                      {confidence !== undefined && (
                        <p className="text-[10px] text-neutral-500">
                          <span className="font-medium text-neutral-400 uppercase">CNN Confidence:</span> {(confidence * 100).toFixed(1)}%
                        </p>
                      )}
                      <p className="text-[10px] text-neutral-500">
                        <span className="font-medium text-neutral-400 uppercase">Coords:</span> {lat.toFixed(4)}, {lng.toFixed(4)}
                      </p>
                      <p className="text-[9px] text-neutral-400 italic pt-0.5 border-t border-neutral-50 mt-1">
                        Logged: {new Date(timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </Popup>
              </Marker>
              {/* Circular warning buffer area around the hotspot */}
              <Circle
                center={[lat, lng]}
                pathOptions={{
                  color: severity === "Critical" ? "red" : "orange",
                  fillColor: severity === "Critical" ? "red" : "orange",
                  fillOpacity: 0.12,
                }}
                radius={2000} // 2km radius circle
              />
            </React.Fragment>
          );
        })}

        {/* Render Circular Geofences */}
        {geofences.map((gf) => {
          const geom = gf.geometry || {};
          if (gf.type === "circle" && geom.center) {
            return (
              <Circle
                key={gf.id}
                center={[geom.center.latitude, geom.center.longitude]}
                radius={geom.radius || 5000}
                pathOptions={{ color: "amber", fillColor: "amber", fillOpacity: 0.08 }}
              />
            );
          }
          return null;
        })}
      </MapContainer>
    </div>
  );
}
