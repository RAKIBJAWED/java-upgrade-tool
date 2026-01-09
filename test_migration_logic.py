#!/usr/bin/env python3
"""
Test the updated migration logic that skips error classifier.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner
from core.validation_system import ValidationAndRetrySystem, RetryConfiguration
from core.error_classifier import ErrorClassifier
from agent.llm_agent import JavaFixAgent

def test_migration_logic():
    """Test the updated migration logic."""
    
    # Nashorn code that works in Java 8 but fails in Java 17
    nashorn_code = '''import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import javax.script.ScriptException;

public class Main {
    public static void main(String[] args) throws ScriptException {
        ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
        // This will throw NullPointerException in Java 17 when engine is null
        engine.eval("print('Hello from Nashorn')");
    }
}'''
    
    print("Testing Updated Migration Logic")
    print("=" * 50)
    print(f"Code to test:\n{nashorn_code}")
    print("=" * 50)
    
    try:
        # Initialize components
        java_runner = JavaRunner()
        error_classifier = ErrorClassifier()
        llm_agent = JavaFixAgent()
        
        if not llm_agent.is_available():
            print("⚠️ LLM Agent not available - cannot test migration logic")
            return False
        
        retry_config = RetryConfiguration(
            max_attempts=1,  # Just one attempt for testing
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
        
        print("🔄 Testing migration from Java 8 to Java 17...")
        system_response = validation_system.process_code_with_migration(
            original_code=nashorn_code,
            source_version=8,
            target_version=17
        )
        
        print(f"\n📊 Migration Results:")
        print(f"Status: {system_response.status}")
        print(f"Source Version: {system_response.source_version}")
        print(f"Target Version: {system_response.target_version}")
        print(f"Total Fix Attempts: {system_response.total_fix_attempts}")
        
        if system_response.source_execution_result:
            print(f"Source Execution Success: {system_response.source_execution_result.success}")
            if system_response.source_execution_result.success:
                print(f"Source Output: '{system_response.source_execution_result.stdout.strip()}'")
        
        if system_response.fixed_code:
            print(f"Fixed Code Available: Yes")
            print(f"Fixed Code Preview:\n{system_response.fixed_code[:200]}...")
        else:
            print(f"Fixed Code Available: No")
        
        if system_response.compile_error:
            print(f"Error Message: {system_response.compile_error}")
        
        # Check if LLM was called (should be > 0 attempts)
        if system_response.total_fix_attempts > 0:
            print("✅ LLM was called for migration fixes")
        else:
            print("❌ LLM was NOT called - this indicates an issue")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_migration_logic()
    print(f"\n{'✅ Migration logic test completed!' if success else '❌ Migration logic test failed!'}")
    sys.exit(0 if success else 1)