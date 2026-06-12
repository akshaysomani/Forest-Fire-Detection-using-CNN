import io
import random
from typing import List, Dict, Any
import numpy as np
from PIL import Image
from app.models.dataset import DatasetFile
from app.services.storage_service import storage_service


class DataStatistics:
    @staticmethod
    async def compute_statistics(files: List[DatasetFile]) -> Dict[str, Any]:
        """
        Compute dataset statistics:
        - Class balance (count & ratio per label)
        - Average image dimensions (width, height) from DB metadata
        - Approximated channel mean and standard deviation (based on up to 50 samples)
        """
        total_files = len(files)
        if total_files == 0:
            return {
                "total_files": 0,
                "class_distribution": {},
                "avg_width": 0.0,
                "avg_height": 0.0,
                "channel_mean": [0.485, 0.456, 0.406],
                "channel_std": [0.229, 0.224, 0.225]
            }

        # Class balance
        class_counts: Dict[str, int] = {}
        for f in files:
            label_name = "Unlabeled"
            if f.label:
                label_name = f.label.name
            elif f.label_id:
                label_name = str(f.label_id)

            class_counts[label_name] = class_counts.get(label_name, 0) + 1

        class_distribution = {
            name: {
                "count": count,
                "percentage": round((count / total_files) * 100, 2)
            }
            for name, count in class_counts.items()
        }

        # Average dimensions from metadata
        widths = []
        heights = []
        for f in files:
            meta = f.metadata_json or {}
            w = meta.get("width")
            h = meta.get("height")
            if w:
                widths.append(float(w))
            if h:
                heights.append(float(h))

        avg_width = float(np.mean(widths)) if widths else 0.0
        avg_height = float(np.mean(heights)) if heights else 0.0

        # Sample channel mean/std calculation (up to 50 samples to avoid I/O bottlenecks)
        sampled_files = files
        if len(files) > 50:
            # Seed the sample selection locally for reproducible stats
            rng = random.Random(42)
            sampled_files = rng.sample(files, 50)

        means = []
        stds = []
        for f in sampled_files:
            try:
                img_bytes = await storage_service.read_file(f.file_path)
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                arr = np.array(img) / 255.0  # Shape: (H, W, C)
                # Compute channel-wise mean and std (axes 0 and 1 are H and W)
                means.append(np.mean(arr, axis=(0, 1)))
                stds.append(np.std(arr, axis=(0, 1)))
            except Exception:
                continue

        if means:
            channel_mean = np.mean(means, axis=0).tolist()
            channel_std = np.mean(stds, axis=0).tolist()
        else:
            # ImageNet default constants
            channel_mean = [0.485, 0.456, 0.406]
            channel_std = [0.229, 0.224, 0.225]

        return {
            "total_files": total_files,
            "class_distribution": class_distribution,
            "avg_width": round(avg_width, 1),
            "avg_height": round(avg_height, 1),
            "channel_mean": [round(m, 4) for m in channel_mean],
            "channel_std": [round(s, 4) for s in channel_std]
        }


data_statistics = DataStatistics()
