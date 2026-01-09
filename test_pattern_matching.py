#!/usr/bin/env python3
"""
Test pattern matching for Nashorn errors.
"""

import re

def test_pattern_matching():
    """Test regex patterns against actual error messages."""
    
    # Actual error message from the test
    error_message = """Exception in thread "main" java.lang.NullPointerException: Cannot invoke "javax.script.ScriptEngine.eval(String)" because "<local1>" is null
        at Main.main(Main.java:9)"""
    
    print("Testing Pattern Matching")
    print("=" * 50)
    print(f"Error Message:\n{error_message}")
    print("=" * 50)
    
    # Test patterns
    patterns = [
        r"NullPointerException.*ScriptEngine\.eval",
        r"Cannot invoke.*ScriptEngine\.eval.*because.*null",
        r"Cannot invoke.*javax\.script\.ScriptEngine\.eval.*null",
        r"ScriptEngine\.eval.*null",
        r"javax\.script\.ScriptEngine\.eval.*null",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_message, re.IGNORECASE | re.DOTALL)
        print(f"Pattern: {pattern}")
        print(f"Match: {'✅ YES' if match else '❌ NO'}")
        if match:
            print(f"Matched text: '{match.group()}'")
        print()
    
    # Test the working pattern
    working_pattern = r"Nashorn script engine not available"
    working_message = "Exception in thread \"main\" java.lang.RuntimeException: Nashorn script engine not available - this is a version compatibility issue!"
    
    match = re.search(working_pattern, working_message, re.IGNORECASE)
    print(f"Working Pattern: {working_pattern}")
    print(f"Working Message: {working_message}")
    print(f"Match: {'✅ YES' if match else '❌ NO'}")

if __name__ == "__main__":
    test_pattern_matching()