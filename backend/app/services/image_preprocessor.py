import io
from datetime import datetime
from typing import Dict, Any, Tuple
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from fastapi.concurrency import run_in_threadpool


class ImagePreprocessor:
    @staticmethod
    def _get_gps_float(values) -> float | None:
        """Convert GPS degree/minute/second lists to float."""
        try:
            # Pillow returns coordinates as tuple of fractions (deg, min, sec)
            d = float(values[0])
            m = float(values[1])
            s = float(values[2])
            return d + (m / 60.0) + (s / 3600.0)
        except Exception:
            return None

    @classmethod
    def extract_exif(cls, file_bytes: bytes) -> Dict[str, Any]:
        """
        Extract EXIF, GPS and hardware metadata from image.
        Returns a dict of parsed fields.
        """
        result = {
            "width": 0,
            "height": 0,
            "captured_at": None,
            "camera_make": None,
            "camera_model": None,
            "gps_latitude": None,
            "gps_longitude": None,
            "exif_raw": {}
        }
        try:
            img = Image.open(io.BytesIO(file_bytes))
            result["width"], result["height"] = img.size

            exif = img.getexif()
            if not exif:
                return result

            # Parse EXIF tags
            exif_dict = {}
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                # Convert bytes or complex values to string/serializable values
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="ignore")
                    except Exception:
                        value = str(value)
                elif not isinstance(value, (int, float, str, bool, dict, list)) and value is not None:
                    value = str(value)
                exif_dict[str(tag_name)] = value

            result["exif_raw"] = exif_dict
            result["camera_make"] = exif_dict.get("Make")
            result["camera_model"] = exif_dict.get("Model")

            # Try parsing captured timestamp
            date_str = exif_dict.get("DateTimeOriginal") or exif_dict.get("DateTime")
            if date_str:
                try:
                    # Standard EXIF format: 'YYYY:MM:DD HH:MM:SS'
                    result["captured_at"] = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except Exception:
                    pass

            # Parse GPS Metadata if available
            # GPSInfo tag ID is typically 34853
            gps_info = exif.get_ifd(34853)
            if gps_info:
                gps_dict = {}
                for key, val in gps_info.items():
                    gps_tag = GPSTAGS.get(key, key)
                    gps_dict[str(gps_tag)] = val

                lat_val = gps_dict.get("GPSLatitude")
                lat_ref = gps_dict.get("GPSLatitudeRef", "N")
                lon_val = gps_dict.get("GPSLongitude")
                lon_ref = gps_dict.get("GPSLongitudeRef", "E")

                if lat_val and lon_val:
                    lat = cls._get_gps_float(lat_val)
                    lon = cls._get_gps_float(lon_val)

                    if lat is not None:
                        if lat_ref == "S":
                            lat = -lat
                        result["gps_latitude"] = lat

                    if lon is not None:
                        if lon_ref == "W":
                            lon = -lon
                        result["gps_longitude"] = lon

        except Exception:
            # If EXIF parse fails, return default empty dict with size
            pass

        return result

    async def resize_image(self, file_bytes: bytes, width: int, height: int, format: str = "PNG") -> bytes:
        """Resize image bytes to target resolution using threadpool."""
        def _resize():
            img = Image.open(io.BytesIO(file_bytes))
            # Keep color profiles / transparency
            resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            resized_img.save(out, format=format)
            return out.getvalue()

        return await run_in_threadpool(_resize)

    async def convert_format(self, file_bytes: bytes, target_format: str = "WEBP", quality: int = 85) -> bytes:
        """Convert image bytes format using threadpool."""
        def _convert():
            img = Image.open(io.BytesIO(file_bytes))
            out = io.BytesIO()
            # Handle RGBA/transparency logic for JPEG
            if target_format.upper() in ("JPEG", "JPG") and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.save(out, format=target_format, quality=quality)
            return out.getvalue()

        return await run_in_threadpool(_convert)


image_preprocessor = ImagePreprocessor()
