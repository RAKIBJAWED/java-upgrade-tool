"""
Java Runner for compiling and executing Java code.

This module provides the JavaRunner class that serves as the main interface
for compiling and executing Java code using the Docker Manager.
Enhanced with comprehensive error handling and graceful degradation.
"""

import re
import logging
from typing import Optional

from core.models import ExecutionResult, JavaCode
from utils.docker_manager import DockerManager, DockerExecutionError
from core.error_handling import (
    ErrorHandler, ErrorCategory, ErrorSeverity, GracefulDegradation, 
    handle_docker_error, get_error_handler
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JavaRunner:
    """
    Main interface for Java code compilation and execution.
    
    This class provides high-level methods for validating, compiling, and executing
    Java code using Docker containers for security and isolation.
    Enhanced with comprehensive error handling and graceful degradation.
    """
    
    def __init__(self):
        """Initialize JavaRunner with DockerManager and error handling."""
        self.error_handler = get_error_handler()
        self.graceful_degradation = GracefulDegradation(self.error_handler)
        
        # Initialize Docker Manager with error handling
        try:
            self.docker_manager = DockerManager()
        except Exception as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.DOCKER_ERROR,
                severity=ErrorSeverity.HIGH,
                component="JavaRunner",
                operation="initialize",
                user_message="Docker service initialization failed. Code execution will be disabled.",
                recovery_suggestions=[
                    "Ensure Docker is installed and running",
                    "Check Docker permissions",
                    "Restart Docker service"
                ]
            )
            self.docker_manager = None
        
        # Register fallback strategies
        self._register_fallback_strategies()
    
    def _register_fallback_strategies(self):
        """Register fallback strategies for Java execution."""
        self.graceful_degradation.register_fallback(
            "java_execution",
            self._fallback_java_execution
        )
    
    def _fallback_java_execution(self, code: str, java_version: int) -> ExecutionResult:
        """Fallback strategy when Docker is not available."""
        return ExecutionResult(
            success=False,
            compile_error=None,
            runtime_error="Java execution is not available. Docker service is required but not accessible.",
            stdout="",
            stderr="",
            execution_time=0.0,
            java_version=java_version,
            exit_code=-1
        )
    
    def compile_and_run_with_migration(self, code: str, source_version: int, target_version: int) -> tuple[ExecutionResult, ExecutionResult]:
        """
        Test Java code with both source and target versions for migration scenarios.
        
        Args:
            code: Java source code to test
            source_version: Source Java version (should succeed)
            target_version: Target Java version (may fail and need fixing)
            
        Returns:
            tuple: (source_result, target_result) - ExecutionResult for each version
        """
        logger.info(f"Testing code migration from Java {source_version} to Java {target_version}")
        
        # Test with source version first
        logger.info(f"Testing with source version Java {source_version}")
        source_result = self.compile_and_run(code, source_version)
        source_result.source_version = source_version
        
        # Test with target version
        logger.info(f"Testing with target version Java {target_version}")
        target_result = self.compile_and_run(code, target_version)
        target_result.source_version = source_version
        
        # Log migration test results
        if source_result.success and target_result.success:
            logger.info("Code works in both source and target versions")
        elif source_result.success and not target_result.success:
            logger.info("Code works in source version but fails in target version - migration needed")
        elif not source_result.success and target_result.success:
            logger.warning("Code fails in source version but works in target version - unexpected")
        else:
            logger.warning("Code fails in both source and target versions")
        
        return source_result, target_result

    def compile_and_run(self, code: str, java_version: int) -> ExecutionResult:
        """
        Compile and execute Java code in the specified Java version with comprehensive error handling.
        
        Args:
            code: Java source code to compile and execute
            java_version: Target Java version (8, 11, 17, or 21)
            
        Returns:
            ExecutionResult: Complete execution results including compilation and runtime info
            
        Raises:
            ValueError: If code is empty or Java version is not supported
        """
        # Input validation with error handling
        try:
            if not code or not code.strip():
                raise ValueError("Java code cannot be empty")
            
            if java_version not in [8, 11, 17, 21]:
                raise ValueError(f"Unsupported Java version: {java_version}")
        except ValueError as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.USER_INPUT_ERROR,
                severity=ErrorSeverity.LOW,
                component="JavaRunner",
                operation="compile_and_run",
                user_message=str(e)
            )
            return ExecutionResult(
                success=False,
                compile_error=str(e),
                runtime_error=None,
                stdout="",
                stderr="",
                execution_time=0.0,
                java_version=java_version,
                exit_code=-1
            )
        
        # Validate Java syntax before attempting execution
        if not self.validate_java_syntax(code):
            error_msg = "Invalid Java syntax: code appears to be malformed"
            self.error_handler.handle_error(
                exception=ValueError(error_msg),
                category=ErrorCategory.VALIDATION_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component="JavaRunner",
                operation="validate_syntax",
                user_message=error_msg,
                recovery_suggestions=[
                    "Check Java code syntax",
                    "Ensure all braces are balanced",
                    "Verify class declarations are correct"
                ]
            )
            return ExecutionResult(
                success=False,
                compile_error=error_msg,
                runtime_error=None,
                stdout="",
                stderr="",
                execution_time=0.0,
                java_version=java_version,
                exit_code=-1
            )
        
        # Use graceful degradation for Java execution
        if self.docker_manager is None:
            return self._fallback_java_execution(code, java_version)
        
        return self.graceful_degradation.execute_with_fallback(
            "java_execution",
            self._execute_with_docker,
            code,
            java_version
        )
    
    def _execute_with_docker(self, code: str, java_version: int) -> ExecutionResult:
        """Execute Java code using Docker with comprehensive error handling."""
        logger.info(f"Compiling and running Java code with Java {java_version}")
        
        try:
            result = self.docker_manager.run_java_code(code, java_version)
            
            # Log execution summary
            if result.success:
                logger.info(f"Java execution successful in {result.execution_time:.2f}s")
            else:
                if result.has_compilation_error():
                    logger.warning("Java compilation failed")
                elif result.has_runtime_error():
                    logger.warning("Java runtime error occurred")
                else:
                    logger.warning("Java execution failed for unknown reason")
            
            return result
            
        except DockerExecutionError as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.DOCKER_ERROR,
                severity=ErrorSeverity.HIGH,
                component="JavaRunner",
                operation="execute_with_docker",
                user_message="Docker execution failed. Please ensure Docker is running and accessible.",
                recovery_suggestions=[
                    "Check Docker service status",
                    "Restart Docker if needed",
                    "Verify Docker permissions"
                ]
            )
            return ExecutionResult(
                success=False,
                compile_error=None,
                runtime_error=f"Docker execution failed: {str(e)}",
                stdout="",
                stderr="",
                execution_time=0.0,
                java_version=java_version,
                exit_code=-1
            )
        except Exception as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component="JavaRunner",
                operation="execute_with_docker",
                user_message="Unexpected error during Java code execution."
            )
            return ExecutionResult(
                success=False,
                compile_error=None,
                runtime_error=f"Execution error: {str(e)}",
                stdout="",
                stderr="",
                execution_time=0.0,
                java_version=java_version,
                exit_code=-1
            )
    
    def validate_java_syntax(self, code: str) -> bool:
        """
        Perform basic Java syntax validation.
        
        Args:
            code: Java source code to validate
            
        Returns:
            bool: True if code appears to have valid Java syntax, False otherwise
        """
        if not code or not code.strip():
            return False
        
        # Basic syntax checks
        try:
            # Check for balanced braces
            if not self._check_balanced_braces(code):
                return False
            
            # Check for at least one class declaration
            if not self._has_class_declaration(code):
                return False
            
            # Check for basic Java structure
            if not self._has_basic_java_structure(code):
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Syntax validation error: {e}")
            return False
    
    def extract_class_name(self, code: str) -> str:
        """
        Extract the main public class name from Java code.
        
        Args:
            code: Java source code
            
        Returns:
            str: Main class name, defaults to "Main" if not found
        """
        # Look for public class declaration
        public_class_pattern = r'public\s+class\s+(\w+)'
        match = re.search(public_class_pattern, code)
        
        if match:
            return match.group(1)
        
        # Look for any class declaration
        class_pattern = r'class\s+(\w+)'
        match = re.search(class_pattern, code)
        
        if match:
            return match.group(1)
        
        # Default class name
        return "Main"
    
    def create_java_code_object(self, code: str) -> JavaCode:
        """
        Create a JavaCode object with extracted metadata.
        
        Args:
            code: Java source code
            
        Returns:
            JavaCode: JavaCode object with extracted metadata
        """
        class_name = self.extract_class_name(code)
        package_name = self._extract_package_name(code)
        imports = self._extract_imports(code)
        
        return JavaCode(
            content=code,
            class_name=class_name,
            package_name=package_name,
            imports=imports
        )
    
    def _check_balanced_braces(self, code: str) -> bool:
        """Check if braces are balanced in the code."""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        # Remove string literals and comments to avoid false positives
        cleaned_code = self._remove_strings_and_comments(code)
        
        for char in cleaned_code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack.pop()] != char:
                    return False
        
        return len(stack) == 0
    
    def _has_class_declaration(self, code: str) -> bool:
        """Check if code contains at least one class declaration."""
        class_pattern = r'\bclass\s+\w+'
        return bool(re.search(class_pattern, code))
    
    def _has_basic_java_structure(self, code: str) -> bool:
        """Check if code has basic Java structure."""
        # Should have at least one of: class, interface, enum
        structure_pattern = r'\b(class|interface|enum)\s+\w+'
        return bool(re.search(structure_pattern, code))
    
    def _extract_package_name(self, code: str) -> Optional[str]:
        """Extract package name from Java code."""
        package_pattern = r'package\s+([\w.]+)\s*;'
        match = re.search(package_pattern, code)
        return match.group(1) if match else None
    
    def _extract_imports(self, code: str) -> list[str]:
        """Extract import statements from Java code."""
        import_pattern = r'import\s+([\w.*]+)\s*;'
        matches = re.findall(import_pattern, code)
        return matches
    
    def _remove_strings_and_comments(self, code: str) -> str:
        """Remove string literals and comments from code for syntax checking."""
        # This is a simplified implementation
        # Remove single-line comments
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        
        # Remove multi-line comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        
        # Remove string literals (simplified - doesn't handle escaped quotes)
        code = re.sub(r'"[^"]*"', '""', code)
        code = re.sub(r"'[^']*'", "''", code)
        
        return code
    
    def cleanup(self) -> None:
        """Clean up resources used by JavaRunner."""
        if self.docker_manager:
            self.docker_manager.cleanup_containers()
    
    def __del__(self):
        """Cleanup when JavaRunner is destroyed."""
        try:
            self.cleanup()
        except:
            pass  # Ignore cleanup errors during destruction