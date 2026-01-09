"""
Comprehensive Error Handling and Resilience Module

This module provides centralized error handling, graceful degradation,
retry logic, and monitoring for the Java Version Fixer system.
"""

import logging
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Union
from functools import wraps
import json
import os
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better handling and monitoring."""
    API_ERROR = "api_error"
    DOCKER_ERROR = "docker_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RESOURCE_ERROR = "resource_error"
    SYSTEM_ERROR = "system_error"
    USER_INPUT_ERROR = "user_input_error"


@dataclass
class ErrorContext:
    """Context information for error handling and recovery."""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    component: str
    operation: str
    original_exception: Optional[Exception] = None
    user_message: str = ""
    technical_details: str = ""
    recovery_suggestions: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retryable_exceptions: List[type] = field(default_factory=list)
    retryable_error_categories: List[ErrorCategory] = field(default_factory=list)


class ErrorHandler:
    """
    Centralized error handler with comprehensive error processing,
    user-friendly messaging, and recovery strategies.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize error handler with logging configuration.
        
        Args:
            log_file: Optional log file path for error logging
        """
        self.logger = self._setup_logging(log_file)
        self.error_history: List[ErrorContext] = []
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        
        # Register default recovery strategies
        self._register_default_recovery_strategies()
    
    def _setup_logging(self, log_file: Optional[str] = None) -> logging.Logger:
        """Set up comprehensive logging for error handling."""
        logger = logging.getLogger("JavaVersionFixer.ErrorHandler")
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler for detailed logging
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.INFO)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Failed to set up file logging: {e}")
        
        return logger
    
    def handle_error(
        self,
        exception: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        component: str,
        operation: str,
        user_message: str = "",
        recovery_suggestions: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> ErrorContext:
        """
        Handle an error with comprehensive processing and logging.
        
        Args:
            exception: The original exception
            category: Error category for classification
            severity: Error severity level
            component: Component where error occurred
            operation: Operation being performed when error occurred
            user_message: User-friendly error message
            recovery_suggestions: List of recovery suggestions
            metadata: Additional metadata for error context
            
        Returns:
            ErrorContext: Processed error context
        """
        error_id = self._generate_error_id()
        
        error_context = ErrorContext(
            error_id=error_id,
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            component=component,
            operation=operation,
            original_exception=exception,
            user_message=user_message or self._generate_user_message(exception, category),
            technical_details=self._extract_technical_details(exception),
            recovery_suggestions=recovery_suggestions or self._get_recovery_suggestions(category),
            metadata=metadata or {}
        )
        
        # Log the error
        self._log_error(error_context)
        
        # Store in history
        self.error_history.append(error_context)
        
        # Update error counts
        error_key = f"{category.value}:{component}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Attempt recovery if strategy exists
        if category in self.recovery_strategies:
            try:
                self.recovery_strategies[category](error_context)
            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy failed for {category}: {recovery_error}")
        
        return error_context
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _generate_user_message(self, exception: Exception, category: ErrorCategory) -> str:
        """Generate user-friendly error message based on exception and category."""
        user_messages = {
            ErrorCategory.API_ERROR: "Unable to connect to the AI service. Please check your internet connection and API keys.",
            ErrorCategory.DOCKER_ERROR: "Docker service is not available. Please ensure Docker is running and accessible.",
            ErrorCategory.VALIDATION_ERROR: "The code validation failed. Please check your Java code for syntax errors.",
            ErrorCategory.CONFIGURATION_ERROR: "System configuration error. Please check your settings and try again.",
            ErrorCategory.NETWORK_ERROR: "Network connection failed. Please check your internet connection and try again.",
            ErrorCategory.TIMEOUT_ERROR: "The operation timed out. Please try again or check if the service is responding.",
            ErrorCategory.AUTHENTICATION_ERROR: "Authentication failed. Please check your API keys and credentials.",
            ErrorCategory.RESOURCE_ERROR: "System resources are unavailable. Please try again later.",
            ErrorCategory.SYSTEM_ERROR: "An unexpected system error occurred. Please try again or contact support.",
            ErrorCategory.USER_INPUT_ERROR: "Invalid input provided. Please check your input and try again."
        }
        
        base_message = user_messages.get(category, "An unexpected error occurred. Please try again.")
        
        # Add specific details for certain exception types
        if isinstance(exception, ConnectionError):
            return f"{base_message} Connection details: {str(exception)}"
        elif isinstance(exception, TimeoutError):
            return f"{base_message} The operation exceeded the time limit."
        elif isinstance(exception, ValueError):
            return f"{base_message} Input validation failed: {str(exception)}"
        
        return base_message
    
    def _extract_technical_details(self, exception: Exception) -> str:
        """Extract technical details from exception for logging and debugging."""
        details = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc()
        }
        
        # Add specific details for certain exception types
        if hasattr(exception, 'response'):
            details["http_status"] = getattr(exception.response, 'status_code', None)
            details["http_reason"] = getattr(exception.response, 'reason', None)
        
        if hasattr(exception, 'errno'):
            details["error_code"] = exception.errno
        
        return json.dumps(details, indent=2)
    
    def _get_recovery_suggestions(self, category: ErrorCategory) -> List[str]:
        """Get recovery suggestions based on error category."""
        suggestions = {
            ErrorCategory.API_ERROR: [
                "Check your internet connection",
                "Verify API keys are correctly configured",
                "Try again in a few minutes",
                "Check API service status"
            ],
            ErrorCategory.DOCKER_ERROR: [
                "Ensure Docker is installed and running",
                "Check Docker permissions",
                "Restart Docker service",
                "Verify Docker images are available"
            ],
            ErrorCategory.VALIDATION_ERROR: [
                "Check Java code syntax",
                "Ensure code is complete",
                "Verify Java version compatibility",
                "Review error messages for specific issues"
            ],
            ErrorCategory.CONFIGURATION_ERROR: [
                "Check configuration files",
                "Verify environment variables",
                "Reset to default configuration",
                "Contact system administrator"
            ],
            ErrorCategory.NETWORK_ERROR: [
                "Check internet connection",
                "Verify firewall settings",
                "Try again later",
                "Use different network if available"
            ],
            ErrorCategory.TIMEOUT_ERROR: [
                "Try again with simpler code",
                "Check system performance",
                "Increase timeout settings if possible",
                "Break down complex operations"
            ],
            ErrorCategory.AUTHENTICATION_ERROR: [
                "Verify API keys",
                "Check credentials expiration",
                "Regenerate API keys if needed",
                "Contact service provider"
            ],
            ErrorCategory.RESOURCE_ERROR: [
                "Free up system resources",
                "Close unnecessary applications",
                "Try again later",
                "Contact system administrator"
            ]
        }
        
        return suggestions.get(category, ["Try again later", "Contact support if problem persists"])
    
    def _log_error(self, error_context: ErrorContext) -> None:
        """Log error with appropriate level and formatting."""
        log_message = (
            f"[{error_context.error_id}] {error_context.component}.{error_context.operation} - "
            f"{error_context.category.value} ({error_context.severity.value}): "
            f"{error_context.user_message}"
        )
        
        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
            self.logger.critical(f"Technical details: {error_context.technical_details}")
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
            self.logger.error(f"Technical details: {error_context.technical_details}")
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
            self.logger.debug(f"Technical details: {error_context.technical_details}")
        else:
            self.logger.info(log_message)
            self.logger.debug(f"Technical details: {error_context.technical_details}")
    
    def _register_default_recovery_strategies(self) -> None:
        """Register default recovery strategies for different error categories."""
        self.recovery_strategies[ErrorCategory.DOCKER_ERROR] = self._recover_docker_error
        self.recovery_strategies[ErrorCategory.API_ERROR] = self._recover_api_error
        self.recovery_strategies[ErrorCategory.NETWORK_ERROR] = self._recover_network_error
    
    def _recover_docker_error(self, error_context: ErrorContext) -> None:
        """Recovery strategy for Docker errors."""
        self.logger.info(f"Attempting Docker error recovery for {error_context.error_id}")
        # Add specific Docker recovery logic here
        # For now, just log the attempt
        
    def _recover_api_error(self, error_context: ErrorContext) -> None:
        """Recovery strategy for API errors."""
        self.logger.info(f"Attempting API error recovery for {error_context.error_id}")
        # Add specific API recovery logic here
        
    def _recover_network_error(self, error_context: ErrorContext) -> None:
        """Recovery strategy for network errors."""
        self.logger.info(f"Attempting network error recovery for {error_context.error_id}")
        # Add specific network recovery logic here
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error statistics and patterns."""
        total_errors = len(self.error_history)
        if total_errors == 0:
            return {"total_errors": 0, "message": "No errors recorded"}
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        component_counts = {}
        
        for error in self.error_history:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            component_counts[error.component] = component_counts.get(error.component, 0) + 1
        
        return {
            "total_errors": total_errors,
            "by_category": category_counts,
            "by_severity": severity_counts,
            "by_component": component_counts,
            "most_recent": self.error_history[-1].timestamp.isoformat() if self.error_history else None
        }


class RetryableOperation:
    """
    Decorator and context manager for implementing retry logic with exponential backoff.
    """
    
    def __init__(self, config: RetryConfig, error_handler: ErrorHandler):
        """
        Initialize retryable operation.
        
        Args:
            config: Retry configuration
            error_handler: Error handler for logging and processing
        """
        self.config = config
        self.error_handler = error_handler
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for making functions retryable."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)
        return wrapper
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all retries failed
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self._is_retryable(e):
                    self.error_handler.logger.info(f"Exception {type(e).__name__} is not retryable")
                    raise e
                
                # Log retry attempt
                self.error_handler.logger.warning(
                    f"Attempt {attempt + 1}/{self.config.max_attempts} failed: {str(e)}"
                )
                
                # Don't sleep after the last attempt
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.error_handler.logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
        
        # All attempts failed
        self.error_handler.logger.error(f"All {self.config.max_attempts} attempts failed")
        raise last_exception
    
    def _is_retryable(self, exception: Exception) -> bool:
        """Check if exception is retryable based on configuration."""
        # Check by exception type
        if self.config.retryable_exceptions:
            if any(isinstance(exception, exc_type) for exc_type in self.config.retryable_exceptions):
                return True
        
        # Check by error category (if exception has category attribute)
        if hasattr(exception, 'error_category') and self.config.retryable_error_categories:
            if exception.error_category in self.config.retryable_error_categories:
                return True
        
        # Default retryable exceptions
        retryable_types = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
        
        # Check for specific error messages that indicate transient issues
        transient_messages = [
            "connection timeout",
            "connection reset",
            "temporary failure",
            "service unavailable",
            "rate limit",
            "too many requests"
        ]
        
        error_message = str(exception).lower()
        if any(msg in error_message for msg in transient_messages):
            return True
        
        return isinstance(exception, retryable_types)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff and jitter."""
        if self.config.exponential_backoff:
            delay = self.config.base_delay * (2 ** attempt)
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay


class GracefulDegradation:
    """
    Provides graceful degradation strategies for system components.
    """
    
    def __init__(self, error_handler: ErrorHandler):
        """
        Initialize graceful degradation handler.
        
        Args:
            error_handler: Error handler for logging and processing
        """
        self.error_handler = error_handler
        self.fallback_strategies: Dict[str, Callable] = {}
        self.component_status: Dict[str, bool] = {}
    
    def register_fallback(self, component: str, fallback_func: Callable) -> None:
        """
        Register a fallback strategy for a component.
        
        Args:
            component: Component name
            fallback_func: Fallback function to use when component fails
        """
        self.fallback_strategies[component] = fallback_func
        self.error_handler.logger.info(f"Registered fallback strategy for {component}")
    
    def execute_with_fallback(self, component: str, primary_func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with fallback strategy if primary fails.
        
        Args:
            component: Component name
            primary_func: Primary function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result from primary function or fallback
        """
        try:
            result = primary_func(*args, **kwargs)
            self.component_status[component] = True
            return result
        except Exception as e:
            self.component_status[component] = False
            
            # Log the failure
            error_context = self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component=component,
                operation="primary_execution",
                user_message=f"{component} is temporarily unavailable, using fallback mode"
            )
            
            # Try fallback if available
            if component in self.fallback_strategies:
                try:
                    self.error_handler.logger.info(f"Using fallback strategy for {component}")
                    return self.fallback_strategies[component](*args, **kwargs)
                except Exception as fallback_error:
                    self.error_handler.handle_error(
                        exception=fallback_error,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.HIGH,
                        component=component,
                        operation="fallback_execution",
                        user_message=f"Both primary and fallback strategies failed for {component}"
                    )
                    raise fallback_error
            else:
                # No fallback available
                self.error_handler.logger.error(f"No fallback strategy available for {component}")
                raise e
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        total_components = len(self.component_status)
        healthy_components = sum(1 for status in self.component_status.values() if status)
        
        health_percentage = (healthy_components / total_components * 100) if total_components > 0 else 100
        
        return {
            "overall_health": health_percentage,
            "total_components": total_components,
            "healthy_components": healthy_components,
            "failed_components": total_components - healthy_components,
            "component_status": self.component_status.copy(),
            "degraded_mode": health_percentage < 100
        }


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get or create global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        log_file = os.path.join(os.getcwd(), "logs", "java_version_fixer.log")
        _global_error_handler = ErrorHandler(log_file)
    return _global_error_handler


def handle_api_error(func: Callable) -> Callable:
    """Decorator for handling API errors with user-friendly messages."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler = get_error_handler()
            error_context = error_handler.handle_error(
                exception=e,
                category=ErrorCategory.API_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component=func.__module__,
                operation=func.__name__,
                user_message="API service is temporarily unavailable. Please try again."
            )
            # Re-raise with enhanced context
            e.error_context = error_context
            raise e
    return wrapper


def handle_docker_error(func: Callable) -> Callable:
    """Decorator for handling Docker errors with graceful degradation."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler = get_error_handler()
            error_context = error_handler.handle_error(
                exception=e,
                category=ErrorCategory.DOCKER_ERROR,
                severity=ErrorSeverity.HIGH,
                component=func.__module__,
                operation=func.__name__,
                user_message="Docker service is not available. Code execution is disabled."
            )
            # Re-raise with enhanced context
            e.error_context = error_context
            raise e
    return wrapper