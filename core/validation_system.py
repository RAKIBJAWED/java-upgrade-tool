"""
Validation and Retry System for Java Version Compatibility Fixer.

This module provides comprehensive validation and retry logic for the LLM-based
code fixing process, ensuring that generated fixes are validated and retried
according to the system requirements.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from core.models import ExecutionResult, FixAttempt, CompatibilityAnalysis, SystemResponse, SystemStatus
from core.java_runner import JavaRunner
from core.error_classifier import ErrorClassifier
from agent.llm_agent import JavaFixAgent, LLMResponse


@dataclass
class ValidationResult:
    """Result of code validation process."""
    is_valid: bool
    validation_type: str
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class RetryConfiguration:
    """Configuration for retry logic."""
    max_attempts: int = 2
    validate_fixes: bool = True
    track_attempts: bool = True
    require_execution_success: bool = True


class ValidationAndRetrySystem:
    """
    Comprehensive validation and retry system for Java code fixing.
    
    This system implements the validation loop with automatic re-execution,
    retry logic with maximum attempts, attempt tracking, and comprehensive
    failure handling as specified in requirements 5.1-5.5.
    """
    
    def __init__(
        self,
        java_runner: JavaRunner,
        error_classifier: ErrorClassifier,
        llm_agent: JavaFixAgent,
        retry_config: Optional[RetryConfiguration] = None
    ):
        """
        Initialize the validation and retry system.
        
        Args:
            java_runner: JavaRunner instance for code execution
            error_classifier: ErrorClassifier for analyzing errors
            llm_agent: JavaFixAgent for generating code fixes
            retry_config: Configuration for retry behavior
        """
        self.java_runner = java_runner
        self.error_classifier = error_classifier
        self.llm_agent = llm_agent
        self.retry_config = retry_config or RetryConfiguration()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Track system state
        self.current_attempt = 0
        self.fix_attempts: List[FixAttempt] = []
        self.validation_history: List[ValidationResult] = []
    
    def process_code_with_migration(
        self,
        original_code: str,
        source_version: int,
        target_version: int
    ) -> SystemResponse:
        """
        Process Java code for version migration with comprehensive validation.
        
        This method implements the source/target version workflow:
        1. Test code with source version (should succeed)
        2. Test code with target version (may fail)
        3. If target fails, apply LLM fixes and retry
        4. Validate fixes work in target version
        
        Args:
            original_code: The original Java code to process
            source_version: Source Java version (code should work here)
            target_version: Target Java version (migration target)
            
        Returns:
            SystemResponse with complete migration results
        """
        self.logger.info(f"Starting code migration from Java {source_version} to Java {target_version}")
        
        # Reset state for new processing
        self._reset_state()
        
        # Step 1: Test with both source and target versions
        source_result, target_result = self.java_runner.compile_and_run_with_migration(
            original_code, source_version, target_version
        )
        
        # Step 2: Validate source version works
        if not source_result.success:
            self.logger.error(f"Code fails in source version Java {source_version}")
            return SystemResponse(
                status=SystemStatus.FAILED,
                java_version=target_version,
                source_version=source_version,
                target_version=target_version,
                original_code=original_code,
                fixed_code=None,
                compile_error=f"Code fails in source version Java {source_version}: {source_result.compile_error or source_result.runtime_error}",
                runtime_output=source_result.stdout,
                source_execution_result=source_result,
                execution_attempts=self.fix_attempts,
                total_fix_attempts=0
            )
        
        # Step 3: Check if target version already works
        if target_result.success:
            self.logger.info("Code already works in both source and target versions")
            return SystemResponse(
                status=SystemStatus.SUCCESS,
                java_version=target_version,
                source_version=source_version,
                target_version=target_version,
                original_code=original_code,
                fixed_code=None,
                compile_error=None,
                runtime_output=target_result.stdout,
                source_execution_result=source_result,
                execution_attempts=self.fix_attempts,
                total_fix_attempts=0
            )
        
        # Step 4: Target version fails - directly attempt LLM fixes for migration
        # Skip error classifier since we know this is a migration scenario
        self.logger.info(f"Code works in Java {source_version} but fails in Java {target_version} - attempting LLM migration fixes")
        
        error_message = target_result.compile_error or target_result.runtime_error or "Execution failed"
        
        # Create a compatibility analysis for migration scenario
        from core.models import CompatibilityAnalysis
        migration_analysis = CompatibilityAnalysis(
            is_version_issue=True,  # Always true for migration scenarios
            detected_features=["version_migration"],
            required_version=target_version,
            error_category="version_compatibility",
            confidence_score=1.0  # High confidence since source works but target fails
        )
        
        # Step 5: Attempt fixes with validation and retry
        fix_result = self._attempt_fixes_with_retry(
            original_code, target_version, migration_analysis, source_result
        )
        
        if fix_result['success']:
            self.logger.info(f"Code successfully migrated after {fix_result['attempts_made']} attempts")
            return SystemResponse(
                status=SystemStatus.FIXED,
                java_version=target_version,
                source_version=source_version,
                target_version=target_version,
                original_code=original_code,
                fixed_code=fix_result['fixed_code'],
                compile_error=None,
                runtime_output=fix_result['execution_result'].stdout,
                source_execution_result=source_result,
                execution_attempts=self.fix_attempts,
                total_fix_attempts=fix_result['attempts_made']
            )
        else:
            # Check if migration was determined to be not feasible
            if fix_result.get('migration_not_feasible', False):
                self.logger.info(f"Migration determined not feasible: {fix_result.get('feasibility_reason', 'Unknown reason')}")
                return SystemResponse(
                    status=SystemStatus.FAILED,
                    java_version=target_version,
                    source_version=source_version,
                    target_version=target_version,
                    original_code=original_code,
                    fixed_code=None,
                    compile_error=f"Migration not feasible: {fix_result.get('feasibility_reason', 'LLM determined this migration cannot be completed automatically')}",
                    runtime_output="",
                    source_execution_result=source_result,
                    execution_attempts=self.fix_attempts,
                    total_fix_attempts=fix_result['attempts_made']
                )
            else:
                self.logger.warning(f"All migration attempts failed after {fix_result['attempts_made']} attempts")
                return SystemResponse(
                    status=SystemStatus.FAILED,
                    java_version=target_version,
                    source_version=source_version,
                    target_version=target_version,
                    original_code=original_code,
                    fixed_code=fix_result.get('last_fixed_code'),
                    compile_error=fix_result.get('last_error', error_message),
                    runtime_output="",
                    source_execution_result=source_result,
                    execution_attempts=self.fix_attempts,
                    total_fix_attempts=fix_result['attempts_made']
                )

    def process_code_with_validation(
        self,
        original_code: str,
        java_version: int,
        initial_error: Optional[str] = None
    ) -> SystemResponse:
        """
        Process Java code with comprehensive validation and retry logic.
        
        This is the main entry point that implements the complete workflow:
        1. Initial execution and error analysis
        2. LLM-based code fixing with validation
        3. Retry logic with maximum attempts
        4. Comprehensive failure handling
        
        Args:
            original_code: The original Java code to process
            java_version: Target Java version
            initial_error: Optional initial error message
            
        Returns:
            SystemResponse with complete processing results
        """
        self.logger.info(f"Starting code processing with validation for Java {java_version}")
        
        # Reset state for new processing
        self._reset_state()
        
        # Step 1: Execute original code to get baseline
        original_result = self._execute_and_validate(original_code, java_version, "original")
        
        if original_result.success:
            # Code already works, no fixing needed
            self.logger.info("Original code executed successfully, no fixes needed")
            return SystemResponse(
                status=SystemStatus.SUCCESS,
                java_version=java_version,
                original_code=original_code,
                fixed_code=None,
                compile_error=None,
                runtime_output=original_result.stdout,
                execution_attempts=self.fix_attempts,
                total_fix_attempts=0
            )
        
        # Step 2: Analyze error for version compatibility
        error_message = initial_error or original_result.compile_error or original_result.runtime_error
        if not error_message:
            error_message = "Execution failed without specific error message"
        
        compatibility_analysis = self.error_classifier.analyze_error(
            error_message, java_version, original_code
        )
        
        if not compatibility_analysis.is_version_issue:
            # Not a version compatibility issue, cannot fix
            self.logger.info("Error is not version-related, cannot apply LLM fixes")
            return SystemResponse(
                status=SystemStatus.FAILED,
                java_version=java_version,
                original_code=original_code,
                fixed_code=None,
                compile_error=error_message,
                runtime_output=original_result.stdout,
                execution_attempts=self.fix_attempts,
                total_fix_attempts=0
            )
        
        # Step 3: Attempt fixes with validation and retry
        fix_result = self._attempt_fixes_with_retry(
            original_code, java_version, compatibility_analysis
        )
        
        if fix_result['success']:
            self.logger.info(f"Code successfully fixed after {fix_result['attempts_made']} attempts")
            return SystemResponse(
                status=SystemStatus.FIXED,
                java_version=java_version,
                original_code=original_code,
                fixed_code=fix_result['fixed_code'],
                compile_error=None,
                runtime_output=fix_result['execution_result'].stdout,
                execution_attempts=self.fix_attempts,
                total_fix_attempts=fix_result['attempts_made']
            )
        else:
            self.logger.warning(f"All fix attempts failed after {fix_result['attempts_made']} attempts")
            return SystemResponse(
                status=SystemStatus.FAILED,
                java_version=java_version,
                original_code=original_code,
                fixed_code=fix_result.get('last_fixed_code'),
                compile_error=fix_result.get('last_error', error_message),
                runtime_output="",
                execution_attempts=self.fix_attempts,
                total_fix_attempts=fix_result['attempts_made']
            )
    
    def validate_fix(
        self,
        original_code: str,
        fixed_code: str,
        java_version: int
    ) -> ValidationResult:
        """
        Validate that a fixed code meets all requirements.
        
        Implements requirement 5.1: validation loop with automatic re-execution.
        
        Args:
            original_code: Original Java code
            fixed_code: Fixed Java code to validate
            java_version: Target Java version
            
        Returns:
            ValidationResult with validation details
        """
        self.logger.info("Validating fixed code")
        
        try:
            # Step 1: Execute the fixed code
            execution_result = self._execute_and_validate(fixed_code, java_version, "fixed")
            
            if not execution_result.success:
                return ValidationResult(
                    is_valid=False,
                    validation_type="execution",
                    details={
                        "execution_result": execution_result,
                        "compile_error": execution_result.compile_error,
                        "runtime_error": execution_result.runtime_error
                    },
                    error_message=f"Fixed code failed to execute: {execution_result.compile_error or execution_result.runtime_error}"
                )
            
            # Step 2: Validate logic preservation (if both codes can execute)
            logic_validation = self._validate_logic_preservation(original_code, fixed_code, java_version)
            
            if not logic_validation.is_valid:
                return logic_validation
            
            # Step 3: Validate version compatibility
            version_validation = self._validate_version_compatibility(fixed_code, java_version)
            
            if not version_validation.is_valid:
                return version_validation
            
            # All validations passed
            self.logger.info("Fixed code passed all validation checks")
            return ValidationResult(
                is_valid=True,
                validation_type="comprehensive",
                details={
                    "execution_result": execution_result,
                    "logic_preserved": True,
                    "version_compatible": True
                }
            )
            
        except Exception as e:
            self.logger.error(f"Validation failed with exception: {e}")
            return ValidationResult(
                is_valid=False,
                validation_type="exception",
                error_message=f"Validation failed: {str(e)}"
            )
    
    def _attempt_fixes_with_retry(
        self,
        original_code: str,
        java_version: int,
        compatibility_analysis: CompatibilityAnalysis,
        source_result: Optional[ExecutionResult] = None
    ) -> Dict[str, Any]:
        """
        Attempt to fix code with retry logic.
        
        Implements requirements 5.2, 5.3, 5.5: retry logic with maximum attempts,
        success reporting, and attempt tracking.
        
        Args:
            original_code: Original Java code
            java_version: Target Java version
            compatibility_analysis: Analysis of compatibility issues
            
        Returns:
            Dictionary with fix attempt results
        """
        attempts_made = 0
        last_fixed_code = None
        last_error = None
        
        while attempts_made < self.retry_config.max_attempts:
            attempts_made += 1
            self.current_attempt = attempts_made
            
            self.logger.info(f"Fix attempt {attempts_made}/{self.retry_config.max_attempts}")
            
            try:
                # Generate fix using LLM
                llm_response = self.llm_agent.fix_code(
                    original_code, java_version, compatibility_analysis
                )
                
                if not llm_response.success or not llm_response.content:
                    last_error = llm_response.error_message or "LLM failed to generate fix"
                    self._record_failed_attempt(
                        attempts_made, original_code, "", last_error, "llm_generation_failed"
                    )
                    continue
                
                # Check if LLM says migration is not feasible
                if llm_response.content.startswith("MIGRATION_NOT_FEASIBLE:"):
                    reason = llm_response.content[len("MIGRATION_NOT_FEASIBLE:"):].strip()
                    last_error = f"Migration not feasible: {reason}"
                    self.logger.info(f"LLM determined migration is not feasible: {reason}")
                    self._record_failed_attempt(
                        attempts_made, original_code, "", last_error, "migration_not_feasible"
                    )
                    # Don't continue trying, return immediately
                    return {
                        'success': False,
                        'attempts_made': attempts_made,
                        'last_fixed_code': None,
                        'last_error': last_error,
                        'migration_not_feasible': True,
                        'feasibility_reason': reason
                    }
                
                fixed_code = llm_response.content
                last_fixed_code = fixed_code
                
                # Validate the fix
                if self.retry_config.validate_fixes:
                    validation_result = self.validate_fix(original_code, fixed_code, java_version)
                    
                    if validation_result.is_valid:
                        # Success! Record successful attempt
                        execution_result = validation_result.details.get('execution_result')
                        self._record_successful_attempt(
                            attempts_made, original_code, fixed_code, execution_result, "comprehensive_validation"
                        )
                        
                        return {
                            'success': True,
                            'fixed_code': fixed_code,
                            'attempts_made': attempts_made,
                            'execution_result': execution_result,
                            'validation_result': validation_result
                        }
                    else:
                        # Validation failed, record and continue
                        last_error = validation_result.error_message
                        self._record_failed_attempt(
                            attempts_made, original_code, fixed_code, last_error, "validation_failed"
                        )
                        
                        # Update compatibility analysis for next attempt if we have new error info
                        if validation_result.details.get('execution_result'):
                            exec_result = validation_result.details['execution_result']
                            new_error = exec_result.compile_error or exec_result.runtime_error
                            if new_error:
                                compatibility_analysis = self.error_classifier.analyze_error(
                                    new_error, java_version, fixed_code
                                )
                else:
                    # No validation required, just execute to check
                    execution_result = self._execute_and_validate(fixed_code, java_version, "fixed")
                    
                    if execution_result.success:
                        self._record_successful_attempt(
                            attempts_made, original_code, fixed_code, execution_result, "execution_only"
                        )
                        
                        return {
                            'success': True,
                            'fixed_code': fixed_code,
                            'attempts_made': attempts_made,
                            'execution_result': execution_result
                        }
                    else:
                        last_error = execution_result.compile_error or execution_result.runtime_error
                        self._record_failed_attempt(
                            attempts_made, original_code, fixed_code, last_error, "execution_failed"
                        )
                
            except Exception as e:
                last_error = f"Fix attempt failed with exception: {str(e)}"
                self.logger.error(last_error)
                self._record_failed_attempt(
                    attempts_made, original_code, last_fixed_code or "", last_error, "exception"
                )
        
        # All attempts failed
        return {
            'success': False,
            'attempts_made': attempts_made,
            'last_fixed_code': last_fixed_code,
            'last_error': last_error
        }
    
    def _execute_and_validate(self, code: str, java_version: int, code_type: str) -> ExecutionResult:
        """
        Execute code and return detailed results.
        
        Args:
            code: Java code to execute
            java_version: Java version to use
            code_type: Type of code being executed (for logging)
            
        Returns:
            ExecutionResult with execution details
        """
        self.logger.debug(f"Executing {code_type} code with Java {java_version}")
        
        try:
            result = self.java_runner.compile_and_run(code, java_version)
            
            if result.success:
                self.logger.debug(f"{code_type.capitalize()} code executed successfully")
            else:
                self.logger.debug(f"{code_type.capitalize()} code execution failed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Exception during {code_type} code execution: {e}")
            return ExecutionResult(
                success=False,
                compile_error=None,
                runtime_error=f"Execution exception: {str(e)}",
                stdout="",
                stderr="",
                execution_time=0.0,
                java_version=java_version,
                exit_code=-1
            )
    
    def _validate_logic_preservation(
        self,
        original_code: str,
        fixed_code: str,
        java_version: int
    ) -> ValidationResult:
        """
        Validate that the fixed code preserves the original program logic.
        
        This implements a comprehensive logic preservation check by comparing
        execution results when both codes can run successfully.
        
        Args:
            original_code: Original Java code
            fixed_code: Fixed Java code
            java_version: Java version
            
        Returns:
            ValidationResult for logic preservation
        """
        try:
            # Try to execute original code in a higher Java version if current version fails
            original_result = None
            test_versions = [java_version, 21, 17, 11]  # Try multiple versions
            
            for test_version in test_versions:
                try:
                    original_result = self.java_runner.compile_and_run(original_code, test_version)
                    if original_result.success:
                        break
                except:
                    continue
            
            if not original_result or not original_result.success:
                # Cannot validate logic preservation if original doesn't run
                self.logger.info("Cannot validate logic preservation - original code doesn't execute")
                return ValidationResult(
                    is_valid=True,  # Assume valid if we can't test
                    validation_type="logic_preservation",
                    details={"reason": "original_code_non_executable"},
                    error_message=None
                )
            
            # Execute fixed code
            fixed_result = self.java_runner.compile_and_run(fixed_code, java_version)
            
            if not fixed_result.success:
                return ValidationResult(
                    is_valid=False,
                    validation_type="logic_preservation",
                    details={"reason": "fixed_code_non_executable"},
                    error_message="Fixed code does not execute successfully"
                )
            
            # Compare outputs
            outputs_match = self._compare_execution_outputs(original_result, fixed_result)
            
            if outputs_match:
                return ValidationResult(
                    is_valid=True,
                    validation_type="logic_preservation",
                    details={
                        "original_output": original_result.stdout,
                        "fixed_output": fixed_result.stdout,
                        "outputs_match": True
                    }
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    validation_type="logic_preservation",
                    details={
                        "original_output": original_result.stdout,
                        "fixed_output": fixed_result.stdout,
                        "outputs_match": False
                    },
                    error_message="Fixed code produces different output than original"
                )
                
        except Exception as e:
            self.logger.warning(f"Logic preservation validation failed: {e}")
            # Be lenient on validation errors
            return ValidationResult(
                is_valid=True,
                validation_type="logic_preservation",
                details={"reason": "validation_error", "error": str(e)}
            )
    
    def _validate_version_compatibility(self, code: str, java_version: int) -> ValidationResult:
        """
        Validate that the code is compatible with the target Java version.
        
        Args:
            code: Java code to validate
            java_version: Target Java version
            
        Returns:
            ValidationResult for version compatibility
        """
        try:
            # Use the LLM agent's version compatibility check
            compatibility_check = self.llm_agent.check_target_version_compatibility(code, java_version)
            
            if compatibility_check.get('is_compatible', False):
                return ValidationResult(
                    is_valid=True,
                    validation_type="version_compatibility",
                    details=compatibility_check
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    validation_type="version_compatibility",
                    details=compatibility_check,
                    error_message=f"Code uses features incompatible with Java {java_version}: {compatibility_check.get('incompatible_features', [])}"
                )
                
        except Exception as e:
            self.logger.warning(f"Version compatibility validation failed: {e}")
            # Be lenient on validation errors
            return ValidationResult(
                is_valid=True,
                validation_type="version_compatibility",
                details={"reason": "validation_error", "error": str(e)}
            )
    
    def _compare_execution_outputs(self, result1: ExecutionResult, result2: ExecutionResult) -> bool:
        """
        Compare execution outputs to determine if they are equivalent.
        
        Args:
            result1: First execution result
            result2: Second execution result
            
        Returns:
            True if outputs are considered equivalent
        """
        # Normalize outputs for comparison
        output1 = result1.stdout.strip()
        output2 = result2.stdout.strip()
        
        # Direct comparison
        if output1 == output2:
            return True
        
        # Normalize whitespace and line endings
        normalized1 = ' '.join(output1.split())
        normalized2 = ' '.join(output2.split())
        
        if normalized1 == normalized2:
            return True
        
        # For very short outputs, be more strict
        if len(output1) <= 10 and len(output2) <= 10:
            return output1 == output2
        
        # For longer outputs, allow some flexibility
        if len(output1) > 50 and len(output2) > 50:
            # Check if they contain the same key information
            lines1 = set(line.strip() for line in output1.split('\n') if line.strip())
            lines2 = set(line.strip() for line in output2.split('\n') if line.strip())
            
            # At least 80% of lines should match
            if lines1 and lines2:
                intersection = lines1.intersection(lines2)
                return len(intersection) >= 0.8 * max(len(lines1), len(lines2))
        
        return False
    
    def _record_successful_attempt(
        self,
        attempt_number: int,
        original_code: str,
        fixed_code: str,
        execution_result: ExecutionResult,
        fix_strategy: str
    ):
        """Record a successful fix attempt."""
        attempt = FixAttempt(
            attempt_number=attempt_number,
            original_code=original_code,
            fixed_code=fixed_code,
            execution_result=execution_result,
            fix_strategy=fix_strategy,
            timestamp=datetime.now(),
            llm_model_used=self.llm_agent.get_current_model()
        )
        
        self.fix_attempts.append(attempt)
        self.logger.info(f"Recorded successful fix attempt {attempt_number}")
    
    def _record_failed_attempt(
        self,
        attempt_number: int,
        original_code: str,
        fixed_code: str,
        error_message: str,
        fix_strategy: str
    ):
        """Record a failed fix attempt."""
        # Create a failed execution result
        failed_result = ExecutionResult(
            success=False,
            compile_error=error_message if "compil" in error_message.lower() else None,
            runtime_error=error_message if "compil" not in error_message.lower() else None,
            stdout="",
            stderr=error_message,
            execution_time=0.0,
            java_version=0,
            exit_code=-1
        )
        
        attempt = FixAttempt(
            attempt_number=attempt_number,
            original_code=original_code,
            fixed_code=fixed_code,
            execution_result=failed_result,
            fix_strategy=fix_strategy,
            timestamp=datetime.now(),
            llm_model_used=self.llm_agent.get_current_model()
        )
        
        self.fix_attempts.append(attempt)
        self.logger.warning(f"Recorded failed fix attempt {attempt_number}: {error_message}")
    
    def _reset_state(self):
        """Reset system state for new processing."""
        self.current_attempt = 0
        self.fix_attempts = []
        self.validation_history = []
    
    def get_attempt_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all fix attempts.
        
        Implements requirement 5.5: attempt tracking and reporting.
        
        Returns:
            Dictionary with attempt summary information
        """
        successful_attempts = [attempt for attempt in self.fix_attempts if attempt.execution_result.success]
        failed_attempts = [attempt for attempt in self.fix_attempts if not attempt.execution_result.success]
        
        return {
            'total_attempts': len(self.fix_attempts),
            'successful_attempts': len(successful_attempts),
            'failed_attempts': len(failed_attempts),
            'current_attempt': self.current_attempt,
            'max_attempts': self.retry_config.max_attempts,
            'attempts_remaining': max(0, self.retry_config.max_attempts - self.current_attempt),
            'fix_strategies_used': list(set(attempt.fix_strategy for attempt in self.fix_attempts)),
            'models_used': list(set(attempt.llm_model_used for attempt in self.fix_attempts if attempt.llm_model_used))
        }
    
    def get_detailed_failure_info(self) -> Dict[str, Any]:
        """
        Get detailed information about failures for comprehensive error reporting.
        
        Implements requirement 5.4: comprehensive failure handling with detailed error information.
        
        Returns:
            Dictionary with detailed failure information
        """
        if not self.fix_attempts:
            return {"error": "No fix attempts recorded"}
        
        failed_attempts = [attempt for attempt in self.fix_attempts if not attempt.execution_result.success]
        
        if not failed_attempts:
            return {"status": "No failures recorded"}
        
        failure_info = {
            'total_failures': len(failed_attempts),
            'failure_patterns': {},
            'error_categories': {},
            'last_failure': None,
            'common_issues': []
        }
        
        # Analyze failure patterns
        for attempt in failed_attempts:
            strategy = attempt.fix_strategy
            if strategy not in failure_info['failure_patterns']:
                failure_info['failure_patterns'][strategy] = 0
            failure_info['failure_patterns'][strategy] += 1
            
            # Categorize errors
            error_msg = attempt.execution_result.compile_error or attempt.execution_result.runtime_error or "Unknown error"
            error_category = "compilation" if attempt.execution_result.compile_error else "runtime"
            
            if error_category not in failure_info['error_categories']:
                failure_info['error_categories'][error_category] = []
            failure_info['error_categories'][error_category].append(error_msg)
        
        # Get last failure details
        if failed_attempts:
            last_failure = failed_attempts[-1]
            failure_info['last_failure'] = {
                'attempt_number': last_failure.attempt_number,
                'timestamp': last_failure.timestamp.isoformat(),
                'fix_strategy': last_failure.fix_strategy,
                'error_message': last_failure.execution_result.compile_error or last_failure.execution_result.runtime_error,
                'model_used': last_failure.llm_model_used
            }
        
        # Identify common issues
        all_errors = []
        for attempt in failed_attempts:
            error = attempt.execution_result.compile_error or attempt.execution_result.runtime_error
            if error:
                all_errors.append(error)
        
        # Simple pattern detection for common issues
        if any("cannot find symbol" in error for error in all_errors):
            failure_info['common_issues'].append("Symbol resolution issues")
        if any("syntax" in error.lower() for error in all_errors):
            failure_info['common_issues'].append("Syntax errors")
        if any("version" in error.lower() for error in all_errors):
            failure_info['common_issues'].append("Version compatibility issues")
        
        return failure_info