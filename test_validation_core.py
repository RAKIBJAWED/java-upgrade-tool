"""
Core unit tests for the Validation and Retry System.

This script tests the core functionality without external dependencies
like Docker or LLM APIs to verify the validation logic works correctly.
"""

import sys
import os
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.validation_system import ValidationAndRetrySystem, RetryConfiguration, ValidationResult
from core.models import ExecutionResult, CompatibilityAnalysis, SystemStatus, FixAttempt


def create_mock_components():
    """Create mock components for testing."""
    # Mock JavaRunner
    java_runner = Mock()
    java_runner.compile_and_run.return_value = ExecutionResult(
        success=True,
        compile_error=None,
        runtime_error=None,
        stdout="Hello, World!",
        stderr="",
        execution_time=0.5,
        java_version=8
    )
    
    # Mock ErrorClassifier
    error_classifier = Mock()
    error_classifier.analyze_error.return_value = CompatibilityAnalysis(
        is_version_issue=True,
        detected_features=["var"],
        required_version=10,
        error_category="version_compatibility",
        confidence_score=0.95
    )
    
    # Mock LLMAgent
    llm_agent = Mock()
    llm_agent.fix_code.return_value = Mock(
        success=True,
        content="public class Test { public static void main(String[] args) { System.out.println(\"Fixed!\"); } }",
        error_message=None
    )
    llm_agent.get_current_model.return_value = "Claude-3-haiku"
    llm_agent.check_target_version_compatibility.return_value = {
        'is_compatible': True,
        'required_version': 8,
        'target_version': 8,
        'detected_features': [],
        'incompatible_features': []
    }
    
    return java_runner, error_classifier, llm_agent


def test_retry_configuration():
    """Test RetryConfiguration dataclass."""
    print("Testing RetryConfiguration...")
    
    # Test default configuration
    config = RetryConfiguration()
    assert config.max_attempts == 2
    assert config.validate_fixes == True
    assert config.track_attempts == True
    assert config.require_execution_success == True
    
    # Test custom configuration
    custom_config = RetryConfiguration(
        max_attempts=3,
        validate_fixes=False,
        track_attempts=False,
        require_execution_success=False
    )
    assert custom_config.max_attempts == 3
    assert custom_config.validate_fixes == False
    
    print("✅ RetryConfiguration test passed")
    return True


def test_validation_result():
    """Test ValidationResult dataclass."""
    print("Testing ValidationResult...")
    
    # Test successful validation
    result = ValidationResult(
        is_valid=True,
        validation_type="execution",
        details={"test": "data"},
        error_message=None
    )
    
    assert result.is_valid == True
    assert result.validation_type == "execution"
    assert result.details["test"] == "data"
    assert result.error_message is None
    
    # Test failed validation
    failed_result = ValidationResult(
        is_valid=False,
        validation_type="compilation",
        error_message="Compilation failed"
    )
    
    assert failed_result.is_valid == False
    assert failed_result.error_message == "Compilation failed"
    
    print("✅ ValidationResult test passed")
    return True


def test_validation_system_initialization():
    """Test ValidationAndRetrySystem initialization."""
    print("Testing ValidationAndRetrySystem initialization...")
    
    java_runner, error_classifier, llm_agent = create_mock_components()
    
    retry_config = RetryConfiguration(max_attempts=3)
    
    validation_system = ValidationAndRetrySystem(
        java_runner=java_runner,
        error_classifier=error_classifier,
        llm_agent=llm_agent,
        retry_config=retry_config
    )
    
    assert validation_system.java_runner == java_runner
    assert validation_system.error_classifier == error_classifier
    assert validation_system.llm_agent == llm_agent
    assert validation_system.retry_config.max_attempts == 3
    assert validation_system.current_attempt == 0
    assert len(validation_system.fix_attempts) == 0
    
    print("✅ ValidationAndRetrySystem initialization test passed")
    return True


def test_successful_code_processing():
    """Test processing code that executes successfully."""
    print("Testing successful code processing...")
    
    java_runner, error_classifier, llm_agent = create_mock_components()
    
    # Mock successful execution
    java_runner.compile_and_run.return_value = ExecutionResult(
        success=True,
        compile_error=None,
        runtime_error=None,
        stdout="Hello, World!",
        stderr="",
        execution_time=0.5,
        java_version=8
    )
    
    validation_system = ValidationAndRetrySystem(
        java_runner=java_runner,
        error_classifier=error_classifier,
        llm_agent=llm_agent
    )
    
    response = validation_system.process_code_with_validation(
        "public class Test { public static void main(String[] args) { System.out.println(\"Hello!\"); } }",
        8
    )
    
    assert response.status == SystemStatus.SUCCESS
    assert response.fixed_code is None
    assert response.total_fix_attempts == 0
    assert response.runtime_output == "Hello, World!"
    
    print("✅ Successful code processing test passed")
    return True


def test_failed_code_with_non_version_issue():
    """Test processing code that fails with non-version issues."""
    print("Testing failed code with non-version issue...")
    
    java_runner, error_classifier, llm_agent = create_mock_components()
    
    # Mock failed execution
    java_runner.compile_and_run.return_value = ExecutionResult(
        success=False,
        compile_error="Syntax error",
        runtime_error=None,
        stdout="",
        stderr="",
        execution_time=0.0,
        java_version=8
    )
    
    # Mock non-version issue
    error_classifier.analyze_error.return_value = CompatibilityAnalysis(
        is_version_issue=False,
        detected_features=[],
        required_version=None,
        error_category="syntax_error",
        confidence_score=0.85
    )
    
    validation_system = ValidationAndRetrySystem(
        java_runner=java_runner,
        error_classifier=error_classifier,
        llm_agent=llm_agent
    )
    
    response = validation_system.process_code_with_validation(
        "public class Test { // missing brace",
        8
    )
    
    assert response.status == SystemStatus.FAILED
    assert response.fixed_code is None
    assert response.total_fix_attempts == 0
    assert response.compile_error == "Syntax error"
    
    print("✅ Failed code with non-version issue test passed")
    return True


def test_fix_attempt_tracking():
    """Test that fix attempts are tracked correctly."""
    print("Testing fix attempt tracking...")
    
    java_runner, error_classifier, llm_agent = create_mock_components()
    
    # Mock failed original execution
    java_runner.compile_and_run.side_effect = [
        # Original execution fails
        ExecutionResult(
            success=False,
            compile_error="var not supported",
            runtime_error=None,
            stdout="",
            stderr="",
            execution_time=0.0,
            java_version=8
        ),
        # First fix attempt fails
        ExecutionResult(
            success=False,
            compile_error="Still has issues",
            runtime_error=None,
            stdout="",
            stderr="",
            execution_time=0.0,
            java_version=8
        ),
        # Second fix attempt succeeds
        ExecutionResult(
            success=True,
            compile_error=None,
            runtime_error=None,
            stdout="Fixed output",
            stderr="",
            execution_time=0.3,
            java_version=8
        )
    ]
    
    validation_system = ValidationAndRetrySystem(
        java_runner=java_runner,
        error_classifier=error_classifier,
        llm_agent=llm_agent
    )
    
    response = validation_system.process_code_with_validation(
        "public class Test { public static void main(String[] args) { var x = 5; } }",
        8
    )
    
    # Should have tracked 2 attempts
    assert len(response.execution_attempts) == 2
    assert response.total_fix_attempts == 2
    
    # Check attempt details
    first_attempt = response.execution_attempts[0]
    assert first_attempt.attempt_number == 1
    assert first_attempt.execution_result.success == False
    assert first_attempt.llm_model_used == "Claude-3-haiku"
    
    second_attempt = response.execution_attempts[1]
    assert second_attempt.attempt_number == 2
    assert second_attempt.execution_result.success == True
    
    print("✅ Fix attempt tracking test passed")
    return True


def test_retry_limit_enforcement():
    """Test that retry limits are enforced."""
    print("Testing retry limit enforcement...")
    
    java_runner, error_classifier, llm_agent = create_mock_components()
    
    # Mock all executions fail
    java_runner.compile_and_run.return_value = ExecutionResult(
        success=False,
        compile_error="Always fails",
        runtime_error=None,
        stdout="",
        stderr="",
        execution_time=0.0,
        java_version=8
    )
    
    retry_config = RetryConfiguration(max_attempts=2)
    validation_system = ValidationAndRetrySystem(
        java_runner=java_runner,
        error_classifier=error_classifier,
        llm_agent=llm_agent,
        retry_config=retry_config
    )
    
    response = validation_system.process_code_with_validation(
        "public class Test { var x = 5; }",
        8
    )
    
    # Should have attempted exactly max_attempts times
    assert response.total_fix_attempts == 2
    assert len(response.execution_attempts) == 2
    assert response.status == SystemStatus.FAILED
    
    print("✅ Retry limit enforcement test passed")
    return True


def test_attempt_summary():
    """Test attempt summary functionality."""
    print("Testing attempt summary...")
    
    java_runner, error_classifier, llm_agent = create_mock_components()
    
    validation_system = ValidationAndRetrySystem(
        java_runner=java_runner,
        error_classifier=error_classifier,
        llm_agent=llm_agent
    )
    
    # Manually add some attempts for testing
    validation_system.fix_attempts = [
        FixAttempt(
            attempt_number=1,
            original_code="test",
            fixed_code="fixed",
            execution_result=ExecutionResult(
                success=False, compile_error="error", runtime_error=None,
                stdout="", stderr="", execution_time=0.0, java_version=8
            ),
            fix_strategy="test_strategy",
            timestamp=datetime.now(),
            llm_model_used="test_model"
        )
    ]
    validation_system.current_attempt = 1
    
    summary = validation_system.get_attempt_summary()
    
    assert summary['total_attempts'] == 1
    assert summary['successful_attempts'] == 0
    assert summary['failed_attempts'] == 1
    assert summary['current_attempt'] == 1
    assert summary['max_attempts'] == 2
    assert summary['attempts_remaining'] == 1
    assert 'test_strategy' in summary['fix_strategies_used']
    assert 'test_model' in summary['models_used']
    
    print("✅ Attempt summary test passed")
    return True


def test_detailed_failure_info():
    """Test detailed failure information."""
    print("Testing detailed failure info...")
    
    java_runner, error_classifier, llm_agent = create_mock_components()
    
    validation_system = ValidationAndRetrySystem(
        java_runner=java_runner,
        error_classifier=error_classifier,
        llm_agent=llm_agent
    )
    
    # Manually add failed attempts
    validation_system.fix_attempts = [
        FixAttempt(
            attempt_number=1,
            original_code="test",
            fixed_code="fixed1",
            execution_result=ExecutionResult(
                success=False, compile_error="compilation error", runtime_error=None,
                stdout="", stderr="", execution_time=0.0, java_version=8
            ),
            fix_strategy="strategy1",
            timestamp=datetime.now(),
            llm_model_used="model1"
        ),
        FixAttempt(
            attempt_number=2,
            original_code="test",
            fixed_code="fixed2",
            execution_result=ExecutionResult(
                success=False, compile_error=None, runtime_error="runtime error",
                stdout="", stderr="", execution_time=0.0, java_version=8
            ),
            fix_strategy="strategy2",
            timestamp=datetime.now(),
            llm_model_used="model2"
        )
    ]
    
    failure_info = validation_system.get_detailed_failure_info()
    
    assert failure_info['total_failures'] == 2
    assert 'strategy1' in failure_info['failure_patterns']
    assert 'strategy2' in failure_info['failure_patterns']
    assert 'compilation' in failure_info['error_categories']
    assert 'runtime' in failure_info['error_categories']
    assert failure_info['last_failure']['attempt_number'] == 2
    
    print("✅ Detailed failure info test passed")
    return True


def run_all_tests():
    """Run all core validation tests."""
    print("Starting core validation system tests...\n")
    
    tests = [
        ("RetryConfiguration", test_retry_configuration),
        ("ValidationResult", test_validation_result),
        ("ValidationSystem Initialization", test_validation_system_initialization),
        ("Successful Code Processing", test_successful_code_processing),
        ("Failed Code with Non-Version Issue", test_failed_code_with_non_version_issue),
        ("Fix Attempt Tracking", test_fix_attempt_tracking),
        ("Retry Limit Enforcement", test_retry_limit_enforcement),
        ("Attempt Summary", test_attempt_summary),
        ("Detailed Failure Info", test_detailed_failure_info)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"--- Running {test_name} Test ---")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name} test PASSED\n")
        except Exception as e:
            print(f"❌ {test_name} test FAILED: {e}\n")
            results.append((test_name, False))
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All core validation tests passed!")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)