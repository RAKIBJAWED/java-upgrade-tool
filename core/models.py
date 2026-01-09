"""
Data models for Java Version Compatibility Fixer.

This module contains the core data structures used throughout the application
for representing execution results, code analysis, and system responses.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Literal
from enum import Enum


@dataclass
class ExecutionResult:
    """
    Result of Java code compilation and execution.
    
    This model captures all possible outputs from running Java code in a Docker container,
    including success/failure status, compilation errors, runtime errors, and program output.
    """
    success: bool
    compile_error: Optional[str]
    runtime_error: Optional[str]
    stdout: str
    stderr: str
    execution_time: float
    java_version: int
    container_id: Optional[str] = None
    exit_code: Optional[int] = None
    timed_out: bool = False
    source_version: Optional[int] = None  # For tracking source version in migration scenarios
    
    def has_compilation_error(self) -> bool:
        """Check if execution failed due to compilation error."""
        return self.compile_error is not None and len(self.compile_error.strip()) > 0
    
    def has_runtime_error(self) -> bool:
        """Check if execution failed due to runtime error."""
        return self.runtime_error is not None and len(self.runtime_error.strip()) > 0
    
    def has_output(self) -> bool:
        """Check if execution produced any stdout output."""
        return len(self.stdout.strip()) > 0


@dataclass
class JavaCode:
    """
    Represents Java source code with metadata.
    
    This model stores Java code along with extracted metadata like class name,
    package information, and detected language features.
    """
    content: str
    class_name: str
    package_name: Optional[str] = None
    imports: List[str] = None
    detected_features: List[str] = None
    
    def __post_init__(self):
        if self.imports is None:
            self.imports = []
        if self.detected_features is None:
            self.detected_features = []


@dataclass
class CompatibilityAnalysis:
    """
    Result of analyzing code for version compatibility issues.
    
    This model represents the output of error classification and feature detection
    to determine if compilation/runtime errors are due to Java version incompatibility.
    """
    is_version_issue: bool
    detected_features: List[str]
    required_version: Optional[int]
    error_category: str
    confidence_score: float
    
    def __post_init__(self):
        if self.detected_features is None:
            self.detected_features = []


@dataclass
class FixAttempt:
    """
    Represents a single attempt to fix Java code compatibility issues.
    
    This model tracks each iteration of the LLM-based code fixing process,
    including the generated code and its execution results.
    """
    attempt_number: int
    original_code: str
    fixed_code: str
    execution_result: ExecutionResult
    fix_strategy: str
    timestamp: datetime
    llm_model_used: Optional[str] = None


class SystemStatus(Enum):
    """Enumeration of possible system response statuses."""
    SUCCESS = "success"
    FIXED = "fixed"
    FAILED = "failed"


@dataclass
class SystemResponse:
    """
    Complete system response for a Java code processing request.
    
    This model represents the final output of the entire workflow,
    including original code, any fixes applied, and execution results.
    """
    status: SystemStatus
    java_version: int
    original_code: str
    fixed_code: Optional[str]
    compile_error: Optional[str]
    runtime_output: str
    execution_attempts: List[FixAttempt]
    total_fix_attempts: int
    source_version: Optional[int] = None  # Source Java version for migration scenarios
    target_version: Optional[int] = None  # Target Java version for migration scenarios
    source_execution_result: Optional[ExecutionResult] = None  # Result from source version
    
    def __post_init__(self):
        if self.execution_attempts is None:
            self.execution_attempts = []


@dataclass
class DockerExecutionConfig:
    """
    Configuration for Docker container execution.
    
    This model encapsulates all the security and resource constraints
    that should be applied when running Java code in Docker containers.
    """
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    timeout_seconds: int = 30
    network_disabled: bool = True
    read_only: bool = True
    user_id: str = "1000:1000"
    auto_remove: bool = True
    
    def to_docker_kwargs(self) -> dict:
        """Convert to Docker SDK run() method kwargs."""
        return {
            'mem_limit': self.memory_limit,
            'nano_cpus': int(float(self.cpu_limit) * 1_000_000_000),  # Convert string to float then to nanocpus
            'network_disabled': self.network_disabled,
            'read_only': self.read_only,
            'user': self.user_id,
            'remove': False,  # We'll remove manually after getting logs
            'stdout': True,
            'stderr': True
        }