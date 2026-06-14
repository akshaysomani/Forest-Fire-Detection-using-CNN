class SecurityMetrics:
    def __init__(self):
        self._metrics = {"failed_logins": 0, "blocked_threats": 0, "secret_rotations": 0, "policy_scans": 0}

    def increment(self, name: str) -> None:
        """Increment metric counter."""
        if name in self._metrics:
            self._metrics[name] += 1

    def get_metrics(self) -> dict:
        """Returns current counts."""
        return self._metrics


security_metrics = SecurityMetrics()
