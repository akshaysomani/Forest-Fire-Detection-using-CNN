import threading
from typing import Dict, Tuple, List


class RunManager:
    def __init__(self):
        # Maps run_id string to a tuple of (Thread, Event)
        self._active_runs: Dict[str, Tuple[threading.Thread, threading.Event]] = {}
        self._lock = threading.Lock()

    def register_run(self, run_id: str, thread: threading.Thread, cancel_event: threading.Event) -> None:
        """Register a new active training run thread."""
        with self._lock:
            self._active_runs[str(run_id)] = (thread, cancel_event)

    def deregister_run(self, run_id: str) -> None:
        """Remove a run from the registry upon termination."""
        with self._lock:
            self._active_runs.pop(str(run_id), None)

    def stop_run(self, run_id: str) -> bool:
        """Signal early stopping to a running thread. Returns True if found."""
        with self._lock:
            run_info = self._active_runs.get(str(run_id))
            if run_info:
                thread, cancel_event = run_info
                cancel_event.set()
                return True
            return False

    def is_running(self, run_id: str) -> bool:
        """Check if a specific run is currently executing."""
        with self._lock:
            return str(run_id) in self._active_runs

    def list_active_runs(self) -> List[str]:
        """List all active training run IDs."""
        with self._lock:
            return list(self._active_runs.keys())


run_manager = RunManager()
