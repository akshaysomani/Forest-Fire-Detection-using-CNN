import logging
from typing import Optional

logger = logging.getLogger("alert.risk_score_calculator")


class RiskScoreCalculator:
    @staticmethod
    def calculate_score(
        label: str,
        confidence: float,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        category: Optional[str] = None,
    ) -> float:
        """
        Calculate a composite risk score (0.0 to 100.0) based on prediction parameters,
        geographical risk zones, and category metadata.
        """
        if label.lower() != "fire":
            return 0.0

        # Base score is based on confidence (up to 80 points)
        base_score = confidence * 80.0

        # Location factor (up to 15 points)
        location_score = 0.0
        if latitude is not None and longitude is not None:
            # Designate certain latitude/longitude bounding boxes as high risk forest zones
            # e.g., Mediterranean dry zones, California/Pacific Northwest approximations
            is_high_risk_zone = (32.0 <= latitude <= 42.0 and -125.0 <= longitude <= -114.0) or (  # California approx
                35.0 <= latitude <= 45.0 and -10.0 <= longitude <= 30.0
            )  # Med approx
            if is_high_risk_zone:
                location_score = 15.0
                logger.debug("High risk geographical zone detected, adding risk weight.")
            else:
                location_score = 5.0
        else:
            location_score = 0.0

        # Category factor (up to 5 points)
        category_score = 0.0
        if category:
            cat_lower = category.lower()
            if "forest" in cat_lower or "dry" in cat_lower or "wildfire" in cat_lower:
                category_score = 5.0
            elif "dense" in cat_lower or "vegetation" in cat_lower:
                category_score = 3.0
            else:
                category_score = 1.0

        composite_score = base_score + location_score + category_score
        return min(max(composite_score, 0.0), 100.0)


risk_score_calculator = RiskScoreCalculator()
