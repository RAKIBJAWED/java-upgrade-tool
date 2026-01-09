#!/usr/bin/env python3
"""
Debug script to check what should be displayed in the UI.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner
from core.validation_system import ValidationAndRetrySystem, RetryConfiguration
from core.error_classifier import ErrorClassifier
from agent.llm_agent import JavaFixAgent
from core.models import SystemStatus

def debug_ui_output():
    """Debug what the UI should display."""
    
    # Simple test code
    test_code = '''public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from UI test!");
        System.out.println("Line 2 output");
    }
}'''
    
    print("Debugging UI Output Display")
    print("=" * 50)
    
    try:
        # Simulate what happens in the UI
        java_runner = JavaRunner()
        error_classifier = ErrorClassifier()
        llm_agent = JavaFixAgent()
        
        retry_config = RetryConfiguration(
            max_attempts=2,
            validate_fixes=True,
            track_attempts=True,
            require_execution_success=True
        )
        
        validation_system = ValidationAndRetrySystem(
            java_runner=java_runner,
            error_classifier=error_classifier,
            llm_agent=llm_agent,
            retry_config=retry_config
        )
        
        # This is what happens when user clicks "Run Java Code"
        print("🔄 Simulating UI execution...")
        system_response = validation_system.process_code_with_migration(
            original_code=test_code,
            source_version=8,
            target_version=17
        )
        
        print(f"\n📊 System Response Analysis:")
        print(f"Status: {system_response.status}")
        print(f"Status Type: {type(system_response.status)}")
        print(f"Is SUCCESS: {system_response.status == SystemStatus.SUCCESS}")
        print(f"Runtime Output: '{system_response.runtime_output}'")
        print(f"Runtime Output Length: {len(system_response.runtime_output) if system_response.runtime_output else 0}")
        print(f"Source Execution Result: {system_response.source_execution_result is not None}")
        
        if system_response.source_execution_result:
            print(f"Source STDOUT: '{system_response.source_execution_result.stdout}'")
            print(f"Source Success: {system_response.source_execution_result.success}")
        
        print(f"Execution Attempts: {len(system_response.execution_attempts)}")
        print(f"Total Fix Attempts: {system_response.total_fix_attempts}")
        
        # Simulate the UI logic for Program Output tab
        print(f"\n🖥️ UI Display Logic Simulation:")
        output_content = ""
        output_status = "info"
        
        if system_response.status == SystemStatus.SUCCESS:
            output_content = system_response.runtime_output
            output_status = "success"
            print(f"✅ SUCCESS path: output_content = '{output_content}'")
        elif system_response.status == SystemStatus.FIXED:
            print("🔧 FIXED path")
            if system_response.execution_attempts:
                for attempt in reversed(system_response.execution_attempts):
                    if attempt.execution_result.success and attempt.execution_result.stdout:
                        output_content = attempt.execution_result.stdout
                        output_status = "success"
                        print(f"Found successful attempt output: '{output_content}'")
                        break
            if not output_content:
                output_content = system_response.runtime_output
                output_status = "success" if output_content else "info"
                print(f"Fallback to runtime_output: '{output_content}'")
        else:
            print(f"❌ Other status: {system_response.status}")
        
        print(f"\nFinal UI Display:")
        print(f"Output Content: '{output_content}'")
        print(f"Output Status: {output_status}")
        print(f"Will Show Output: {bool(output_content)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_ui_output()
    print(f"\n{'✅ Debug completed!' if success else '❌ Debug failed!'}")
    sys.exit(0 if success else 1)