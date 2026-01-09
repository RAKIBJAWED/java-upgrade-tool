#!/usr/bin/env python3
"""
Test to see what error message is generated for Nashorn failures.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner
from core.error_classifier import ErrorClassifier

def test_nashorn_error():
    """Test what error message is generated for Nashorn failures."""
    
    # Code that should fail in Java 17 (without null check)
    failing_nashorn_code = '''import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import javax.script.ScriptException;

public class Main {
    public static void main(String[] args) throws ScriptException {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
        // This will throw NullPointerException in Java 17 when engine is null
        engine.eval("print('Hello from Nashorn')");
    }
}'''
    
    print("Testing Nashorn Error Messages")
    print("=" * 50)
    
    try:
        java_runner = JavaRunner()
        error_classifier = ErrorClassifier()
        
        # Test with Java 8 (should work)
        print("🔄 Testing with Java 8...")
        result8 = java_runner.compile_and_run(failing_nashorn_code, 8)
        print(f"Java 8 Success: {result8.success}")
        if result8.success:
            print(f"Java 8 Output: '{result8.stdout.strip()}'")
        else:
            print(f"Java 8 Error: {result8.compile_error or result8.runtime_error}")
        
        # Test with Java 17 (should fail)
        print("\n🔄 Testing with Java 17...")
        result17 = java_runner.compile_and_run(failing_nashorn_code, 17)
        print(f"Java 17 Success: {result17.success}")
        if result17.success:
            print(f"Java 17 Output: '{result17.stdout.strip()}'")
        else:
            error_msg = result17.compile_error or result17.runtime_error
            print(f"Java 17 Error: {error_msg}")
            
            # Test error classification
            print(f"\n🔍 Error Classification:")
            analysis = error_classifier.analyze_error(error_msg, 17, failing_nashorn_code)
            print(f"Is Version Issue: {analysis.is_version_issue}")
            print(f"Confidence: {analysis.confidence_score}")
            print(f"Error Category: {analysis.error_category}")
            print(f"Detected Features: {analysis.detected_features}")
            print(f"Required Version: {analysis.required_version}")
        
        # Test another version that should definitely fail
        print("\n🔄 Testing code that definitely fails in Java 17...")
        definitely_failing_code = '''import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;

public class Main {
    public static void main(String[] args) {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
        System.out.println("Engine: " + engine);
        if (engine == null) {
            throw new RuntimeException("Nashorn script engine not available - this is a version compatibility issue!");
        }
        try {
            engine.eval("print('Hello from Nashorn')");
        } catch (Exception e) {
            throw new RuntimeException("Nashorn execution failed: " + e.getMessage());
        }
    }
}'''
        
        result17_fail = java_runner.compile_and_run(definitely_failing_code, 17)
        print(f"Definitely Failing Code Success: {result17_fail.success}")
        if not result17_fail.success:
            error_msg = result17_fail.compile_error or result17_fail.runtime_error
            print(f"Error Message: {error_msg}")
            
            analysis = error_classifier.analyze_error(error_msg, 17, definitely_failing_code)
            print(f"Is Version Issue: {analysis.is_version_issue}")
            print(f"Confidence: {analysis.confidence_score}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nashorn_error()
    print(f"\n{'✅ Test completed!' if success else '❌ Test failed!'}")
    sys.exit(0 if success else 1)