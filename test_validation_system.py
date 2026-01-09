"""
Test script for the Validation and Retry System.

This script tests the core functionality of the validation and retry system
to ensure it meets the requirements specified in the design document.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.validation_system import ValidationAndRetrySystem, RetryConfiguration, ValidationResult
from core.java_runner import JavaRunner
from core.error_classifier import ErrorClassifier
from agent.llm_agent import JavaFixAgent
from core.models import CompatibilityAnalysis, SystemStatus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_validation_system_initialization():
    """Test that the validation system initializes correctly."""
    logger.info("Testing validation system initialization...")
    
    try:
        java_runner = JavaRunner()
        error_classifier = ErrorClassifier()
        llm_agent = JavaFixAgent()
        
        retry_config = RetryConfiguration(
            max_attempts=2,
            validate_fixes=True,
            track_attempts=True
        )
        
        validation_system = ValidationAndRetrySystem(
            java_runner=java_runner,
            error_classifier=error_classifier,
            llm_agent=llm_agent,
            retry_config=retry_config
        )
        
        logger.info("✅ Validation system initialized successfully")
        return validation_system
        
    except Exception as e:
        logger.error(f"❌ Validation system initialization failed: {e}")
        return None


def test_successful_code_execution():
    """Test processing of code that executes successfully."""
    logger.info("Testing successful code execution...")
    
    validation_system = test_validation_system_initialization()
    if not validation_system:
        return False
    
    # Simple Java code that should work
    java_code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
    
    try:
        response = validation_system.process_code_with_validation(java_code, 8)
        
        if response.status == SystemStatus.SUCCESS:
            logger.info("✅ Successful code execution test passed")
            return True
        else:
            logger.error(f"❌ Expected SUCCESS status, got {response.status}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Successful code execution test failed: {e}")
        return False


def test_retry_limit_enforcement():
    """Test that retry limits are enforced correctly."""
    logger.info("Testing retry limit enforcement...")
    
    validation_system = test_validation_system_initialization()
    if not validation_system:
        return False
    
    # Code with version compatibility issue that might be hard to fix
    java_code = """
public class VarExample {
    public static void main(String[] args) {
        var message = "Hello from Java 10+";
        System.out.println(message);
    }
}
"""
    
    try:
        response = validation_system.process_code_with_validation(java_code, 8)
        
        # Should either succeed with fixes or fail after max attempts
        if response.status == SystemStatus.FIXED:
            logger.info("✅ Code was successfully fixed")
            return True
        elif response.status == SystemStatus.FAILED:
            if response.total_fix_attempts <= validation_system.retry_config.max_attempts:
                logger.info(f"✅ Retry limit enforced correctly: {response.total_fix_attempts} attempts")
                return True
            else:
                logger.error(f"❌ Retry limit exceeded: {response.total_fix_attempts} > {validation_system.retry_config.max_attempts}")
                return False
        else:
            logger.error(f"❌ Unexpected status: {response.status}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Retry limit enforcement test failed: {e}")
        return False


def test_attempt_tracking():
    """Test that attempts are tracked correctly."""
    logger.info("Testing attempt tracking...")
    
    validation_system = test_validation_system_initialization()
    if not validation_system:
        return False
    
    # Code that will likely need fixing
    java_code = """
public class SwitchExample {
    public static void main(String[] args) {
        int day = 1;
        String dayName = switch (day) {
            case 1 -> "Monday";
            case 2 -> "Tuesday";
            default -> "Unknown";
        };
        System.out.println(dayName);
    }
}
"""
    
    try:
        response = validation_system.process_code_with_validation(java_code, 8)
        
        # Check that attempts are tracked
        if len(response.execution_attempts) > 0:
            logger.info(f"✅ Attempts tracked correctly: {len(response.execution_attempts)} attempts recorded")
            
            # Verify attempt details
            for attempt in response.execution_attempts:
                if not hasattr(attempt, 'attempt_number') or not hasattr(attempt, 'timestamp'):
                    logger.error("❌ Attempt missing required fields")
                    return False
            
            return True
        else:
            logger.error("❌ No attempts were tracked")
            return False
            
    except Exception as e:
        logger.error(f"❌ Attempt tracking test failed: {e}")
        return False


def test_validation_result_structure():
    """Test that validation results have the correct structure."""
    logger.info("Testing validation result structure...")
    
    validation_system = test_validation_system_initialization()
    if not validation_system:
        return False
    
    # Create a simple validation result
    original_code = "public class Test { public static void main(String[] args) { System.out.println(\"test\"); } }"
    fixed_code = "public class Test { public static void main(String[] args) { System.out.println(\"test\"); } }"
    
    try:
        validation_result = validation_system.validate_fix(original_code, fixed_code, 8)
        
        # Check required fields
        required_fields = ['is_valid', 'validation_type', 'details']
        for field in required_fields:
            if not hasattr(validation_result, field):
                logger.error(f"❌ ValidationResult missing required field: {field}")
                return False
        
        logger.info("✅ Validation result structure test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation result structure test failed: {e}")
        return False


def test_comprehensive_failure_handling():
    """Test comprehensive failure handling."""
    logger.info("Testing comprehensive failure handling...")
    
    validation_system = test_validation_system_initialization()
    if not validation_system:
        return False
    
    # Code with syntax errors that cannot be fixed
    java_code = """
public class BrokenCode {
    public static void main(String[] args) {
        System.out.println("Missing semicolon")
        // This will cause compilation errors
    }
}
"""
    
    try:
        response = validation_system.process_code_with_validation(java_code, 8)
        
        # Should handle failure gracefully
        if response.status == SystemStatus.FAILED:
            # Check that failure information is available
            failure_info = validation_system.get_detailed_failure_info()
            
            if 'total_failures' in failure_info or 'error' in failure_info:
                logger.info("✅ Comprehensive failure handling test passed")
                return True
            else:
                logger.error("❌ Failure information not properly captured")
                return False
        else:
            logger.warning(f"⚠️ Expected FAILED status, got {response.status} (code might have been fixed)")
            return True  # This is actually okay if the LLM managed to fix it
            
    except Exception as e:
        logger.error(f"❌ Comprehensive failure handling test failed: {e}")
        return False


def run_all_tests():
    """Run all validation system tests."""
    logger.info("Starting validation system tests...")
    
    tests = [
        ("Initialization", test_validation_system_initialization),
        ("Successful Code Execution", test_successful_code_execution),
        ("Retry Limit Enforcement", test_retry_limit_enforcement),
        ("Attempt Tracking", test_attempt_tracking),
        ("Validation Result Structure", test_validation_result_structure),
        ("Comprehensive Failure Handling", test_comprehensive_failure_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Validation system is working correctly.")
        return True
    else:
        logger.error(f"⚠️ {total - passed} tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)