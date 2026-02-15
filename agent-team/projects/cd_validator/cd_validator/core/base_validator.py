"""
Base Validator - Foundation class for all CD validators.

Handles RevitMCPBridge connection via named pipe and provides
common validation infrastructure.
"""

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Windows named pipe support
try:
    import win32file
    import win32pipe
    import pywintypes
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"           # Informational, no action required
    WARNING = "warning"     # Should be reviewed, may be intentional
    ERROR = "error"         # Must be fixed before issue
    CRITICAL = "critical"   # Blocks document production


@dataclass
class ValidationResult:
    """Single validation finding."""
    rule_id: str
    message: str
    severity: ValidationSeverity
    element_id: Optional[int] = None
    element_type: Optional[str] = None
    location: Optional[str] = None  # Sheet number, view name, etc.
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "location": self.location,
            "suggestion": self.suggestion,
            "metadata": self.metadata,
        }


class RevitMCPConnection:
    """
    Connection handler for RevitMCPBridge via named pipe.

    Pipe: \\\\.\\pipe\\RevitMCPBridge2026
    Protocol: JSON request/response
    """

    PIPE_NAME = r'\\.\pipe\RevitMCPBridge2026'
    BUFFER_SIZE = 65536  # 64KB
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5  # seconds

    # Windows error codes for pipe issues
    ERROR_BROKEN_PIPE = 109
    ERROR_PIPE_BUSY = 231

    def __init__(self):
        if not PYWIN32_AVAILABLE:
            raise RuntimeError(
                "pywin32 not installed. Install with: pip install pywin32"
            )
        self._connected = False

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a request to RevitMCPBridge and return the response.

        Args:
            method: MCP method name (e.g., "getAllSheets", "getViewsOnSheet")
            params: Method parameters as dictionary

        Returns:
            Response dictionary with 'success' key and result data
        """
        import time
        params = params or {}
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Connect to named pipe
                handle = win32file.CreateFile(
                    self.PIPE_NAME,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )

                # Build request
                request = {
                    "method": method,
                    "params": params
                }
                request_json = json.dumps(request)

                # Send request
                win32file.WriteFile(handle, request_json.encode('utf-8'))

                # Read response
                result, data = win32file.ReadFile(handle, self.BUFFER_SIZE)

                # Close handle
                win32file.CloseHandle(handle)

                # Parse response
                response = json.loads(data.decode('utf-8'))
                return response

            except pywintypes.error as e:
                last_error = e
                error_code = e.args[0]

                if error_code == 2:  # ERROR_FILE_NOT_FOUND
                    return {
                        "success": False,
                        "error": "RevitMCPBridge not running. Start MCP Server in Revit."
                    }
                elif error_code in (self.ERROR_BROKEN_PIPE, self.ERROR_PIPE_BUSY):
                    # Retry on broken pipe or busy pipe
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "error": f"Pipe error after {self.MAX_RETRIES} retries ({error_code}): {e.args[2]}"
                    }
                return {
                    "success": False,
                    "error": f"Pipe error ({error_code}): {e.args[2]}"
                }
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON response: {e}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        # Should not reach here, but just in case
        return {
            "success": False,
            "error": f"Unexpected retry exhaustion: {last_error}"
        }

    def is_connected(self) -> bool:
        """Test if MCP server is responsive."""
        response = self.send_request("getProjectInfo", {})
        return response.get("success", False)


class BaseValidator(ABC):
    """
    Abstract base class for all CD validators.

    Subclasses must implement:
        - name: Human-readable validator name
        - description: What this validator checks
        - validate(): Run validation and return results
    """

    def __init__(self, connection: Optional[RevitMCPConnection] = None):
        """
        Initialize validator with optional MCP connection.

        Args:
            connection: Existing RevitMCPConnection, or None to create new
        """
        self._connection = connection or RevitMCPConnection()
        self._results: List[ValidationResult] = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable validator name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this validator checks."""
        pass

    @property
    def connection(self) -> RevitMCPConnection:
        """Get the MCP connection."""
        return self._connection

    @property
    def results(self) -> List[ValidationResult]:
        """Get validation results."""
        return self._results

    def clear_results(self) -> None:
        """Clear previous validation results."""
        self._results = []

    def add_result(
        self,
        rule_id: str,
        message: str,
        severity: ValidationSeverity,
        element_id: Optional[int] = None,
        element_type: Optional[str] = None,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
        **metadata
    ) -> None:
        """Add a validation result."""
        self._results.append(ValidationResult(
            rule_id=rule_id,
            message=message,
            severity=severity,
            element_id=element_id,
            element_type=element_type,
            location=location,
            suggestion=suggestion,
            metadata=metadata,
        ))

    @abstractmethod
    def validate(self) -> List[ValidationResult]:
        """
        Run validation and return results.

        Returns:
            List of ValidationResult objects
        """
        pass

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of validation results."""
        counts = {s.value: 0 for s in ValidationSeverity}
        for result in self._results:
            counts[result.severity.value] += 1

        return {
            "validator": self.name,
            "total_issues": len(self._results),
            "by_severity": counts,
            "passed": counts["error"] == 0 and counts["critical"] == 0,
        }

    def to_json(self) -> str:
        """Export results as JSON."""
        return json.dumps({
            "validator": self.name,
            "description": self.description,
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self._results],
        }, indent=2)
