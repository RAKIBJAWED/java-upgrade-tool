"""
Local Java Runner for cloud deployment (without Docker).

This module provides Java execution using local JDK installations
when Docker is not available (e.g., in App Runner, Lambda).
"""

import os
import subprocess
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional

from core.models import ExecutionResult


class LocalJavaRunner:
    """
    Java runner that uses local JDK installations instead of Docker.
    
    This is used in cloud environments where Docker-in-Docker is not available.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.java_versions = {
            8: os.environ.get('JAVA_8_HOME', '/usr/lib/jvm/java-8-openjdk-amd64'),
            17: os.environ.get('JAVA_17_HOME', '/usr/lib/jvm/java-17-openjdk-amd64'),
            21: os.environ.get('JAVA_21_HOME', '/usr/lib/jvm/java-21-openjdk-amd64'),
        }
        self.workspace_dir = Path("/tmp/java-workspace")
        self.workspace_dir.mkdir(exist_ok=True)
    
    def run_java_code(self, code: str, java_version: int) -> ExecutionResult:
        """
        Run Java code using local JDK installation.
        
        Args:
            code: Java source code to execute
            java_version: Java version to use (8, 17, 21)
            
        Returns:
            ExecutionResult with execution details
        """
        start_time = time.time()
        
        try:
            # Validate Java version
            if java_version not in self.java_versions:
                return ExecutionResult(
                    success=False,
                    compile_error=f"Unsupported Java version: {java_version}",
                    runtime_error=None,
                    stdout="",
                    stderr="",
                    execution_time=0.0,
                    java_version=java_version,
                    exit_code=-1
                )
            
            # Get Java home for the specified version
            java_home = self.java_versions[java_version]
            if not os.path.exists(java_home):
                return ExecutionResult(
                    success=False,
                    compile_error=f"Java {java_version} not installed at {java_home}",
                    runtime_error=None,
                    stdout="",
                    stderr="",
                    execution_time=0.0,
                    java_version=java_version,
                    exit_code=-1
                )
            
            # Extract class name
            class_name = self._extract_class_name(code)
            
            # Create temporary workspace
            with tempfile.TemporaryDirectory(dir=self.workspace_dir) as temp_dir:
                temp_path = Path(temp_dir)
                java_file = temp_path / f"{class_name}.java"
                
                # Write Java code to file
                java_file.write_text(code)
                
                # Set up environment
                env = os.environ.copy()
                env['JAVA_HOME'] = java_home
                env['PATH'] = f"{java_home}/bin:{env.get('PATH', '')}"
                
                # Compile Java code
                compile_result = self._run_command(
                    ["javac", str(java_file)],
                    cwd=temp_path,
                    env=env,
                    timeout=30
                )
                
                if compile_result['exit_code'] != 0:
                    execution_time = time.time() - start_time
                    return ExecutionResult(
                        success=False,
                        compile_error=compile_result['stderr'] or compile_result['stdout'],
                        runtime_error=None,
                        stdout=compile_result['stdout'],
                        stderr=compile_result['stderr'],
                        execution_time=execution_time,
                        java_version=java_version,
                        exit_code=compile_result['exit_code']
                    )
                
                # Execute Java code
                execute_result = self._run_command(
                    ["java", class_name],
                    cwd=temp_path,
                    env=env,
                    timeout=30
                )
                
                execution_time = time.time() - start_time
                success = execute_result['exit_code'] == 0
                
                return ExecutionResult(
                    success=success,
                    compile_error=None,
                    runtime_error=execute_result['stderr'] if not success else None,
                    stdout=execute_result['stdout'],
                    stderr=execute_result['stderr'],
                    execution_time=execution_time,
                    java_version=java_version,
                    exit_code=execute_result['exit_code']
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Java execution failed: {e}")
            return ExecutionResult(
                success=False,
                compile_error=None,
                runtime_error=f"Execution failed: {str(e)}",
                stdout="",
                stderr="",
                execution_time=execution_time,
                java_version=java_version,
                exit_code=-1
            )
    
    def _extract_class_name(self, code: str) -> str:
        """Extract the main class name from Java code."""
        import re
        
        # Look for public class declaration
        public_class_match = re.search(r'public\s+class\s+(\w+)', code)
        if public_class_match:
            return public_class_match.group(1)
        
        # Look for any class declaration
        class_match = re.search(r'class\s+(\w+)', code)
        if class_match:
            return class_match.group(1)
        
        # Default class name
        return "Main"
    
    def _run_command(self, command, cwd=None, env=None, timeout=30):
        """Run a command and return the result."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                'exit_code': -1,
                'stdout': "",
                'stderr': f"Command timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                'exit_code': -1,
                'stdout': "",
                'stderr': f"Command execution failed: {str(e)}"
            }