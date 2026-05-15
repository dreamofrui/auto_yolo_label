"""Tests for shared exception infrastructure."""

from __future__ import annotations

from utils.exceptions import (
    AutoLabelerError,
    ErrorCode,
    ErrorInfo,
    InternalError,
    PathNotFoundError,
    PermissionDeniedError,
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskNotFoundError,
    ValidationError,
)


def test_auto_labeler_error_keeps_message_details_and_retryable() -> None:
    """AutoLabelerError exposes a stable API for GUI handlers."""
    error = AutoLabelerError(
        "处理失败",
        details="stack trace",
        retryable=True,
    )

    assert error.code == ErrorCode.INTERNAL_ERROR
    assert error.message == "处理失败"
    assert error.details == "stack trace"
    assert error.retryable is True
    assert str(error) == "[INTERNAL_ERROR] 处理失败 (stack trace)"


def test_to_error_info_returns_plain_dataclass() -> None:
    """Business errors can be converted to serializable error payloads."""
    error = ValidationError("参数错误")

    info = error.to_error_info()

    assert info == ErrorInfo(
        code="VALIDATION_ERROR",
        message="参数错误",
        details=None,
        retryable=False,
    )


def test_common_subclasses_define_required_error_codes() -> None:
    """Shared exceptions map to the common and task error codes."""
    cases = [
        (ValidationError, ErrorCode.VALIDATION_ERROR),
        (PathNotFoundError, ErrorCode.PATH_NOT_FOUND),
        (PermissionDeniedError, ErrorCode.PERMISSION_DENIED),
        (InternalError, ErrorCode.INTERNAL_ERROR),
        (TaskNotFoundError, ErrorCode.TASK_NOT_FOUND),
        (TaskAlreadyRunningError, ErrorCode.TASK_ALREADY_RUNNING),
        (TaskCancelledError, ErrorCode.TASK_CANCELLED),
    ]

    for exc_type, expected_code in cases:
        error = exc_type("message")
        assert isinstance(error, AutoLabelerError)
        assert error.code == expected_code


def test_error_code_contains_all_requirement_codes() -> None:
    """ErrorCode is the shared registry for current requirement codes."""
    expected = {
        "VALIDATION_ERROR",
        "PATH_NOT_FOUND",
        "PERMISSION_DENIED",
        "INTERNAL_ERROR",
        "TASK_NOT_FOUND",
        "TASK_ALREADY_RUNNING",
        "TASK_CANCELLED",
        "SCAN_PATH_NOT_FOUND",
        "SCAN_INVALID_STRUCTURE",
        "SCAN_LABEL_MISMATCH",
        "SCAN_EMPTY",
        "SAMPLE_MAPPING_NOT_FOUND",
        "SAMPLE_INVALID_CONFIG",
        "SAMPLE_XML_CONVERT",
        "SAMPLE_IO",
        "LABELIMG_PYTHON_NOT_FOUND",
        "LABELIMG_NOT_INSTALLED",
        "LABELIMG_LAUNCH_DISABLED",
        "LABELIMG_LAUNCH",
        "TRAIN_DATA_YAML_INVALID",
        "TRAIN_BASE_MODEL_NOT_FOUND",
        "TRAIN_DEVICE_UNAVAILABLE",
        "TRAIN_OOM",
        "TRAIN_INTERRUPTED",
        "INFER_MODEL_NOT_FOUND",
        "INFER_MODEL_LOAD",
        "INFER_IMAGE_NOT_FOUND",
        "INFER_DEVICE_UNAVAILABLE",
        "INSPECTOR_RUN_NOT_FOUND",
        "INSPECTOR_PRODUCT_NOT_FOUND",
        "RESTORE_SOURCE_NOT_FOUND",
        "RESTORE_MAPPING_NOT_FOUND",
        "RESTORE_INVALID_SOURCE_TYPE",
        "CONVERT_FOLDER_NOT_FOUND",
        "CONVERT_CLASSES_NOT_FOUND",
        "CONVERT_CLASS_ID_OUT_OF_RANGE",
        "CONVERT_XML_PARSE",
    }

    assert expected <= {code.value for code in ErrorCode}
