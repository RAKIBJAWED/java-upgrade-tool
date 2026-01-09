#!/usr/bin/env python3
"""
Test the exact failing Nashorn code from the UI.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner

def test_failing_nashorn():
    """Test the exact Nashorn code that's failing in the UI."""
    
    # Exact code from the user (without proper exception handling)
    failing_code = '''import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;

public class Main {
    public static void main(String[] args) {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
        engine.eval("print('Hello from Nashorn')");
    }
}'''
    
    print("Testing Failing Nashorn Code")
    print("=" * 50)
    print(f"Code to test:\n{failing_code}")
    print("=" * 50)
    
    try:
        # Initialize JavaRunner
        java_runner = JavaRunner()
        print("✅ JavaRunner initialized successfully")
        
        # Test with Java 8 (should work but might have issues)
        print("\n🔄 Testing with Java 8...")
        result = java_runner.compile_and_run(failing_code, 8)
        
        print(f"\n📊 Results:")
        print(f"Success: {'✅ Yes' if result.success else '❌ No'}")
        print(f"Java Version: {result.java_version}")
        print(f"Execution Time: {result.execution_time:.3f}s")
        print(f"Exit Code: {result.exit_code}")
        
        if result.success:
            print(f"✅ STDOUT: '{result.stdout.strip()}'")
            if result.stderr.strip():
                print(f"⚠️ STDERR: '{result.stderr.strip()}'")
        else:
            print("❌ EXECUTION FAILED:")
            if result.compile_error:
                print(f"  📝 Compilation Error: {result.compile_error}")
            if result.runtime_error:
                print(f"  🏃 Runtime Error: {result.runtime_error}")
            if result.stdout.strip():
                print(f"  📤 STDOUT: '{result.stdout.strip()}'")
            if result.stderr.strip():
                print(f"  📤 STDERR: '{result.stderr.strip()}'")
        
        # Test with Java 17 for comparison
        print("\n🔄 Testing with Java 17 for comparison...")
        result17 = java_runner.compile_and_run(failing_code, 17)
        
        print(f"Java 17 Success: {'✅ Yes' if result17.success else '❌ No'}")
        if result17.success:
            print(f"Java 17 Output: '{result17.stdout.strip()}'")
        else:
            if result17.compile_error:
                print(f"Java 17 Compilation Error: {result17.compile_error}")
            if result17.runtime_error:
                print(f"Java 17 Runtime Error: {result17.runtime_error}")
            if result17.stdout.strip():
                print(f"Java 17 STDOUT: '{result17.stdout.strip()}'")
            if result17.stderr.strip():
                print(f"Java 17 STDERR: '{result17.stderr.strip()}'")
        
        # Show the corrected version
        print("\n💡 CORRECTED VERSION:")
        corrected_code = '''import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import javax.script.ScriptException;

public class Main {
    public static void main(String[] args) {
        try {
            ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
            if (engine != null) {
                engine.eval("print('Hello from Nashorn')");
            } else {
                System.out.println("Nashorn script engine not available");
            }
        } catch (ScriptException e) {
            System.out.println("Script execution error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}'''
        
        print(corrected_code)
        
        print("\n🔄 Testing corrected version with Java 8...")
        corrected_result = java_runner.compile_and_run(corrected_code, 8)
        
        print(f"Corrected Success: {'✅ Yes' if corrected_result.success else '❌ No'}")
        if corrected_result.success:
            print(f"Corrected Output: '{corrected_result.stdout.strip()}'")
        else:
            print(f"Corrected Error: {corrected_result.compile_error or corrected_result.runtime_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_failing_nashorn()
    print(f"\n{'✅ Test completed!' if success else '❌ Test failed!'}")
    sys.exit(0 if success else 1)