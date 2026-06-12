import io
import torch
import torch.nn as nn
from typing import Dict, Any, Tuple
from app.services.storage_service import storage_service


class CheckpointManager:
    @staticmethod
    async def save_checkpoint(
        run_id: str,
        epoch: int,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        val_loss: float,
        val_accuracy: float,
        hyperparameters: Dict[str, Any],
        is_best: bool = False
    ) -> str:
        """
        Serialize model and optimizer states to bytes and save via storage_service.
        Saves to 'runs/{run_id}/checkpoints/epoch_{epoch}.pth'
        If is_best is True, also copies/saves to 'runs/{run_id}/checkpoints/best_model.pth'
        Returns the relative storage path of the checkpoint.
        """
        checkpoint_data = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "val_loss": val_loss,
            "val_accuracy": val_accuracy,
            "hyperparameters": hyperparameters
        }

        buffer = io.BytesIO()
        torch.save(checkpoint_data, buffer)
        file_bytes = buffer.getvalue()

        filename = f"epoch_{epoch}.pth"
        storage_path = f"runs/{run_id}/checkpoints/{filename}"
        await storage_service.save_file(file_bytes, storage_path)

        if is_best:
            best_path = f"runs/{run_id}/checkpoints/best_model.pth"
            await storage_service.save_file(file_bytes, best_path)

        return storage_path

    @staticmethod
    async def load_checkpoint(
        storage_path: str,
        model: nn.Module,
        optimizer: torch.optim.Optimizer | None = None,
        device: torch.device | None = None
    ) -> Tuple[int, float, float, Dict[str, Any]]:
        """
        Load checkpoint from storage and restore model and optimizer state.
        Returns a tuple of (epoch, val_loss, val_accuracy, hyperparameters).
        """
        file_bytes = await storage_service.read_file(storage_path)
        buffer = io.BytesIO(file_bytes)

        map_location = device if device else torch.device("cpu")
        checkpoint_data = torch.load(buffer, map_location=map_location)

        model.load_state_dict(checkpoint_data["model_state_dict"])
        if optimizer and "optimizer_state_dict" in checkpoint_data:
            optimizer.load_state_dict(checkpoint_data["optimizer_state_dict"])

        epoch = checkpoint_data.get("epoch", 0)
        val_loss = checkpoint_data.get("val_loss", 0.0)
        val_accuracy = checkpoint_data.get("val_accuracy", 0.0)
        hyperparameters = checkpoint_data.get("hyperparameters", {})

        return epoch, val_loss, val_accuracy, hyperparameters


checkpoint_manager = CheckpointManager()
