"""
Configuration management system for Java Version Compatibility Fixer.

This module handles loading and validation of system configuration including
Java version mappings, Docker images, and timeout settings.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    error_message: Optional[str] = None

@dataclass
class SystemConfiguration:
    """System configuration data structure."""
    java_versions: Dict[int, str]  # Java version to Docker image mapping
    execution_timeout: int  # Timeout in seconds
    docker_memory_limit: str  # Memory limit for Docker containers
    docker_cpu_limit: str  # CPU limit for Docker containers
    supported_llm_models: Dict[str, str]  # Model name to provider mapping
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

# Default configuration
DEFAULT_CONFIG = {
    "java_versions": {
        8: "openjdk:8-jdk-alpine",
        11: "openjdk:11-jdk-alpine", 
        17: "openjdk:17-jdk-alpine",
        21: "openjdk:21-jdk-alpine"
    },
    "execution_timeout": 30,
    "docker_memory_limit": "512m",
    "docker_cpu_limit": "1.0",
    "supported_llm_models": {
        "GPT-4": "openai",
        "GPT-3.5-turbo": "openai",
        "Claude-3-opus": "anthropic",
        "Claude-3-sonnet": "anthropic",
        "Claude-3-haiku": "anthropic"
    }
}

def load_configuration() -> SystemConfiguration:
    """
    Load system configuration from config file and environment variables.
    
    Returns:
        SystemConfiguration: Loaded configuration object
        
    Raises:
        FileNotFoundError: If config file is missing
        json.JSONDecodeError: If config file is invalid JSON
        ValueError: If required configuration is missing
    """
    config_path = Path("config/java_versions.json")
    
    # Load from config file if it exists, otherwise use defaults
    if config_path.exists():
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    else:
        config_data = DEFAULT_CONFIG.copy()
        # Create default config file
        config_path.parent.mkdir(exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
    
    # Load API keys from environment variables
    openai_api_key = os.getenv('OPENAI_API_KEY')
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    
    return SystemConfiguration(
        java_versions={int(k): v for k, v in config_data["java_versions"].items()},
        execution_timeout=config_data["execution_timeout"],
        docker_memory_limit=config_data["docker_memory_limit"],
        docker_cpu_limit=config_data["docker_cpu_limit"],
        supported_llm_models=config_data["supported_llm_models"],
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key
    )

def validate_configuration(config: SystemConfiguration) -> ValidationResult:
    """
    Validate system configuration for completeness and correctness.
    
    Args:
        config: Configuration object to validate
        
    Returns:
        ValidationResult: Validation result with success status and error details
    """
    # Check required Java versions
    required_versions = {8, 11, 17, 21}
    if not required_versions.issubset(set(config.java_versions.keys())):
        missing = required_versions - set(config.java_versions.keys())
        return ValidationResult(
            is_valid=False,
            error_message=f"Missing Java version mappings for: {sorted(missing)}"
        )
    
    # Validate Docker image names
    for version, image in config.java_versions.items():
        if not image or not isinstance(image, str):
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid Docker image for Java {version}: {image}"
            )
    
    # Validate timeout
    if config.execution_timeout <= 0 or config.execution_timeout > 300:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid execution timeout: {config.execution_timeout}. Must be between 1-300 seconds."
        )
    
    # Validate Docker resource limits
    if not config.docker_memory_limit or not config.docker_cpu_limit:
        return ValidationResult(
            is_valid=False,
            error_message="Docker resource limits (memory and CPU) must be specified"
        )
    
    # Validate LLM models
    if not config.supported_llm_models:
        return ValidationResult(
            is_valid=False,
            error_message="No LLM models configured"
        )
    
    # Check if at least one API key is available
    if not config.openai_api_key and not config.anthropic_api_key:
        return ValidationResult(
            is_valid=False,
            error_message="No LLM API keys found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables."
        )
    
    return ValidationResult(is_valid=True)

def get_java_image(version: int) -> str:
    """
    Get Docker image name for specified Java version.
    
    Args:
        version: Java version number
        
    Returns:
        str: Docker image name
        
    Raises:
        ValueError: If version is not supported
    """
    config = load_configuration()
    if version not in config.java_versions:
        raise ValueError(f"Unsupported Java version: {version}")
    return config.java_versions[version]

def get_execution_timeout() -> int:
    """Get configured execution timeout in seconds."""
    config = load_configuration()
    return config.execution_timeout

def get_docker_limits() -> tuple[str, str]:
    """Get Docker resource limits (memory, cpu)."""
    config = load_configuration()
    return config.docker_memory_limit, config.docker_cpu_limit