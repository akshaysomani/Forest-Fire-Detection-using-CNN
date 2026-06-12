import random
from typing import List, Dict, Tuple, Any
from app.models.dataset import DatasetFile


class DatasetSplitter:
    @staticmethod
    def split_dataset(
        files: List[DatasetFile],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42
    ) -> Tuple[List[DatasetFile], List[DatasetFile], List[DatasetFile]]:
        """
        Split a list of DatasetFile objects into train, validation, and test sets.
        Uses a stratified split to ensure each split has proportional class representations.
        """
        # Allow slight floating point variations by checking proximity to 1.0
        total_ratio = train_ratio + val_ratio + test_ratio
        if not (0.99 <= total_ratio <= 1.01):
            raise ValueError(f"Split ratios must sum to 1.0 (current sum: {total_ratio})")

        # Group files by label_id
        label_groups: Dict[Any, List[DatasetFile]] = {}
        for f in files:
            label_groups.setdefault(f.label_id, []).append(f)

        train_files: List[DatasetFile] = []
        val_files: List[DatasetFile] = []
        test_files: List[DatasetFile] = []

        # Use an isolated Random generator to guarantee local thread-safe reproducibility
        rng = random.Random(seed)

        for label_id, group in label_groups.items():
            # Copy to avoid side-effects
            shuffled_group = list(group)
            rng.shuffle(shuffled_group)

            n = len(shuffled_group)
            if n == 0:
                continue

            # Compute split indexes
            train_end = int(train_ratio * n)
            val_end = train_end + int(val_ratio * n)

            # Ensure each split receives at least one sample if dataset contains enough elements
            if n >= 3:
                if train_end == 0:
                    train_end = 1
                if val_end == train_end:
                    val_end = train_end + 1

            train_files.extend(shuffled_group[:train_end])
            val_files.extend(shuffled_group[train_end:val_end])
            test_files.extend(shuffled_group[val_end:])

        # Final shuffle of each combined list so the models don't receive single-class batches initially
        rng.shuffle(train_files)
        rng.shuffle(val_files)
        rng.shuffle(test_files)

        return train_files, val_files, test_files


dataset_splitter = DatasetSplitter()
