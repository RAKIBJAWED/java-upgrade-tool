"""
Docker Manager for secure Java code execution.

This module provides the DockerManager class that handles secure execution of Java code
in isolated Docker containers with proper resource constraints and security measures.
Enhanced with comprehensive error handling, retry logic, and graceful degradation.
"""

import docker
import tempfile
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

from core.models import ExecutionResult, DockerExecutionConfig
from config.settings import get_java_image, get_execution_timeout, get_docker_limits
from core.error_handling import (
    ErrorHandler, ErrorCategory, ErrorSeverity, RetryableOperation, 
    RetryConfig, GracefulDegradation, handle_docker_error, get_error_handler
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DockerExecutionError(Exception):
    """Exception raised when Docker execution fails."""
    pass


class DockerManager:
    """
    Manages Docker containers for secure Java code execution.
    
    This class provides methods to compile and execute Java code in isolated
    Docker containers with security constraints including memory limits,
    CPU limits, network isolation, and automatic cleanup.
    Enhanced with comprehensive error handling and graceful degradation.
    """
    
    def __init__(self):
        """Initialize Docker client and execution configuration with error handling."""
        self.error_handler = get_error_handler()
        self.client = None
        self.config = None
        self.active_containers: Dict[str, Any] = {}
        
        # Configure retry logic for Docker operations
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=10.0,
            exponential_backoff=True,
            jitter=True,
            retryable_exceptions=[docker.errors.APIError, ConnectionError, TimeoutError],
            retryable_error_categories=[ErrorCategory.DOCKER_ERROR, ErrorCategory.NETWORK_ERROR]
        )
        self.retry_operation = RetryableOperation(self.retry_config, self.error_handler)
        
        # Initialize graceful degradation
        self.graceful_degradation = GracefulDegradation(self.error_handler)
        self._register_fallback_strategies()
        
        # Initialize Docker client with error handling
        self._initialize_docker_client()
    
    def _initialize_docker_client(self) -> None:
        """Initialize Docker client with comprehensive error handling."""
        try:
            self.client = docker.from_env()
            # Test Docker connection with retry logic
            def _test_connection():
                self.client.ping()
                return True
            
            self.retry_operation.execute(_test_connection)
            logger.info("Docker client initialized successfully")
            
            # Load configuration
            memory_limit, cpu_limit = get_docker_limits()
            timeout = get_execution_timeout()
            
            self.config = DockerExecutionConfig(
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                timeout_seconds=timeout
            )
            
        except docker.errors.DockerException as e:
            error_context = self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.DOCKER_ERROR,
                severity=ErrorSeverity.CRITICAL,
                component="DockerManager",
                operation="initialize",
                user_message="Docker is not available. Please ensure Docker is installed and running.",
                recovery_suggestions=[
                    "Install Docker Desktop or Docker Engine",
                    "Start Docker service",
                    "Check Docker permissions",
                    "Verify Docker is accessible from command line"
                ]
            )
            logger.error(f"Failed to initialize Docker client: {e}")
            # Don't raise here - allow graceful degradation
            
        except Exception as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.HIGH,
                component="DockerManager",
                operation="initialize",
                user_message="System error during Docker initialization."
            )
            logger.error(f"Unexpected error during Docker initialization: {e}")
    
    def _register_fallback_strategies(self) -> None:
        """Register fallback strategies for Docker operations."""
        self.graceful_degradation.register_fallback(
            "docker_execution", 
            self._fallback_execution
        )
    
    def _fallback_execution(self, code: str, java_version: int) -> ExecutionResult:
        """Fallback execution strategy when Docker is not available."""
        return ExecutionResult(
            success=False,
            compile_error=None,
            runtime_error="Docker service is not available. Code execution is disabled.",
            stdout="",
            stderr="",
            execution_time=0.0,
            java_version=java_version,
            exit_code=-1,
            timed_out=False
        )
    
    def run_java_code(self, code: str, java_version: int) -> ExecutionResult:
        """
        Compile and execute Java code in a Docker container with comprehensive error handling.
        
        Args:
            code: Java source code to execute
            java_version: Target Java version (8, 11, 17, or 21)
            
        Returns:
            ExecutionResult: Execution results including output, errors, and metadata
        """
        if self.client is None or self.config is None:
            return self._fallback_execution(code, java_version)
        
        # Use graceful degradation for Docker execution
        return self.graceful_degradation.execute_with_fallback(
            "docker_execution",
            self._execute_java_code,
            code,
            java_version
        )
    
    def _execute_java_code(self, code: str, java_version: int) -> ExecutionResult:
        """
        Internal method to execute Java code with comprehensive error handling.
        
        Args:
            code: Java source code to execute
            java_version: Target Java version (8, 11, 17, or 21)
            
        Returns:
            ExecutionResult: Execution results including output, errors, and metadata
            
        Raises:
            DockerExecutionError: If Docker execution fails
            ValueError: If Java version is not supported
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not code or not code.strip():
                raise ValueError("Java code cannot be empty")
            
            if java_version not in [8, 11, 17, 21]:
                raise ValueError(f"Unsupported Java version: {java_version}")
            
            # Get Docker image for Java version with retry logic
            def _get_image():
                return get_java_image(java_version)
            
            image_name = self.retry_operation.execute(_get_image)
            
            # Extract class name from code
            class_name = self._extract_class_name(code)
            
            # Create temporary directory for Java files
            with self._create_temp_workspace() as temp_dir:
                # Write Java code to file
                java_file = temp_dir / f"{class_name}.java"
                java_file.write_text(code, encoding='utf-8')
                
                # Compile Java code with retry logic
                compile_result = self.retry_operation.execute(
                    self._compile_java, image_name, temp_dir, class_name
                )
                
                if not compile_result.success:
                    execution_time = time.time() - start_time
                    return ExecutionResult(
                        success=False,
                        compile_error=compile_result.compile_error,
                        runtime_error=None,
                        stdout="",
                        stderr=compile_result.stderr,
                        execution_time=execution_time,
                        java_version=java_version,
                        exit_code=compile_result.exit_code
                    )
                
                # Execute compiled Java code with retry logic
                execution_result = self.retry_operation.execute(
                    self._execute_java, image_name, temp_dir, class_name
                )
                execution_result.java_version = java_version
                execution_result.execution_time = time.time() - start_time
                
                return execution_result
                
        except ValueError as e:
            # Input validation errors
            execution_time = time.time() - start_time
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.USER_INPUT_ERROR,
                severity=ErrorSeverity.LOW,
                component="DockerManager",
                operation="run_java_code",
                user_message=str(e)
            )
            return ExecutionResult(
                success=False,
                compile_error=str(e),
                runtime_error=None,
                stdout="",
                stderr="",
                execution_time=execution_time,
                java_version=java_version
            )
            
        except docker.errors.ImageNotFound as e:
            execution_time = time.time() - start_time
            error_msg = f"Docker image not found for Java {java_version}"
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.DOCKER_ERROR,
                severity=ErrorSeverity.HIGH,
                component="DockerManager",
                operation="run_java_code",
                user_message=error_msg,
                recovery_suggestions=[
                    f"Pull the required Docker image: docker pull {get_java_image(java_version)}",
                    "Check internet connection",
                    "Verify Docker Hub access"
                ]
            )
            return ExecutionResult(
                success=False,
                compile_error=error_msg,
                runtime_error=None,
                stdout="",
                stderr="",
                execution_time=execution_time,
                java_version=java_version,
                exit_code=-1
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Docker execution error: {str(e)}"
            
            # Determine error category based on exception type
            if isinstance(e, docker.errors.APIError):
                category = ErrorCategory.DOCKER_ERROR
                severity = ErrorSeverity.HIGH
            elif isinstance(e, (ConnectionError, TimeoutError)):
                category = ErrorCategory.NETWORK_ERROR
                severity = ErrorSeverity.MEDIUM
            else:
                category = ErrorCategory.SYSTEM_ERROR
                severity = ErrorSeverity.MEDIUM
            
            self.error_handler.handle_error(
                exception=e,
                category=category,
                severity=severity,
                component="DockerManager",
                operation="run_java_code",
                user_message="Code execution failed due to system error.",
                metadata={"java_version": java_version, "class_name": self._extract_class_name(code)}
            )
            
            return ExecutionResult(
                success=False,
                compile_error=None,
                runtime_error=error_msg,
                stdout="",
                stderr="",
                execution_time=execution_time,
                java_version=java_version
            )
    
    def _extract_class_name(self, code: str) -> str:
        """
        Extract the main class name from Java code.
        
        Args:
            code: Java source code
            
        Returns:
            str: Main class name, defaults to "Main" if not found
        """
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('public class '):
                # Extract class name
                parts = line.split()
                if len(parts) >= 3:
                    class_name = parts[2]
                    # Remove any trailing characters like '{'
                    if '{' in class_name:
                        class_name = class_name.split('{')[0]
                    return class_name.strip()
        
        # Default class name if not found
        return "Main"
    
    @contextmanager
    def _create_temp_workspace(self):
        """
        Create a temporary workspace directory for Java compilation.
        
        Yields:
            Path: Temporary directory path
        """
        temp_dir = None
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="java_exec_"))
            logger.debug(f"Created temporary workspace: {temp_dir}")
            yield temp_dir
        finally:
            if temp_dir and temp_dir.exists():
                # Clean up temporary files
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.debug(f"Cleaned up temporary workspace: {temp_dir}")
    
    def _compile_java(self, image_name: str, workspace: Path, class_name: str) -> ExecutionResult:
        """
        Compile Java code in Docker container.
        
        Args:
            image_name: Docker image to use
            workspace: Workspace directory containing Java files
            class_name: Name of the Java class
            
        Returns:
            ExecutionResult: Compilation result
        """
        compile_command = f"javac {class_name}.java"
        
        return self._run_docker_command(
            image_name=image_name,
            command=compile_command,
            workspace=workspace,
            operation="compilation"
        )
    
    def _execute_java(self, image_name: str, workspace: Path, class_name: str) -> ExecutionResult:
        """
        Execute compiled Java code in Docker container.
        
        Args:
            image_name: Docker image to use
            workspace: Workspace directory containing compiled classes
            class_name: Name of the Java class to execute
            
        Returns:
            ExecutionResult: Execution result
        """
        execute_command = f"java {class_name}"
        
        return self._run_docker_command(
            image_name=image_name,
            command=execute_command,
            workspace=workspace,
            operation="execution"
        )
    
    def _run_docker_command(self, image_name: str, command: str, workspace: Path, 
                          operation: str) -> ExecutionResult:
        """
        Run a command in a Docker container with security constraints.
        
        Args:
            image_name: Docker image to use
            command: Command to execute
            workspace: Workspace directory to mount
            operation: Operation type for logging ("compilation" or "execution")
            
        Returns:
            ExecutionResult: Command execution result
        """
        container = None
        start_time = time.time()
        
        try:
            # Prepare Docker run arguments
            docker_kwargs = self.config.to_docker_kwargs()
            docker_kwargs.update({
                'image': image_name,
                'command': f"sh -c 'cd /workspace && {command}'",
                'volumes': {str(workspace): {'bind': '/workspace', 'mode': 'rw'}},
                'working_dir': '/workspace',
                'detach': True  # Run in detached mode so we can control timeout
            })
            
            logger.info(f"Starting {operation} with command: {command}")
            
            # Run container in detached mode
            container = self.client.containers.run(**docker_kwargs)
            
            # Wait for container to complete or timeout
            try:
                result = container.wait(timeout=self.config.timeout_seconds)
                if isinstance(result, dict):
                    exit_code = result.get('StatusCode', 0)
                else:
                    exit_code = result
            except Exception as e:
                logger.warning(f"Container timeout or error during {operation}: {e}")
                # Force stop the container
                try:
                    container.stop(timeout=1)
                    container.remove()
                except:
                    pass
                
                execution_time = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    compile_error=f"Timeout during {operation}" if operation == "compilation" else None,
                    runtime_error=f"Timeout during {operation}" if operation == "execution" else None,
                    stdout="",
                    stderr="",
                    execution_time=execution_time,
                    java_version=0,  # Will be set by caller
                    exit_code=-1,
                    timed_out=True
                )
            
            # Get container logs
            try:
                stdout = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
                stderr = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Failed to get container logs: {e}")
                stdout = ""
                stderr = str(e)
            
            # Clean up container
            try:
                container.remove()
            except:
                pass
            
            execution_time = time.time() - start_time
            success = exit_code == 0
            
            # Determine error type based on operation and exit code
            compile_error = None
            runtime_error = None
            
            if not success:
                if operation == "compilation":
                    compile_error = stderr if stderr else stdout
                else:
                    runtime_error = stderr if stderr else "Execution failed"
            
            logger.info(f"{operation.capitalize()} completed with exit code: {exit_code}")
            
            return ExecutionResult(
                success=success,
                compile_error=compile_error,
                runtime_error=runtime_error,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                java_version=0,  # Will be set by caller
                exit_code=exit_code,
                timed_out=False
            )
            
        except docker.errors.ImageNotFound:
            execution_time = time.time() - start_time
            error_msg = f"Docker image not found: {image_name}"
            logger.error(error_msg)
            return ExecutionResult(
                success=False,
                compile_error=error_msg if operation == "compilation" else None,
                runtime_error=error_msg if operation == "execution" else None,
                stdout="",
                stderr="",
                execution_time=execution_time,
                java_version=0,
                exit_code=-1
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Docker {operation} error: {str(e)}"
            logger.error(error_msg)
            return ExecutionResult(
                success=False,
                compile_error=error_msg if operation == "compilation" else None,
                runtime_error=error_msg if operation == "execution" else None,
                stdout="",
                stderr="",
                execution_time=execution_time,
                java_version=0,
                exit_code=-1
            )
        
        finally:
            # Cleanup container if it exists and wasn't auto-removed
            if container and not self.config.auto_remove:
                try:
                    container.remove(force=True)
                    logger.debug("Container cleaned up successfully")
                except Exception as e:
                    logger.warning(f"Failed to cleanup container: {e}")
    
    def cleanup_containers(self) -> None:
        """
        Clean up any remaining containers created by this manager.
        
        This method should be called when shutting down the application
        to ensure no containers are left running.
        """
        try:
            # Get all containers with our labels or naming pattern
            containers = self.client.containers.list(all=True)
            cleaned_count = 0
            
            for container in containers:
                try:
                    # Check if container was created by our application
                    if any('java_exec_' in mount.get('Source', '') 
                          for mount in container.attrs.get('Mounts', [])):
                        container.remove(force=True)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup container {container.id}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} containers")
                
        except Exception as e:
            logger.error(f"Error during container cleanup: {e}")
    
    def get_java_image(self, version: int) -> str:
        """
        Get Docker image name for specified Java version.
        
        Args:
            version: Java version number
            
        Returns:
            str: Docker image name
            
        Raises:
            ValueError: If version is not supported
        """
        return get_java_image(version)
    
    def pull_java_images(self) -> Dict[int, bool]:
        """
        Pull all required Java Docker images.
        
        Returns:
            Dict[int, bool]: Mapping of Java version to pull success status
        """
        results = {}
        
        for version in [8, 11, 17, 21]:
            try:
                image_name = get_java_image(version)
                logger.info(f"Pulling Docker image: {image_name}")
                self.client.images.pull(image_name)
                results[version] = True
                logger.info(f"Successfully pulled {image_name}")
            except Exception as e:
                logger.error(f"Failed to pull image for Java {version}: {e}")
                results[version] = False
        
        return results
    
    def __del__(self):
        """Cleanup when DockerManager is destroyed."""
        try:
            self.cleanup_containers()
        except:
            pass  # Ignore cleanup errors during destruction