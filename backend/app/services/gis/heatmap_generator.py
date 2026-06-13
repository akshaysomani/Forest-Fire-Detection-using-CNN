import logging
from typing import List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.detection import Detection

logger = logging.getLogger("gis.heatmap_generator")


class HeatmapGenerator:
    async def compile_fire_heatmap(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Compiles coordinates and intensities of active verified fire points
        to feed map visualizers (e.g. Leaflet.heat or Google Maps Heatmap Layer).
        Intensity ranges between 0.0 and 1.0 (mapped to CNN model confidence).
        """
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

        heatmap_points = []
        for d in detections:
            heatmap_points.append({
                "latitude": d.latitude,
                "longitude": d.longitude,
                "intensity": round(d.confidence, 2)
            })

        logger.info(f"Heatmap points compiled successfully. Total points: {len(heatmap_points)}")
        return heatmap_points


heatmap_generator = HeatmapGenerator()
