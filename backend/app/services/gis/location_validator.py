import logging
from app.core.exceptions import ValidationException

logger = logging.getLogger("gis.location_validator")


class LocationValidator:
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """
        Validates latitude and longitude ranges based on WGS84 standard.
        Latitude range: [-90.0, 90.0]
        Longitude range: [-180.0, 180.0]
        """
        if latitude is None or longitude is None:
            raise ValidationException("Latitude and Longitude cannot be null.")

        if not (-90.0 <= latitude <= 90.0):
            logger.warning(f"Invalid latitude detected: {latitude}")
            raise ValidationException(f"Latitude must be between -90.0 and 90.0 degrees. Got: {latitude}")

        if not (-180.0 <= longitude <= 180.0):
            logger.warning(f"Invalid longitude detected: {longitude}")
            raise ValidationException(f"Longitude must be between -180.0 and 180.0 degrees. Got: {longitude}")

        return True


location_validator = LocationValidator()
