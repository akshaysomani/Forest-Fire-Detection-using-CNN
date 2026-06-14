import math
import logging
from typing import List

logger = logging.getLogger("gis.boundary_engine")


class BoundaryEngine:
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Computes the great-circle distance between two points on a sphere
        using the Haversine formula. Returns distance in meters.
        """
        R = 6371000.0  # Earth's radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2

        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance = R * c
        return distance

    @staticmethod
    def is_point_in_polygon(latitude: float, longitude: float, polygon: List[List[float]]) -> bool:
        """
        Ray-Casting Algorithm to determine if a WGS84 point [lat, lng] is inside a polygon
        defined as a list of coordinates [[lat, lng], [lat, lng], ...].
        """
        if not polygon:
            return False

        # Support GeoJSON style where coordinates are nested inside a single ring
        # polygon: list of [lat, lng] coordinates.
        n = len(polygon)
        inside = False

        p1lat, p1lng = polygon[0]
        for i in range(n + 1):
            p2lat, p2lng = polygon[i % n]
            if longitude > min(p1lng, p2lng):
                if longitude <= max(p1lng, p2lng):
                    if latitude <= max(p1lat, p2lat):
                        if p1lng != p2lng:
                            xinters = (longitude - p1lng) * (p2lat - p1lat) / (p2lng - p1lng) + p1lat
                        if p1lat == p2lat or latitude <= xinters:
                            inside = not inside
            p1lat, p1lng = p2lat, p2lng

        return inside


boundary_engine = BoundaryEngine()
