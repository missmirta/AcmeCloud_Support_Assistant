"""
Audit logging for backend requests.
Tracks all requests and responses for review verification.
"""

from datetime import datetime
from typing import List, Dict, Any
import json


class AuditLog:
    """Logs all backend requests and responses."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log(self, method: str, path: str, params: Dict[str, Any]):
        """Log an incoming request."""
        self.entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "method": method,
            "path": path,
            "params": params
        })

    def log_response(self, method: str, path: str, response: Any, stale: bool = False):
        """Log a successful response."""
        self.entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "method": method,
            "path": path,
            "response": response,
            "stale": stale
        })

    def log_failure(self, method: str, path: str, failure: Dict[str, Any]):
        """Log a failure."""
        self.entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "failure",
            "method": method,
            "path": path,
            "failure": failure
        })

    def get_log(self) -> List[Dict[str, Any]]:
        """Get all log entries."""
        return self.entries

    def clear(self):
        """Clear the log."""
        self.entries = []

    def save_to_file(self, filename: str):
        """Save log to file."""
        with open(filename, "w") as f:
            json.dump(self.entries, f, indent=2)
