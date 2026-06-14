import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.gis.cluster_analyzer import cluster_analyzer
from app.services.gis.heatmap_generator import heatmap_generator

logger = logging.getLogger("gis.spatial_analytics")


class SpatialAnalytics:
    async def get_spatial_analytics_report(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Compiles the complete spatial analytics package combining proximity clustering,
        heatmap coordinate arrays, and density counts.
        """
        logger.info("Generating spatial analytics report...")

        clusters = await cluster_analyzer.find_detection_clusters(db, distance_threshold_meters=1500.0)
        heatmap = await heatmap_generator.compile_fire_heatmap(db)

        # Count total clusters and density
        total_clusters = len(clusters)
        total_points = len(heatmap)

        return {
            "total_fire_points": total_points,
            "total_hotspot_clusters": total_clusters,
            "heatmap_data": heatmap,
            "clusters_data": clusters,
        }


spatial_analytics = SpatialAnalytics()
