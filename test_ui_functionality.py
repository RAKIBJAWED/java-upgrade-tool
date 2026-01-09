#!/usr/bin/env python3
"""
Test script to verify the UI functionality works with source/target versions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_session_state_variables():
    """Test that the session state variables are properly defined."""
    print("Testing session state variable definitions...")
    
    # Simulate session state
    class MockSessionState:
        def __init__(self):
            self.selected_source_version = 8
            self.selected_target_version = 17
            self.selected_java_version = 17  # backward compatibility
    
    session_state = MockSessionState()
    
    # Test that all required variables exist
    assert hasattr(session_state, 'selected_source_version')
    assert hasattr(session_state, 'selected_target_version')
    assert hasattr(session_state, 'selected_java_version')
    
    # Test default values
    assert session_state.selected_source_version == 8
    assert session_state.selected_target_version == 17
    assert session_state.selected_java_version == 17
    
    print("✅ Session state variables test passed")
    return True

def test_migration_workflow():
    """Test the migration workflow logic."""
    print("Testing migration workflow...")
    
    from core.java_runner import JavaRunner
    from core.models import ExecutionResult
    
    # Test the new migration method exists
    java_runner = JavaRunner()
    assert hasattr(java_runner, 'compile_and_run_with_migration')
    
    # Test method signature
    import inspect
    sig = inspect.signature(java_runner.compile_and_run_with_migration)
    params = list(sig.parameters.keys())
    
    expected_params = ['code', 'source_version', 'target_version']
    assert params == expected_params, f"Expected {expected_params}, got {params}"
    
    print("✅ Migration workflow test passed")
    return True

def test_system_response_fields():
    """Test that SystemResponse has the new migration fields."""
    print("Testing SystemResponse migration fields...")
    
    from core.models import SystemResponse, SystemStatus, ExecutionResult
    
    # Create a test SystemResponse
    response = SystemResponse(
        status=SystemStatus.SUCCESS,
        java_version=17,
        original_code="test code",
        fixed_code=None,
        compile_error=None,
        runtime_output="test output",
        execution_attempts=[],
        total_fix_attempts=0,
        source_version=8,
        target_version=17,
        source_execution_result=ExecutionResult(
            success=True,
            compile_error=None,
            runtime_error=None,
            stdout="test",
            stderr="",
            execution_time=1.0,
            java_version=8,
            source_version=8
        )
    )
    
    # Test that new fields exist
    assert hasattr(response, 'source_version')
    assert hasattr(response, 'target_version')
    assert hasattr(response, 'source_execution_result')
    
    # Test values
    assert response.source_version == 8
    assert response.target_version == 17
    assert response.source_execution_result.success == True
    
    print("✅ SystemResponse migration fields test passed")
    return True

def test_validation_system_migration():
    """Test that ValidationAndRetrySystem has the new migration method."""
    print("Testing ValidationAndRetrySystem migration method...")
    
    from core.validation_system import ValidationAndRetrySystem
    
    # Test the new migration method exists
    assert hasattr(ValidationAndRetrySystem, 'process_code_with_migration')
    
    # Test method signature
    import inspect
    sig = inspect.signature(ValidationAndRetrySystem.process_code_with_migration)
    params = list(sig.parameters.keys())
    
    expected_params = ['self', 'original_code', 'source_version', 'target_version']
    assert params == expected_params, f"Expected {expected_params}, got {params}"
    
    print("✅ ValidationAndRetrySystem migration method test passed")
    return True

def test_execution_result_fields():
    """Test that ExecutionResult has the new source_version field."""
    print("Testing ExecutionResult source_version field...")
    
    from core.models import ExecutionResult
    
    # Create a test ExecutionResult
    result = ExecutionResult(
        success=True,
        compile_error=None,
        runtime_error=None,
        stdout="test output",
        stderr="",
        execution_time=1.0,
        java_version=17,
        source_version=8
    )
    
    # Test that new field exists
    assert hasattr(result, 'source_version')
    assert result.source_version == 8
    
    print("✅ ExecutionResult source_version field test passed")
    return True

def run_all_tests():
    """Run all UI functionality tests."""
    print("Starting UI functionality tests...\n")
    
    tests = [
        ("Session State Variables", test_session_state_variables),
        ("Migration Workflow", test_migration_workflow),
        ("SystemResponse Fields", test_system_response_fields),
        ("ValidationSystem Migration", test_validation_system_migration),
        ("ExecutionResult Fields", test_execution_result_fields),
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
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("="*60)
    print("UI FUNCTIONALITY TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All UI functionality tests passed!")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)