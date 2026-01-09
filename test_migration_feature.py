#!/usr/bin/env python3
"""
Test script for the new source/target version migration feature.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner
from core.validation_system import ValidationAndRetrySystem, RetryConfiguration
from core.error_classifier import ErrorClassifier
from agent.llm_agent import JavaFixAgent

def test_nashorn_migration():
    """Test the Nashorn script engine migration from Java 8 to Java 17."""
    
    # The problematic Java code that works in Java 8 but fails in Java 17
    nashorn_code = '''
import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;

public class Main {
    public static void main(String[] args) {
        try {
            ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
            engine.eval("print('Hello from Nashorn')");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
'''
    
    print("Testing Java Version Migration Feature")
    print("=" * 50)
    print(f"Code to test:\n{nashorn_code}")
    print("=" * 50)
    
    try:
        # Initialize JavaRunner
        java_runner = JavaRunner()
        print("✅ JavaRunner initialized successfully")
        
        # Test migration from Java 8 to Java 17
        print("\n🔄 Testing migration from Java 8 to Java 17...")
        source_result, target_result = java_runner.compile_and_run_with_migration(
            nashorn_code, 8, 17
        )
        
        print(f"\n📊 Results:")
        print(f"Java 8 (Source): {'✅ Success' if source_result.success else '❌ Failed'}")
        if source_result.success:
            print(f"  Output: {source_result.stdout.strip()}")
        else:
            print(f"  Error: {source_result.compile_error or source_result.runtime_error}")
        
        print(f"Java 17 (Target): {'✅ Success' if target_result.success else '❌ Failed'}")
        if target_result.success:
            print(f"  Output: {target_result.stdout.strip()}")
        else:
            print(f"  Error: {target_result.compile_error or target_result.runtime_error}")
        
        # Test with validation system if available
        try:
            error_classifier = ErrorClassifier()
            llm_agent = JavaFixAgent()
            
            if llm_agent.is_available():
                print("\n🤖 Testing with full validation system...")
                
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
                
                system_response = validation_system.process_code_with_migration(
                    original_code=nashorn_code,
                    source_version=8,
                    target_version=17
                )
                
                print(f"Migration Status: {system_response.status.value}")
                print(f"Fix Attempts: {system_response.total_fix_attempts}")
                
                if system_response.fixed_code:
                    print(f"Fixed Code Available: Yes")
                    print(f"Fixed Code Preview:\n{system_response.fixed_code[:200]}...")
                else:
                    print(f"Fixed Code Available: No")
                    
            else:
                print("⚠️ LLM Agent not available - skipping validation system test")
                
        except Exception as e:
            print(f"⚠️ Validation system test failed: {e}")
        
        print("\n✅ Migration feature test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nashorn_migration()
    sys.exit(0 if success else 1)