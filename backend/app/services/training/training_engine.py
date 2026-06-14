import asyncio
import threading
import uuid
import random
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
import torch
import torch.nn as nn
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models.training import TrainingRun, TrainingCheckpoint
from app.services.training.dataset_preparation import dataset_preparation
from app.services.training.model_factory import model_factory
from app.services.training.data_loader import get_data_loader
from app.services.training.augmentation_manager import augmentation_manager
from app.services.training.trainer import Trainer
from app.services.training.checkpoint_manager import checkpoint_manager
from app.services.training.experiment_tracker import experiment_tracker
from app.services.training.run_manager import run_manager
from app.services.training.evaluation_service import evaluation_service
from app.services.training.evaluation_report_generator import evaluation_report_generator
from app.services.training.hyperparameter_manager import hyperparameter_manager


def seed_everything(seed: int = 42) -> None:
    """Initialize all random seeds to guarantee reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class TrainingEngine:
    def start_training_run(
        self,
        run_id: uuid.UUID,
        dataset_id: uuid.UUID,
        version_str: str | None,
        model_name: str,
        hyperparams_dict: Dict[str, Any] | None,
        user_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Trigger training in a background thread and register it in the run manager.
        """
        cancel_event = threading.Event()
        thread = threading.Thread(
            target=self._run_training_thread_entrypoint,
            args=(run_id, dataset_id, version_str, model_name, hyperparams_dict, user_id, cancel_event),
            daemon=True,
        )
        run_manager.register_run(str(run_id), thread, cancel_event)
        thread.start()
        return run_id

    def _run_training_thread_entrypoint(
        self,
        run_id: uuid.UUID,
        dataset_id: uuid.UUID,
        version_str: str | None,
        model_name: str,
        hyperparams_dict: Dict[str, Any] | None,
        user_id: uuid.UUID,
        cancel_event: threading.Event,
    ) -> None:
        """Background thread entrypoint setting up an async event loop for the database and storage providers."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._execute_training_run_async(
                    run_id, dataset_id, version_str, model_name, hyperparams_dict, user_id, cancel_event
                )
            )
        finally:
            loop.close()
            run_manager.deregister_run(str(run_id))

    async def _execute_training_run_async(
        self,
        run_id: uuid.UUID,
        dataset_id: uuid.UUID,
        version_str: str | None,
        model_name: str,
        hyperparams_dict: Dict[str, Any] | None,
        user_id: uuid.UUID,
        cancel_event: threading.Event,
    ) -> None:
        """Internal asynchronous core training implementation."""
        # 1. Parse and validate hyperparameters
        hparams = hyperparameter_manager.validate_and_parse(hyperparams_dict)
        seed_everything(hparams.random_seed)

        async with SessionLocal() as db:
            # 2. Fetch and initialize database record
            run = await db.get(TrainingRun, run_id)
            if not run:
                return

            run.status = "running"
            run.started_at = datetime.utcnow()
            run.hyperparameters = hyperparameter_manager.serialize(hparams)
            await db.commit()

            try:
                # 3. Load and Split Datasets
                prep_result = await dataset_preparation.prepare_dataset(
                    db=db, dataset_id=dataset_id, version_str=version_str, seed=hparams.random_seed
                )

                train_files = prep_result["train_files"]
                val_files = prep_result["val_files"]
                test_files = prep_result["test_files"]
                stats = prep_result["statistics"]

                # Resolve label mapping consistently
                # (e.g. sorted list of label IDs mapped to 0 and 1)
                all_label_ids = sorted(list({f.label_id for f in train_files if f.label_id is not None}))
                label_map = {lid: idx for idx, lid in enumerate(all_label_ids)}

                # 4. Construct PyTorch DataLoaders
                # Training loader receives augmentation transforms
                train_transform = augmentation_manager.get_transforms(
                    policy="default", custom_config={"mean": stats["channel_mean"], "std": stats["channel_std"]}
                )
                # Validation and testing loaders receive basic resize and normalization transforms (policy="none")
                val_transform = augmentation_manager.get_transforms(
                    policy="none", custom_config={"mean": stats["channel_mean"], "std": stats["channel_std"]}
                )

                train_loader = get_data_loader(
                    files=train_files,
                    batch_size=hparams.batch_size,
                    transform=train_transform,
                    label_map=label_map,
                    shuffle=True,
                )
                val_loader = get_data_loader(
                    files=val_files, batch_size=hparams.batch_size, transform=val_transform, label_map=label_map, shuffle=False
                )
                test_loader = get_data_loader(
                    files=test_files,
                    batch_size=hparams.batch_size,
                    transform=val_transform,
                    label_map=label_map,
                    shuffle=False,
                )

                # 5. Build Model Architecture
                model = model_factory.create_model(
                    model_name=model_name, num_classes=2, pretrained=True, dropout=hparams.dropout
                )

                # Configure Execution device (GPU if available)
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                model.to(device)

                # 6. Configure Optimizer and Criterion
                criterion = nn.CrossEntropyLoss()
                if hparams.optimizer == "adam":
                    optimizer = torch.optim.Adam(
                        model.parameters(), lr=hparams.learning_rate, weight_decay=hparams.weight_decay
                    )
                elif hparams.optimizer == "adamw":
                    optimizer = torch.optim.AdamW(
                        model.parameters(), lr=hparams.learning_rate, weight_decay=hparams.weight_decay
                    )
                else:
                    optimizer = torch.optim.SGD(
                        model.parameters(), lr=hparams.learning_rate, momentum=0.9, weight_decay=hparams.weight_decay
                    )

                # Standard CosineAnnealing Scheduler
                scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=hparams.epochs)

                trainer = Trainer(
                    model=model,
                    optimizer=optimizer,
                    criterion=criterion,
                    device=device,
                    scheduler=scheduler,
                    cancel_event=cancel_event,
                )

                # Early stopping configuration parameters
                patience = 5
                patience_counter = 0
                best_val_loss = float("inf")
                metrics_history: List[Dict[str, Any]] = []

                # 7. Main Epoch Loop
                for epoch in range(1, hparams.epochs + 1):
                    # Check for cancellation signal
                    if cancel_event.is_set():
                        break

                    train_loss, train_acc = trainer.train_epoch(train_loader)
                    val_loss, val_acc = trainer.validate_epoch(val_loader)

                    # Extract current learning rate
                    lr = optimizer.param_groups[0]["lr"]

                    # Log progress
                    epoch_stats = await experiment_tracker.log_epoch(
                        run_id=str(run_id),
                        epoch=epoch,
                        train_loss=train_loss,
                        train_acc=train_acc,
                        val_loss=val_loss,
                        val_acc=val_acc,
                        lr=lr,
                    )
                    metrics_history.append(epoch_stats)

                    # Update Database history logs
                    # We reload to prevent SQLAlchemy session conflicts
                    run = await db.get(TrainingRun, run_id)
                    if not run:
                        break
                    run.metrics_history = metrics_history
                    await db.commit()

                    # Save Checkpoint
                    is_best = val_loss < best_val_loss
                    if is_best:
                        best_val_loss = val_loss
                        patience_counter = 0
                    else:
                        patience_counter += 1

                    checkpoint_path = await checkpoint_manager.save_checkpoint(
                        run_id=str(run_id),
                        epoch=epoch,
                        model=model,
                        optimizer=optimizer,
                        val_loss=val_loss,
                        val_accuracy=val_acc,
                        hyperparameters=hyperparameter_manager.serialize(hparams),
                        is_best=is_best,
                    )

                    # Register checkpoint in the database
                    checkpoint_db = TrainingCheckpoint(
                        run_id=run_id,
                        epoch=epoch,
                        val_loss=val_loss,
                        val_accuracy=val_acc,
                        checkpoint_path=checkpoint_path,
                        is_best=is_best,
                    )
                    db.add(checkpoint_db)
                    await db.commit()

                    # Early stopping termination check
                    if patience_counter >= patience:
                        # Log early stopping to stdout
                        import sys

                        sys.stdout.write(
                            f"Early stopping triggered at epoch {epoch}. Validation loss has not improved for {patience} epochs.\n"
                        )
                        break

                # 8. Post-Training Phase (Evaluation and Artifact Packaging)
                run = await db.get(TrainingRun, run_id)
                if not run:
                    return

                if cancel_event.is_set():
                    run.status = "stopped"
                else:
                    # Load best checkpoint weights for testing evaluation
                    best_checkpoint_path = f"runs/{str(run_id)}/checkpoints/best_model.pth"
                    await checkpoint_manager.load_checkpoint(storage_path=best_checkpoint_path, model=model, device=device)

                    # Evaluate on the unseen test set
                    test_metrics = evaluation_service.evaluate_model(model, test_loader, device)

                    # Generate PDF and Markdown Report Artifacts
                    report_paths = await evaluation_report_generator.generate_and_save_report(
                        run_id=str(run_id),
                        metrics=test_metrics,
                        model_name=model_name,
                        hyperparameters=hyperparameter_manager.serialize(hparams),
                    )

                    # Save complete metadata config, history, and test metrics
                    await experiment_tracker.save_run_metadata(
                        run_id=str(run_id),
                        hyperparameters=hyperparameter_manager.serialize(hparams),
                        metrics_history=metrics_history,
                        evaluation_summary=test_metrics,
                    )

                    run.status = "completed"

                run.completed_at = datetime.utcnow()
                await db.commit()

            except Exception as e:
                # Log traceback and mark run as failed
                import traceback

                error_trace = traceback.format_exc()
                import sys

                sys.stderr.write(f"Background training run {run_id} failed with error: {str(e)}\nTraceback:\n{error_trace}\n")

                run = await db.get(TrainingRun, run_id)
                if run:
                    run.status = "failed"
                    run.error_message = f"Error: {str(e)}\n\n{error_trace[:800]}"
                    run.completed_at = datetime.utcnow()
                    await db.commit()


training_engine = TrainingEngine()
