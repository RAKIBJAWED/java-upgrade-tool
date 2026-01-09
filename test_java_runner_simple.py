#!/usr/bin/env python3
"""
Test the Java runner with a simple compatibility demo.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner

def test_simple_java_code():
    """Test running simple Java code with Java 8."""
    
    java_code = '''public class CompatibilityDemo {
    public static void main(String[] args) throws Exception {
        System.out.println("print");
    }
}'''
    
    print("Testing Java Runner with Simple Code")
    print("=" * 50)
    print(f"Code to test:\n{java_code}")
    print("=" * 50)
    
    try:
        # Initialize JavaRunner
        java_runner = JavaRunner()
        print("✅ JavaRunner initialized successfully")
        
        # Test with Java 8
        print("\n🔄 Testing with Java 8...")
        result = java_runner.compile_and_run(java_code, 8)
        
        print(f"\n📊 Results:")
        print(f"Success: {'✅ Yes' if result.success else '❌ No'}")
        print(f"Java Version: {result.java_version}")
        print(f"Execution Time: {result.execution_time:.3f}s")
        
        if result.success:
            print(f"Output: '{result.stdout.strip()}'")
        else:
            if result.compile_error:
                print(f"Compilation Error: {result.compile_error}")
            if result.runtime_error:
                print(f"Runtime Error: {result.runtime_error}")
        
        print(f"Exit Code: {result.exit_code}")
        
        # Also test the migration method
        print("\n🔄 Testing migration method (Java 8 → Java 8)...")
        source_result, target_result = java_runner.compile_and_run_with_migration(java_code, 8, 8)
        
        print(f"Source (Java 8): {'✅ Success' if source_result.success else '❌ Failed'}")
        print(f"Target (Java 8): {'✅ Success' if target_result.success else '❌ Failed'}")
        
        if source_result.success:
            print(f"Source Output: '{source_result.stdout.strip()}'")
        if target_result.success:
            print(f"Target Output: '{target_result.stdout.strip()}'")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_java_code()
    print(f"\n{'✅ Test completed successfully!' if success else '❌ Test failed!'}")
    sys.exit(0 if success else 1)