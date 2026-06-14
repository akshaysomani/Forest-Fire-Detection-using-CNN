import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Tuple, Any


class Trainer:
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        criterion: nn.Module,
        device: torch.device,
        scheduler: Any = None,
        cancel_event: Any = None,
    ):
        self.model = model
        self.optimizer = optimizer
        self.criterion = criterion
        self.device = device
        self.scheduler = scheduler
        self.cancel_event = cancel_event

    def train_epoch(self, dataloader: DataLoader) -> Tuple[float, float]:
        """Runs a single epoch of training. Returns (average_loss, accuracy)."""
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (inputs, targets) in enumerate(dataloader):
            # Check for cancellation signal at the batch boundary
            if self.cancel_event and self.cancel_event.is_set():
                break

            inputs, targets = inputs.to(self.device), targets.to(self.device)

            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

        epoch_loss = running_loss / total if total > 0 else 0.0
        epoch_acc = correct / total if total > 0 else 0.0

        if self.scheduler:
            # Step the learning rate scheduler if configured
            self.scheduler.step()

        return epoch_loss, epoch_acc

    def validate_epoch(self, dataloader: DataLoader) -> Tuple[float, float]:
        """Runs evaluation over the validation set. Returns (average_loss, accuracy)."""
        self.model.eval()
        running_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            for inputs, targets in dataloader:
                if self.cancel_event and self.cancel_event.is_set():
                    break

                inputs, targets = inputs.to(self.device), targets.to(self.device)
                outputs = self.model(inputs)
                loss = self.criterion(outputs, targets)

                running_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()

        epoch_loss = running_loss / total if total > 0 else 0.0
        epoch_acc = correct / total if total > 0 else 0.0
        return epoch_loss, epoch_acc
