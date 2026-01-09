#!/usr/bin/env python3
"""
Test the Nashorn migration scenario (Java 8 to Java 17).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.java_runner import JavaRunner

def test_nashorn_migration():
    """Test the Nashorn script engine migration from Java 8 to Java 17."""
    
    nashorn_code = '''import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;

public class Main {
    public static void main(String[] args) {
        try {
            ScriptEngine engine = new ScriptEngineManager().getEngineByName("nashorn");
            if (engine != null) {
                engine.eval("print('Hello from Nashorn')");
            } else {
                System.out.println("Nashorn script engine not available");
            }
        } catch (Exception e) {
            System.out.println("Error: " + e.getMessage());
            e.printStackTrace();
        }
    }
}'''
    
    print("Testing Nashorn Migration (Java 8 → Java 17)")
    print("=" * 60)
    print(f"Code to test:\n{nashorn_code}")
    print("=" * 60)
    
    try:
        # Initialize JavaRunner
        java_runner = JavaRunner()
        print("✅ JavaRunner initialized successfully")
        
        # Test migration from Java 8 to Java 17
        print("\n🔄 Testing migration from Java 8 to Java 17...")
        source_result, target_result = java_runner.compile_and_run_with_migration(
            nashorn_code, 8, 17
        )
        
        print(f"\n📊 Migration Results:")
        print(f"Java 8 (Source): {'✅ Success' if source_result.success else '❌ Failed'}")
        if source_result.success:
            print(f"  Output: '{source_result.stdout.strip()}'")
        else:
            print(f"  Error: {source_result.compile_error or source_result.runtime_error}")
        
        print(f"Java 17 (Target): {'✅ Success' if target_result.success else '❌ Failed'}")
        if target_result.success:
            print(f"  Output: '{target_result.stdout.strip()}'")
        else:
            print(f"  Error: {target_result.compile_error or target_result.runtime_error}")
        
        # Analyze the migration scenario
        if source_result.success and not target_result.success:
            print("\n🔍 Analysis:")
            print("✅ Code works in Java 8 (source version)")
            print("❌ Code fails in Java 17 (target version)")
            print("💡 This is a perfect migration scenario - LLM can fix this!")
            print("🔧 Expected fix: Replace Nashorn with GraalVM JavaScript or alternative")
        elif source_result.success and target_result.success:
            print("\n🔍 Analysis:")
            print("✅ Code works in both versions - no migration needed!")
        elif not source_result.success:
            print("\n🔍 Analysis:")
            print("❌ Code fails in source version - needs to be fixed first")
        else:
            print("\n🔍 Analysis:")
            print("❌ Code fails in both versions - may have syntax errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nashorn_migration()
    print(f"\n{'✅ Migration test completed!' if success else '❌ Migration test failed!'}")
    sys.exit(0 if success else 1)