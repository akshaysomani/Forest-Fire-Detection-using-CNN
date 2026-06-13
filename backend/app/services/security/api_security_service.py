import time
from typing import Dict, List, Set, Tuple


class ApiSecurityService:
    def __init__(self):
        # In-memory IP block list and rate limiting window tracker
        self._blocked_ips: Set[str] = set()
        self._rate_limits: Dict[str, List[float]] = {}
        # Max 100 requests per minute from a single IP for general APIs
        self._max_requests = 100
        self._window_seconds = 60

    def block_ip(self, ip: str) -> None:
        """Mark an IP address as explicitly blocked."""
        self._blocked_ips.add(ip)

    def unblock_ip(self, ip: str) -> None:
        """Removes an IP address from the block list."""
        self._blocked_ips.discard(ip)

    def is_ip_blocked(self, ip: str) -> bool:
        """Checks if an IP is currently blocked."""
        return ip in self._blocked_ips

    def check_rate_limit(self, ip: str) -> bool:
        """
        Calculates request frequency. If request count exceeds max limit,
        the IP is temporarily added to the block list.
        """
        if self.is_ip_blocked(ip):
            return False

        now = time.time()
        # Clean expired timestamps
        if ip not in self._rate_limits:
            self._rate_limits[ip] = []
        
        timestamps = self._rate_limits[ip]
        self._rate_limits[ip] = [t for t in timestamps if now - t < self._window_seconds]

        # Check threshold
        if len(self._rate_limits[ip]) >= self._max_requests:
            # Auto block abusive client
            self.block_ip(ip)
            return False

        self._rate_limits[ip].append(now)
        return True

    def get_blocked_ips(self) -> List[str]:
        """Returns the list of all blocked IP addresses."""
        return list(self._blocked_ips)


api_security_service = ApiSecurityService()
