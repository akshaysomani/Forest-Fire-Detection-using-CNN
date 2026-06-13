import torch
import torch.nn as nn
import logging
from typing import Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.inference.model_loader import model_loader
from app.services.training.model_factory import model_factory
from app.services.inference.model_registry_adapter import model_registry_adapter
from app.core.exceptions import EntityNotFoundException, BaseAPIException

logger = logging.getLogger("inference.model_manager")


class ModelManager:
    def __init__(self):
        self._cached_models: Dict[str, nn.Module] = {}  # Map of checkpoint_path -> nn.Module
        self._active_model_name: Optional[str] = None
        self._active_checkpoint_path: Optional[str] = None
        self._active_run_id: Optional[str] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initialized ModelManager on device: {self._device}")

    @property
    def device(self) -> torch.device:
        return self._device

    def get_active_model_details(self) -> dict:
        """Returns details about the active loaded model."""
        return {
            "model_name": self._active_model_name,
            "checkpoint_path": self._active_checkpoint_path,
            "run_id": self._active_run_id,
            "device": str(self._device),
            "cached_count": len(self._cached_models)
        }

    def clear_cache(self) -> None:
        """Clear loaded PyTorch models cache to release memory."""
        self._cached_models.clear()
        import gc
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        logger.info("Cleared model manager cache and freed CUDA/RAM memory.")

    async def get_active_model(self, db: AsyncSession) -> Tuple[nn.Module, str, str]:
        """
        Retrieves the current active model, loading it if not cached.
        If no active model has been set, dynamically resolves the latest completed run from the registry.
        Returns a tuple of (model, model_name, model_version).
        """
        if self._active_checkpoint_path and self._active_checkpoint_path in self._cached_models:
            model = self._cached_models[self._active_checkpoint_path]
            version = self._active_run_id or "1.0.0"
            return model, self._active_model_name or "unknown", version

        # Resolve active production model from registry if available
        try:
            from sqlalchemy import and_, select
            from app.models.model_registry import ModelDeployment, ModelVersion, ModelArtifact, RegisteredModel
            
            deploy_query = select(ModelDeployment).where(
                and_(
                    ModelDeployment.environment == "production",
                    ModelDeployment.status == "active",
                    ModelDeployment.deleted_at.is_(None)
                )
            ).order_by(ModelDeployment.deployed_at.desc()).limit(1)
            res_deploy = await db.execute(deploy_query)
            deploy = res_deploy.scalar_one_or_none()
            if deploy:
                version_query = select(ModelVersion).where(
                    and_(ModelVersion.id == deploy.model_version_id, ModelVersion.deleted_at.is_(None))
                )
                res_ver = await db.execute(version_query)
                version = res_ver.scalar_one_or_none()
                if version:
                    # Resolve weights artifact
                    artifact_query = select(ModelArtifact).where(
                        and_(
                            ModelArtifact.model_version_id == version.id,
                            ModelArtifact.artifact_type == "weights",
                            ModelArtifact.deleted_at.is_(None)
                        )
                    ).limit(1)
                    res_art = await db.execute(artifact_query)
                    art = res_art.scalar_one_or_none()
                    
                    if art:
                        # Resolve parent model name
                        m_query = select(RegisteredModel).where(
                            and_(RegisteredModel.id == version.model_id, RegisteredModel.deleted_at.is_(None))
                        )
                        res_m = await db.execute(m_query)
                        reg_model = res_m.scalar_one_or_none()
                        
                        if reg_model:
                            model = await self.load_and_set_active_model(
                                model_name=reg_model.name,
                                checkpoint_path=art.uri,
                                run_id=str(version.id)
                            )
                            # Set cached active parameters
                            self._active_model_name = reg_model.name
                            self._active_checkpoint_path = art.uri
                            self._active_run_id = version.version
                            return model, reg_model.name, version.version
        except Exception as e:
            logger.warning(f"Could not load active production deployment from model registry: {str(e)}. Falling back to training runs.")

        # Resolve latest completed run if no model is loaded
        try:
            run_id, model_name, checkpoint_path = await model_registry_adapter.get_latest_completed_run_checkpoint(db)
            model = await self.load_and_set_active_model(
                model_name=model_name,
                checkpoint_path=checkpoint_path,
                run_id=run_id
            )
            return model, model_name, run_id
        except EntityNotFoundException as e:
            # Fallback to loading an un-pretrained default CustomCNN if no runs exist
            # This allows the API to boot and handle tests even before first training run is run.
            fallback_name = "custom_cnn"
            fallback_key = "fallback_default_init"
            if fallback_key not in self._cached_models:
                logger.warning("No completed training runs found in registry. Initializing empty fallback CustomCNN.")
                model = model_factory.create_model(fallback_name, num_classes=2, pretrained=False)
                model.to(self._device)
                model.eval()
                self._cached_models[fallback_key] = model
            
            self._active_model_name = fallback_name
            self._active_checkpoint_path = fallback_key
            self._active_run_id = "0.0.0"
            return self._cached_models[fallback_key], fallback_name, "0.0.0"

    async def load_and_set_active_model(
        self,
        model_name: str,
        checkpoint_path: str,
        run_id: str
    ) -> nn.Module:
        """
        Loads the specified model from checkpoint, updates cache, and sets it as the active model.
        This enables hot-swapping models dynamically.
        """
        if checkpoint_path in self._cached_models:
            logger.info(f"Model checkpoint already in cache. Swapping active pointer to: {checkpoint_path}")
            self._active_model_name = model_name
            self._active_checkpoint_path = checkpoint_path
            self._active_run_id = run_id
            return self._cached_models[checkpoint_path]

        # Load fresh instance
        model = await model_loader.load_model_from_checkpoint(
            model_name=model_name,
            checkpoint_path=checkpoint_path,
            device=self._device
        )
        
        # Cache weights and update references
        self._cached_models[checkpoint_path] = model
        self._active_model_name = model_name
        self._active_checkpoint_path = checkpoint_path
        self._active_run_id = run_id
        
        return model


model_manager = ModelManager()
