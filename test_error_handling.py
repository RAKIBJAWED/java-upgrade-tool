"""
Test suite for comprehensive error handling and resilience features.

This test suite validates the error handling, retry logic, graceful degradation,
and monitoring capabilities of the Java Version Fixer system.
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.error_handling import (
    ErrorHandler, ErrorCategory, ErrorSeverity, RetryableOperation, 
    RetryConfig, GracefulDegradation, get_error_handler
)
from core.monitoring import SystemMonitor, HealthStatus, get_system_monitor


class TestErrorHandler:
    """Test cases for the ErrorHandler class."""
    
    def test_error_handler_initialization(self):
        """Test error handler initializes correctly."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_log:
            handler = ErrorHandler(temp_log.name)
            assert handler is not None
            assert len(handler.error_history) == 0
            assert len(handler.error_counts) == 0
        
        os.unlink(temp_log.name)
    
    def test_handle_error_basic(self):
        """Test basic error handling functionality."""
        handler = ErrorHandler()
        
        test_exception = ValueError("Test error")
        error_context = handler.handle_error(
            exception=test_exception,
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            component="test_component",
            operation="test_operation"
        )
        
        assert error_context.category == ErrorCategory.VALIDATION_ERROR
        assert error_context.severity == ErrorSeverity.MEDIUM
        assert error_context.component == "test_component"
        assert error_context.operation == "test_operation"
        assert error_context.original_exception == test_exception
        assert len(handler.error_history) == 1
    
    def test_error_counting(self):
        """Test error counting functionality."""
        handler = ErrorHandler()
        
        # Generate multiple errors for the same component
        for i in range(3):
            handler.handle_error(
                exception=ValueError(f"Error {i}"),
                category=ErrorCategory.VALIDATION_ERROR,
                severity=ErrorSeverity.LOW,
                component="test_component",
                operation="test_operation"
            )
        
        error_key = "validation_error:test_component"
        assert handler.error_counts[error_key] == 3
    
    def test_user_message_generation(self):
        """Test automatic user message generation."""
        handler = ErrorHandler()
        
        # Test with ConnectionError
        conn_error = ConnectionError("Connection failed")
        error_context = handler.handle_error(
            exception=conn_error,
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.MEDIUM,
            component="test_component",
            operation="test_operation"
        )
        
        assert "network connection failed" in error_context.user_message.lower()
        assert "connection failed" in error_context.user_message
    
    def test_error_summary(self):
        """Test error summary generation."""
        handler = ErrorHandler()
        
        # Generate errors of different categories
        handler.handle_error(
            ValueError("Error 1"), ErrorCategory.VALIDATION_ERROR, 
            ErrorSeverity.LOW, "comp1", "op1"
        )
        handler.handle_error(
            ConnectionError("Error 2"), ErrorCategory.NETWORK_ERROR, 
            ErrorSeverity.MEDIUM, "comp2", "op2"
        )
        
        summary = handler.get_error_summary()
        assert summary["total_errors"] == 2
        assert "validation_error" in summary["by_category"]
        assert "network_error" in summary["by_category"]
        assert summary["by_category"]["validation_error"] == 1
        assert summary["by_category"]["network_error"] == 1


class TestRetryableOperation:
    """Test cases for the RetryableOperation class."""
    
    def test_successful_operation(self):
        """Test operation that succeeds on first try."""
        handler = ErrorHandler()
        config = RetryConfig(max_attempts=3)
        retry_op = RetryableOperation(config, handler)
        
        def successful_func():
            return "success"
        
        result = retry_op.execute(successful_func)
        assert result == "success"
    
    def test_retry_on_failure(self):
        """Test retry logic on transient failures."""
        handler = ErrorHandler()
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        retry_op = RetryableOperation(config, handler)
        
        call_count = 0
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = retry_op.execute(failing_func)
        assert result == "success"
        assert call_count == 3
    
    def test_max_attempts_exceeded(self):
        """Test behavior when max attempts are exceeded."""
        handler = ErrorHandler()
        config = RetryConfig(max_attempts=2, base_delay=0.1)
        retry_op = RetryableOperation(config, handler)
        
        def always_failing_func():
            raise ConnectionError("Persistent failure")
        
        with pytest.raises(ConnectionError):
            retry_op.execute(always_failing_func)
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        handler = ErrorHandler()
        config = RetryConfig(max_attempts=3, retryable_exceptions=[ConnectionError])
        retry_op = RetryableOperation(config, handler)
        
        call_count = 0
        def func_with_non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            retry_op.execute(func_with_non_retryable_error)
        
        assert call_count == 1  # Should not retry
    
    def test_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        handler = ErrorHandler()
        config = RetryConfig(
            max_attempts=3, 
            base_delay=1.0, 
            exponential_backoff=True,
            jitter=False
        )
        retry_op = RetryableOperation(config, handler)
        
        # Test delay calculation
        assert retry_op._calculate_delay(0) == 1.0
        assert retry_op._calculate_delay(1) == 2.0
        assert retry_op._calculate_delay(2) == 4.0
    
    def test_max_delay_limit(self):
        """Test maximum delay limit enforcement."""
        handler = ErrorHandler()
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=5.0,
            exponential_backoff=True,
            jitter=False
        )
        retry_op = RetryableOperation(config, handler)
        
        # High attempt number should be capped at max_delay
        delay = retry_op._calculate_delay(10)
        assert delay <= config.max_delay


class TestGracefulDegradation:
    """Test cases for the GracefulDegradation class."""
    
    def test_successful_primary_execution(self):
        """Test successful execution of primary function."""
        handler = ErrorHandler()
        degradation = GracefulDegradation(handler)
        
        def primary_func(x, y):
            return x + y
        
        result = degradation.execute_with_fallback(
            "test_component", primary_func, 2, 3
        )
        assert result == 5
    
    def test_fallback_execution(self):
        """Test fallback execution when primary fails."""
        handler = ErrorHandler()
        degradation = GracefulDegradation(handler)
        
        def primary_func():
            raise ConnectionError("Primary failed")
        
        def fallback_func():
            return "fallback_result"
        
        degradation.register_fallback("test_component", fallback_func)
        
        result = degradation.execute_with_fallback(
            "test_component", primary_func
        )
        assert result == "fallback_result"
    
    def test_no_fallback_available(self):
        """Test behavior when no fallback is available."""
        handler = ErrorHandler()
        degradation = GracefulDegradation(handler)
        
        def primary_func():
            raise ValueError("Primary failed")
        
        with pytest.raises(ValueError):
            degradation.execute_with_fallback("test_component", primary_func)
    
    def test_system_health_tracking(self):
        """Test system health tracking."""
        handler = ErrorHandler()
        degradation = GracefulDegradation(handler)
        
        # Successful execution should mark component as healthy
        def successful_func():
            return "success"
        
        degradation.execute_with_fallback("comp1", successful_func)
        
        # Failed execution should mark component as unhealthy
        def failing_func():
            raise ConnectionError("Failed")
        
        def fallback_func():
            return "fallback"
        
        degradation.register_fallback("comp2", fallback_func)
        degradation.execute_with_fallback("comp2", failing_func)
        
        health = degradation.get_system_health()
        assert health["component_status"]["comp1"] == True
        assert health["component_status"]["comp2"] == False
        assert health["healthy_components"] == 1
        assert health["failed_components"] == 1


class TestSystemMonitor:
    """Test cases for the SystemMonitor class."""
    
    def test_monitor_initialization(self):
        """Test system monitor initializes correctly."""
        monitor = SystemMonitor(check_interval=30)
        assert monitor.check_interval == 30
        assert len(monitor.component_health) > 0
        assert len(monitor.system_metrics) == 0
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.pids')
    def test_system_metrics_collection(self, mock_pids, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection."""
        # Mock system metrics
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(percent=60.2)
        mock_disk.return_value = Mock(used=500000000, total=1000000000)
        mock_pids.return_value = [1, 2, 3, 4, 5]
        
        monitor = SystemMonitor()
        metrics = monitor._collect_system_metrics()
        
        assert metrics.cpu_usage == 45.5
        assert metrics.memory_usage == 60.2
        assert metrics.disk_usage == 50.0  # 500MB / 1GB * 100
        assert metrics.active_processes == 5
    
    def test_health_check_execution(self):
        """Test health check execution."""
        monitor = SystemMonitor()
        
        with patch.object(monitor, '_collect_system_metrics') as mock_collect:
            mock_collect.return_value = Mock(
                cpu_usage=30.0, memory_usage=40.0, disk_usage=20.0,
                active_processes=10, docker_containers=2
            )
            
            health_report = monitor.check_system_health()
            
            assert "overall_status" in health_report
            assert "system_metrics" in health_report
            assert "component_health" in health_report
            assert "performance_metrics" in health_report
            assert "recommendations" in health_report
    
    def test_performance_tracking(self):
        """Test performance metrics tracking."""
        monitor = SystemMonitor()
        
        # Record some API calls
        monitor.record_api_call(0.5)
        monitor.record_api_call(1.0)
        monitor.record_api_call(0.8)
        
        # Record some Docker operations
        monitor.record_docker_operation(2.0)
        monitor.record_docker_operation(1.5)
        
        assert len(monitor.api_call_times) == 3
        assert len(monitor.docker_operation_times) == 2
    
    def test_health_summary(self):
        """Test health summary generation."""
        monitor = SystemMonitor()
        
        # Set some component health statuses
        monitor.component_health["comp1"].status = HealthStatus.HEALTHY
        monitor.component_health["comp2"].status = HealthStatus.DEGRADED
        
        summary = monitor.get_health_summary()
        
        assert "overall_status" in summary
        assert "healthy_components" in summary
        assert "total_components" in summary
        assert "health_percentage" in summary
        assert summary["healthy_components"] >= 1


class TestIntegration:
    """Integration tests for error handling system."""
    
    def test_error_handler_with_monitoring(self):
        """Test integration between error handler and monitoring."""
        handler = get_error_handler()
        monitor = get_system_monitor()
        
        # Generate some errors
        handler.handle_error(
            ValueError("Test error"),
            ErrorCategory.VALIDATION_ERROR,
            ErrorSeverity.MEDIUM,
            "test_component",
            "test_operation"
        )
        
        # Check that error is recorded
        assert len(handler.error_history) >= 1
        
        # Check system health
        health_report = monitor.check_system_health()
        assert health_report is not None
    
    def test_retry_with_monitoring(self):
        """Test retry operations with performance monitoring."""
        handler = get_error_handler()
        monitor = get_system_monitor()
        
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        retry_op = RetryableOperation(config, handler)
        
        call_count = 0
        def test_func():
            nonlocal call_count
            call_count += 1
            start_time = time.time()
            time.sleep(0.1)  # Simulate work
            
            # Record performance
            monitor.record_api_call(time.time() - start_time)
            
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = retry_op.execute(test_func)
        assert result == "success"
        assert len(monitor.api_call_times) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])