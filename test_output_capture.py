#!/usr/bin/env python3
"""
Test output capture to debug UI display issues.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner
from core.validation_system import ValidationAndRetrySystem, RetryConfiguration
from core.error_classifier import ErrorClassifier
from agent.llm_agent import JavaFixAgent

def test_output_capture():
    """Test that output is properly captured and returned."""
    
    # Simple test code that should produce clear output
    test_code = '''public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World from Java!");
        System.out.println("This is line 2");
        System.out.println("This is line 3");
    }
}'''
    
    print("Testing Output Capture")
    print("=" * 50)
    
    try:
        # Test JavaRunner directly
        java_runner = JavaRunner()
        print("✅ JavaRunner initialized")
        
        print("\n🔄 Testing direct JavaRunner...")
        result = java_runner.compile_and_run(test_code, 8)
        
        print(f"Success: {result.success}")
        print(f"Exit Code: {result.exit_code}")
        print(f"STDOUT Length: {len(result.stdout)}")
        print(f"STDOUT Content: '{result.stdout}'")
        print(f"STDERR Length: {len(result.stderr)}")
        print(f"STDERR Content: '{result.stderr}'")
        
        # Test migration method
        print("\n🔄 Testing migration method...")
        source_result, target_result = java_runner.compile_and_run_with_migration(test_code, 8, 17)
        
        print(f"Source Success: {source_result.success}")
        print(f"Source STDOUT: '{source_result.stdout}'")
        print(f"Target Success: {target_result.success}")
        print(f"Target STDOUT: '{target_result.stdout}'")
        
        # Test ValidationAndRetrySystem
        print("\n🔄 Testing ValidationAndRetrySystem...")
        try:
            error_classifier = ErrorClassifier()
            llm_agent = JavaFixAgent()
            
            retry_config = RetryConfiguration(
                max_attempts=1,
                validate_fixes=False,
                track_attempts=True,
                require_execution_success=True
            )
            
            validation_system = ValidationAndRetrySystem(
                java_runner=java_runner,
                error_classifier=error_classifier,
                llm_agent=llm_agent,
                retry_config=retry_config
            )
            
            system_response = validation_system.process_code_with_migration(
                original_code=test_code,
                source_version=8,
                target_version=17
            )
            
            print(f"System Status: {system_response.status}")
            print(f"Runtime Output: '{system_response.runtime_output}'")
            print(f"Source Execution Result: {system_response.source_execution_result}")
            if system_response.source_execution_result:
                print(f"Source STDOUT: '{system_response.source_execution_result.stdout}'")
            
        except Exception as e:
            print(f"ValidationAndRetrySystem test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_output_capture()
    print(f"\n{'✅ Test completed!' if success else '❌ Test failed!'}")
    sys.exit(0 if success else 1)