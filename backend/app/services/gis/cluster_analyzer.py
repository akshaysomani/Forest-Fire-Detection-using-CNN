import math
import uuid
import logging
from typing import List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.detection import Detection
from app.services.gis.boundary_engine import boundary_engine

logger = logging.getLogger("gis.cluster_analyzer")


class ClusterAnalyzer:
    async def find_detection_clusters(
        self,
        db: AsyncSession,
        distance_threshold_meters: float = 1000.0
    ) -> List[Dict[str, Any]]:
        """
        Groups active verified fire detections into proximity clusters using a greedy
        DBSCAN-like spatial clustering algorithm. Returns clusters with centroids and sizes.
        """
        # Fetch verified fire detections that have coordinate metadata
        query = select(Detection).where(
            and_(
                Detection.prediction_label == "fire",
                Detection.latitude.isnot(None),
                Detection.longitude.isnot(None),
                Detection.deleted_at.is_(None)
            )
        )
        res = await db.execute(query)
        detections = res.scalars().all()

        if not detections:
            return []

        clusters = []
        visited = set()

        for d in detections:
            if d.id in visited:
                continue

            # Start a new cluster
            current_cluster = [d]
            visited.add(d.id)

            # Find all neighbors within the distance threshold
            for candidate in detections:
                if candidate.id in visited:
                    continue

                dist = boundary_engine.haversine_distance(
                    d.latitude, d.longitude,
                    candidate.latitude, candidate.longitude
                )
                if dist <= distance_threshold_meters:
                    current_cluster.append(candidate)
                    visited.add(candidate.id)

            # Compute Centroid
            avg_lat = sum(item.latitude for item in current_cluster) / len(current_cluster)
            avg_lng = sum(item.longitude for item in current_cluster) / len(current_cluster)

            clusters.append({
                "cluster_id": str(uuid.uuid4()),
                "centroid_latitude": round(avg_lat, 5),
                "centroid_longitude": round(avg_lng, 5),
                "detection_count": len(current_cluster),
                "detection_ids": [str(item.id) for item in current_cluster]
            })

        logger.info(f"Spatial clustering completed. Formed {len(clusters)} clusters from {len(detections)} points.")
        return clusters


cluster_analyzer = ClusterAnalyzer()
