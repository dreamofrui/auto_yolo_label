"""Shared exception infrastructure for AutoLabeler."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCode(str, Enum):
    """Stable business error codes shared by core, GUI, and API layers."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_RUNNING = "TASK_ALREADY_RUNNING"
    TASK_CANCELLED = "TASK_CANCELLED"

    SCAN_PATH_NOT_FOUND = "SCAN_PATH_NOT_FOUND"
    SCAN_INVALID_STRUCTURE = "SCAN_INVALID_STRUCTURE"
    SCAN_LABEL_MISMATCH = "SCAN_LABEL_MISMATCH"
    SCAN_EMPTY = "SCAN_EMPTY"

    SAMPLE_MAPPING_NOT_FOUND = "SAMPLE_MAPPING_NOT_FOUND"
    SAMPLE_INVALID_CONFIG = "SAMPLE_INVALID_CONFIG"
    SAMPLE_XML_CONVERT = "SAMPLE_XML_CONVERT"
    SAMPLE_IO = "SAMPLE_IO"

    LABELIMG_PYTHON_NOT_FOUND = "LABELIMG_PYTHON_NOT_FOUND"
    LABELIMG_NOT_INSTALLED = "LABELIMG_NOT_INSTALLED"
    LABELIMG_LAUNCH_DISABLED = "LABELIMG_LAUNCH_DISABLED"
    LABELIMG_LAUNCH = "LABELIMG_LAUNCH"

    TRAIN_DATA_YAML_INVALID = "TRAIN_DATA_YAML_INVALID"
    TRAIN_BASE_MODEL_NOT_FOUND = "TRAIN_BASE_MODEL_NOT_FOUND"
    TRAIN_DEVICE_UNAVAILABLE = "TRAIN_DEVICE_UNAVAILABLE"
    TRAIN_OOM = "TRAIN_OOM"
    TRAIN_INTERRUPTED = "TRAIN_INTERRUPTED"

    INFER_MODEL_NOT_FOUND = "INFER_MODEL_NOT_FOUND"
    INFER_MODEL_LOAD = "INFER_MODEL_LOAD"
    INFER_IMAGE_NOT_FOUND = "INFER_IMAGE_NOT_FOUND"
    INFER_DEVICE_UNAVAILABLE = "INFER_DEVICE_UNAVAILABLE"

    INSPECTOR_RUN_NOT_FOUND = "INSPECTOR_RUN_NOT_FOUND"
    INSPECTOR_PRODUCT_NOT_FOUND = "INSPECTOR_PRODUCT_NOT_FOUND"
    INSPECTOR_MAPPING_NOT_FOUND = "INSPECTOR_MAPPING_NOT_FOUND"
    INSPECTOR_CLASSES_NOT_FOUND = "INSPECTOR_CLASSES_NOT_FOUND"
    INSPECTOR_ORIGINAL_IMAGE_MISSING = "INSPECTOR_ORIGINAL_IMAGE_MISSING"

    RESTORE_SOURCE_NOT_FOUND = "RESTORE_SOURCE_NOT_FOUND"
    RESTORE_MAPPING_NOT_FOUND = "RESTORE_MAPPING_NOT_FOUND"
    RESTORE_INVALID_SOURCE_TYPE = "RESTORE_INVALID_SOURCE_TYPE"

    CONVERT_FOLDER_NOT_FOUND = "CONVERT_FOLDER_NOT_FOUND"
    CONVERT_CLASSES_NOT_FOUND = "CONVERT_CLASSES_NOT_FOUND"
    CONVERT_CLASS_ID_OUT_OF_RANGE = "CONVERT_CLASS_ID_OUT_OF_RANGE"
    CONVERT_XML_PARSE = "CONVERT_XML_PARSE"


@dataclass(frozen=True)
class ErrorInfo:
    """Serializable error payload used by task handles and API responses."""

    code: str
    message: str
    details: str | None
    retryable: bool


class AutoLabelerError(Exception):
    """Base class for all AutoLabeler business exceptions."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    retryable: bool = False

    def __init__(
        self,
        message: str,
        details: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        """Create a business exception with stable error metadata.

        Args:
            message: Human-readable error message.
            details: Optional diagnostic details for logs or debugging.
            retryable: Optional override for the class-level retryable flag.
        """
        super().__init__(message)
        self.message = message
        self.details = details
        if retryable is not None:
            self.retryable = retryable

    def __str__(self) -> str:
        """Return a compact diagnostic string."""
        text = f"[{self.code.value}] {self.message}"
        if self.details:
            text += f" ({self.details})"
        return text

    def to_error_info(self) -> ErrorInfo:
        """Convert this exception to a serializable error payload."""
        return ErrorInfo(
            code=self.code.value,
            message=self.message,
            details=self.details,
            retryable=self.retryable,
        )


class ValidationError(AutoLabelerError):
    """Raised when input validation fails."""

    code = ErrorCode.VALIDATION_ERROR


class PathNotFoundError(AutoLabelerError):
    """Raised when a required filesystem path does not exist."""

    code = ErrorCode.PATH_NOT_FOUND


class PermissionDeniedError(AutoLabelerError):
    """Raised when a filesystem operation lacks permission."""

    code = ErrorCode.PERMISSION_DENIED


class InternalError(AutoLabelerError):
    """Raised for uncategorized internal failures."""

    code = ErrorCode.INTERNAL_ERROR


class TaskNotFoundError(AutoLabelerError):
    """Raised when a task id does not exist."""

    code = ErrorCode.TASK_NOT_FOUND


class TaskAlreadyRunningError(AutoLabelerError):
    """Raised when a mutually exclusive task is already running."""

    code = ErrorCode.TASK_ALREADY_RUNNING


class TaskCancelledError(AutoLabelerError):
    """Raised when a task is cancelled by the user."""

    code = ErrorCode.TASK_CANCELLED
