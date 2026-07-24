from __future__ import annotations


class CleanDropError(Exception):
    """Base error with a stable, translatable code."""

    code = "CLEANDROP_ERROR"


class ValidationError(CleanDropError):
    code = "VALIDATION_ERROR"


class UnsupportedMediaError(ValidationError):
    code = "UNSUPPORTED_MEDIA"


class ResourceLimitError(ValidationError):
    code = "RESOURCE_LIMIT"


class UnsafePathError(ValidationError):
    code = "UNSAFE_PATH"


class InspectionError(CleanDropError):
    code = "INSPECTION_FAILED"


class SanitizationError(CleanDropError):
    code = "SANITIZATION_FAILED"


class VerificationError(CleanDropError):
    code = "VERIFICATION_FAILED"


class ExternalToolError(CleanDropError):
    code = "EXTERNAL_TOOL_FAILED"


class InvalidTransitionError(CleanDropError):
    code = "INVALID_JOB_TRANSITION"


class JobCancelledError(CleanDropError):
    code = "JOB_CANCELLED"
