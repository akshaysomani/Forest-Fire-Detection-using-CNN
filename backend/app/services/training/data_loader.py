import os
import io
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from app.core.config import settings
from app.models.dataset import DatasetFile


class ForestFireDataset(Dataset):
    def __init__(self, files: list[DatasetFile], transform=None, label_map=None):
        self.files = files
        self.transform = transform

        # Build consistent label-to-index mapping (0 = first label alphabetically, 1 = second)
        if label_map is None:
            label_ids = sorted(list({f.label_id for f in files if f.label_id is not None}))
            self.label_map = {lid: i for i, lid in enumerate(label_ids)}
        else:
            self.label_map = label_map

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        file_obj = self.files[idx]
        file_path = file_obj.file_path

        # Bypass async storage stack for efficiency within DataLoader subprocesses
        try:
            base_dir = os.path.abspath(settings.STORAGE_BASE_DIR)
            clean_path = os.path.normpath(file_path).lstrip("\\/")
            full_path = os.path.join(base_dir, clean_path)

            if not os.path.exists(full_path):
                # Fallback to simulated cloud directory layouts if provider is not local
                provider_type = settings.STORAGE_PROVIDER.lower()
                if provider_type == "s3":
                    full_path = os.path.abspath(os.path.join("./storage/s3", settings.AWS_S3_BUCKET, clean_path))
                elif provider_type == "gcs":
                    full_path = os.path.abspath(os.path.join("./storage/gcs", settings.GCS_BUCKET, clean_path))
                elif provider_type == "azure":
                    full_path = os.path.abspath(os.path.join("./storage/azure", settings.AZURE_CONTAINER, clean_path))

            with open(full_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            raise FileNotFoundError(f"Failed to read image data from path '{file_path}'. Details: {e}")

        # Open image and convert to RGB
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        if self.transform:
            img = self.transform(img)

        # Retrieve integer label class
        label_idx = self.label_map.get(file_obj.label_id, 0)

        return img, torch.tensor(label_idx, dtype=torch.long)


def get_data_loader(
    files: list[DatasetFile], batch_size: int = 32, transform=None, label_map=None, shuffle: bool = True, num_workers: int = 0
) -> DataLoader:
    """Construct a PyTorch DataLoader wrapper."""
    dataset = ForestFireDataset(files, transform=transform, label_map=label_map)

    # Enable pinned memory if CUDA GPU is active for faster host-to-device transfers
    pin_memory = torch.cuda.is_available()

    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers, pin_memory=pin_memory)
