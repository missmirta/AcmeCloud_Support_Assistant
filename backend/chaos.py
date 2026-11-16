"""
Chaos injection engine.
Randomly injects failures based on configured chaos level.
"""

import random
from typing import Optional, Dict, Any


class ChaosEngine:
    """Injects configurable chaos into backend responses."""

    def __init__(self, chaos_level: float = 0.0, seed: int = 42):
        """
        Initialize chaos engine.

        Args:
            chaos_level: Probability of failure (0.0 = no failures, 1.0 = always fail)
            seed: Random seed for reproducible failures
        """
        self.chaos_level = chaos_level
        self.rng = random.Random(seed)

        # Failure type distribution (when failure occurs)
        self.failure_types = {
            "timeout": 0.20,      # 20% of failures
            "rate_limit": 0.30,   # 30% of failures
            "stale_data": 0.30,   # 30% of failures
            "service_error": 0.20 # 20% of failures
        }

    def should_fail(self) -> Optional[Dict[str, Any]]:
        """
        Determine if this request should fail.

        Returns:
            None if no failure, or dict with failure details
        """
        if self.rng.random() >= self.chaos_level:
            return None

        # Choose failure type
        r = self.rng.random()
        cumulative = 0.0

        for failure_type, prob in self.failure_types.items():
            cumulative += prob
            if r < cumulative:
                return self._create_failure(failure_type)

        # Fallback (should not reach)
        return self._create_failure("service_error")

    def _create_failure(self, failure_type: str) -> Dict[str, Any]:
        """Create failure details based on type."""
        if failure_type == "timeout":
            return {
                "type": "timeout",
                "delay": self.rng.uniform(5.0, 30.0)  # 5-30 second hang
            }
        elif failure_type == "rate_limit":
            return {
                "type": "rate_limit",
                "retry_after": 5
            }
        elif failure_type == "stale_data":
            return {
                "type": "stale_data",
                "age_hours": self.rng.randint(24, 72)  # 24-72 hours old
            }
        elif failure_type == "service_error":
            return {
                "type": "service_error"
            }
        else:
            return {"type": "unknown"}
