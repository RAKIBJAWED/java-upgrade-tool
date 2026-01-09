#!/usr/bin/env python3
"""
Test script to verify the project setup is complete and functional.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import streamlit
        print("✅ Streamlit import successful")
        
        import docker
        print("✅ Docker import successful")
        
        import requests
        print("✅ Requests import successful")
        
        import hypothesis
        print("✅ Hypothesis import successful")
        
        from dotenv import load_dotenv
        print("✅ Python-dotenv import successful")
        
        from config.settings import load_configuration, validate_configuration
        print("✅ Configuration module import successful")
        
        # Test LLM agent imports
        from agent.llm_agent import JavaFixAgent, LLMProvider, LLMResponse
        print("✅ LLM agent import successful")
        
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration():
    """Test configuration loading and validation."""
    print("\nTesting configuration...")
    
    try:
        from config.settings import load_configuration, validate_configuration
        
        config = load_configuration()
        print("✅ Configuration loaded successfully")
        
        # Check required Java versions
        required_versions = {8, 11, 17, 21}
        if required_versions.issubset(set(config.java_versions.keys())):
            print("✅ All required Java versions configured")
        else:
            print("❌ Missing Java version configurations")
            return False
        
        # Test validation
        validation = validate_configuration(config)
        if validation.is_valid:
            print("✅ Configuration validation successful (API keys are available)")
        elif not validation.is_valid and "API keys" in validation.error_message:
            print("✅ Configuration validation working (correctly detects missing API keys)")
        else:
            print(f"❌ Unexpected validation result: {validation.error_message}")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_llm_agent():
    """Test LLM agent initialization and basic functionality."""
    print("\nTesting LLM agent...")
    
    try:
        from agent.llm_agent import JavaFixAgent
        
        # Initialize agent (should work even without API keys)
        agent = JavaFixAgent()
        print("✅ LLM agent initialization successful")
        
        # Test model availability (should return empty dict without API keys)
        available_models = agent.get_available_models()
        print(f"✅ Available models check successful (found {len(available_models)} models)")
        
        # Test availability check
        is_available = agent.is_available()
        if not is_available:
            print("✅ Correctly reports no providers available (expected without API keys)")
        else:
            print("✅ LLM providers are available")
        
        return True
    except Exception as e:
        print(f"❌ LLM agent test failed: {e}")
        return False

def test_project_structure():
    """Test that all required directories and files exist."""
    print("\nTesting project structure...")
    
    required_files = [
        "app.py",
        "requirements.txt",
        "README.md",
        ".gitignore",
        ".env.template",
        "config/__init__.py",
        "config/settings.py",
        "config/java_versions.json",
        "core/__init__.py",
        "agent/__init__.py",
        "agent/llm_agent.py",
        "utils/__init__.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def main():
    """Run all tests."""
    print("🚀 Testing Java Version Compatibility Fixer setup...\n")
    
    tests = [
        test_project_structure,
        test_imports,
        test_configuration,
        test_llm_agent
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*50)
    if all(results):
        print("🎉 All tests passed! Project setup is complete.")
        print("\nNext steps:")
        print("1. Copy .env.template to .env and add your API keys")
        print("2. Run: streamlit run app.py")
        print("3. Continue with the next task in the implementation plan")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())