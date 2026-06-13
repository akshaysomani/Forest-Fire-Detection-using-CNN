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
          return (
            <React.Fragment key={fire.id}>
              <Marker position={[lat, lng]}>
                <Popup>
                  <div className="text-neutral-900 text-xs">
                    <h5 className="font-bold text-rose-600">⚠️ ACTIVE HOTSPOT</h5>
                    <p className="mt-1 font-medium">{fire.location?.name}</p>
                    <p className="text-[10px] text-neutral-500 mt-0.5">Coordinates: {lat.toFixed(4)}, {lng.toFixed(4)}</p>
                  </div>
                </Popup>
              </Marker>
              {/* Circular warning buffer area around the hotspot */}
              <Circle
                center={[lat, lng]}
                pathOptions={{ color: "red", fillColor: "red", fillOpacity: 0.15 }}
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
