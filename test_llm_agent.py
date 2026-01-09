#!/usr/bin/env python3
"""
Test script for LLM Agent functionality.

This script tests the LLM agent with actual API keys if available,
or provides mock testing if no keys are present.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from agent.llm_agent import JavaFixAgent, LLMProvider, LLMResponse
from core.models import CompatibilityAnalysis


def test_agent_initialization():
    """Test LLM agent initialization."""
    print("Testing LLM agent initialization...")
    
    try:
        agent = JavaFixAgent()
        print("✅ Agent initialized successfully")
        
        # Test basic methods
        available_models = agent.get_available_models()
        print(f"✅ Available models: {list(available_models.keys())}")
        
        is_available = agent.is_available()
        print(f"✅ Agent availability: {is_available}")
        
        current_model = agent.get_current_model()
        print(f"✅ Current model: {current_model}")
        
        return True
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return False


def test_model_selection():
    """Test model selection functionality."""
    print("\nTesting model selection...")
    
    try:
        agent = JavaFixAgent()
        available_models = agent.get_available_models()
        
        if not available_models:
            print("✅ No models available (expected without API keys)")
            return True
        
        # Test setting a valid model
        first_model = list(available_models.keys())[0]
        success = agent.set_model(first_model)
        if success:
            print(f"✅ Successfully set model to {first_model}")
        else:
            print(f"❌ Failed to set model to {first_model}")
            return False
        
        # Test setting an invalid model
        success = agent.set_model("NonExistentModel")
        if not success:
            print("✅ Correctly rejected invalid model")
        else:
            print("❌ Should have rejected invalid model")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Model selection test failed: {e}")
        return False


def test_code_fixing_mock():
    """Test code fixing with mock data."""
    print("\nTesting code fixing (mock)...")
    
    try:
        agent = JavaFixAgent()
        
        # Create mock compatibility analysis
        error_info = CompatibilityAnalysis(
            is_version_issue=True,
            detected_features=["var", "switch_expression"],
            required_version=14,
            error_category="version_compatibility",
            confidence_score=0.9
        )
        
        # Test code fixing (will fail without API keys, which is expected)
        java_code = """
        public class Test {
            public static void main(String[] args) {
                var message = "Hello World";
                System.out.println(message);
            }
        }
        """
        
        response = agent.fix_code(java_code, 8, error_info)
        
        if not response.success and "No LLM provider available" in response.error_message:
            print("✅ Correctly reports no provider available (expected without API keys)")
        elif response.success:
            print("✅ Code fixing successful (API keys are available)")
            print(f"   Fixed code length: {len(response.content)} characters")
        else:
            print(f"❌ Unexpected error: {response.error_message}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Code fixing test failed: {e}")
        return False


def test_validation():
    """Test code validation functionality."""
    print("\nTesting code validation...")
    
    try:
        agent = JavaFixAgent()
        
        # Test valid fix
        original = "public class Test { public static void main(String[] args) { var x = 5; } }"
        fixed = "public class Test { public static void main(String[] args) { int x = 5; } }"
        
        is_valid = agent.validate_fix(original, fixed)
        if is_valid:
            print("✅ Valid fix correctly identified")
        else:
            print("❌ Valid fix incorrectly rejected")
            return False
        
        # Test invalid fix (empty)
        is_valid = agent.validate_fix(original, "")
        if not is_valid:
            print("✅ Empty fix correctly rejected")
        else:
            print("❌ Empty fix incorrectly accepted")
            return False
        
        # Test invalid fix (not Java)
        is_valid = agent.validate_fix(original, "print('hello world')")
        if not is_valid:
            print("✅ Non-Java fix correctly rejected")
        else:
            print("❌ Non-Java fix incorrectly accepted")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False


def test_with_real_api_keys():
    """Test with real API keys if available."""
    print("\nTesting with real API keys (if available)...")
    
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not openai_key and not anthropic_key:
        print("✅ No API keys found - skipping real API tests")
        return True
    
    try:
        agent = JavaFixAgent()
        
        if not agent.is_available():
            print("❌ Agent should be available with API keys")
            return False
        
        available_models = agent.get_available_models()
        print(f"✅ Found {len(available_models)} available models")
        
        # Try a simple fix if models are available
        if available_models:
            first_model = list(available_models.keys())[0]
            agent.set_model(first_model)
            
            error_info = CompatibilityAnalysis(
                is_version_issue=True,
                detected_features=["var"],
                required_version=10,
                error_category="version_compatibility",
                confidence_score=0.9
            )
            
            simple_code = "public class Test { public static void main(String[] args) { var x = 5; } }"
            
            print(f"   Attempting fix with {first_model}...")
            response = agent.fix_code(simple_code, 8, error_info)
            
            if response.success:
                print("✅ Real API call successful")
                print(f"   Response length: {len(response.content)} characters")
            else:
                print(f"❌ Real API call failed: {response.error_message}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Real API test failed: {e}")
        return False


def main():
    """Run all LLM agent tests."""
    print("🧪 Testing LLM Agent functionality...\n")
    
    tests = [
        test_agent_initialization,
        test_model_selection,
        test_code_fixing_mock,
        test_validation,
        test_with_real_api_keys
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*50)
    if all(results):
        print("🎉 All LLM agent tests passed!")
        
        # Check if API keys are available for additional info
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        if openai_key or anthropic_key:
            print("\n📝 API keys detected - LLM functionality is fully operational")
        else:
            print("\n📝 No API keys detected - add them to .env for full functionality")
        
        return 0
    else:
        print("❌ Some LLM agent tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())