import { apiRequest } from "@/lib/api-client";

export interface LocationReference {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  address: string | null;
  elevation: number | null;
  description: string | null;
  created_at: string;
}

export interface Region {
  id: string;
  name: string;
  code: string;
  type: string;
  boundary: Record<string, any>;
  parent_id: string | null;
  created_at: string;
}

export interface Zone {
  id: string;
  name: string;
  code: string;
  region_id: string;
  type: string;
  boundary: Record<string, any>;
  risk_level: string;
  created_at: string;
}

export interface Geofence {
  id: string;
  name: string;
  description: string | null;
  type: string;
  geometry: Record<string, any>;
  is_active: boolean;
  created_at: string;
}

export interface FireLocation {
  id: string;
  alert_id: string;
  location_id: string;
  location: LocationReference;
  created_at: string;
}

export const gisService = {
  async createLocation(body: {
    name: string;
    latitude: number;
    longitude: number;
    address?: string;
    elevation?: number;
    description?: string;
  }): Promise<LocationReference> {
    return apiRequest<LocationReference>("/gis/locations", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listLocations(skip = 0, limit = 100, name?: string): Promise<{ items: LocationReference[]; total_count: number }> {
    return apiRequest<{ items: LocationReference[]; total_count: number }>("/gis/locations", {
      params: { skip, limit, ...(name && { name }) },
    });
  },

  async getLocationById(id: string): Promise<LocationReference> {
    return apiRequest<LocationReference>(`/gis/locations/${id}`);
  },

  async createRegion(body: {
    name: string;
    code: string;
    type: string;
    boundary: Record<string, any>;
    parent_id?: string;
  }): Promise<Region> {
    return apiRequest<Region>("/gis/regions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listRegions(skip = 0, limit = 100, type?: string): Promise<{ items: Region[]; total_count: number }> {
    return apiRequest<{ items: Region[]; total_count: number }>("/gis/regions", {
      params: { skip, limit, ...(type && { type_: type }) },
    });
  },

  async getRegionById(id: string): Promise<Region> {
    return apiRequest<Region>(`/gis/regions/${id}`);
  },

  async createZone(body: {
    name: string;
    code: string;
    region_id: string;
    type: string;
    boundary: Record<string, any>;
    risk_level: string;
  }): Promise<Zone> {
    return apiRequest<Zone>("/gis/zones", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listZones(skip = 0, limit = 100, regionId?: string): Promise<{ items: Zone[]; total_count: number }> {
    return apiRequest<{ items: Zone[]; total_count: number }>("/gis/zones", {
      params: { skip, limit, ...(regionId && { region_id: regionId }) },
    });
  },

  async createGeofence(body: {
    name: string;
    description?: string;
    type: string;
    geometry: Record<string, any>;
    is_active: boolean;
  }): Promise<Geofence> {
    return apiRequest<Geofence>("/gis/geofences", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async listGeofences(skip = 0, limit = 100, isActive?: boolean): Promise<{ items: Geofence[]; total_count: number }> {
    return apiRequest<{ items: Geofence[]; total_count: number }>("/gis/geofences", {
      params: { skip, limit, ...(isActive !== undefined && { is_active: isActive }) },
    });
  },

  async listActiveFireLocations(): Promise<FireLocation[]> {
    return apiRequest<FireLocation[]>("/gis/fire-locations");
  },

  async getSpatialAnalytics(): Promise<any> {
    return apiRequest<any>("/gis/spatial-analytics");
  },

  async getCoordinateIntelligence(latitude: number, longitude: number): Promise<any> {
    return apiRequest<any>("/gis/coordinate-intelligence", {
      params: { latitude, longitude },
    });
  },

  async logPatrolHistory(body: {
    entity_type: string;
    entity_id: string;
    latitude: number;
    longitude: number;
  }): Promise<any> {
    return apiRequest<any>("/gis/location-history", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};
