"""Core components for Java Version Compatibility Fixer."""

from .models import (
    ExecutionResult,
    JavaCode,
    CompatibilityAnalysis,
    FixAttempt,
    SystemStatus,
    SystemResponse,
    DockerExecutionConfig
)
from .version_mapper import VersionMapper, FeatureDetection
from .error_classifier import ErrorClassifier, ErrorCategory, ErrorPattern

__all__ = [
    'ExecutionResult',
    'JavaCode',
    'CompatibilityAnalysis',
    'FixAttempt',
    'SystemStatus',
    'SystemResponse',
    'DockerExecutionConfig',
    'VersionMapper',
    'FeatureDetection',
    'ErrorClassifier',
    'ErrorCategory',
    'ErrorPattern'
]