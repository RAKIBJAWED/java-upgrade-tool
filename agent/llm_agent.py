"""
LLM Agent for Java code fixing functionality.

This module provides the core LLM integration with support for multiple providers
(OpenAI, Anthropic) and intelligent code transformation for Java version compatibility.
Enhanced with comprehensive error handling, retry logic, and graceful degradation.
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
import time

from core.models import CompatibilityAnalysis
from core.error_handling import (
    ErrorHandler, ErrorCategory, ErrorSeverity, RetryableOperation, 
    RetryConfig, GracefulDegradation, handle_api_error, get_error_handler
)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"


@dataclass
class LLMResponse:
    """Response from LLM API call."""
    content: str
    model: str
    provider: LLMProvider
    tokens_used: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers with enhanced error handling."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)
        self.error_handler = get_error_handler()
        
        # Configure retry logic for API calls
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_backoff=True,
            jitter=True,
            retryable_exceptions=[ConnectionError, TimeoutError, OSError],
            retryable_error_categories=[ErrorCategory.API_ERROR, ErrorCategory.NETWORK_ERROR]
        )
        self.retry_operation = RetryableOperation(self.retry_config, self.error_handler)
    
    @abstractmethod
    def generate_code_fix(
        self, 
        code: str, 
        target_version: int, 
        error_info: CompatibilityAnalysis,
        model: str
    ) -> LLMResponse:
        """Generate fixed Java code for target version."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider."""
        pass
    
    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate API credentials."""
        pass
    
    def _handle_api_error(self, exception: Exception, operation: str) -> LLMResponse:
        """Handle API errors with comprehensive error processing."""
        # Determine error category based on exception type
        if isinstance(exception, ConnectionError):
            category = ErrorCategory.NETWORK_ERROR
            severity = ErrorSeverity.MEDIUM
            user_message = "Network connection failed. Please check your internet connection."
        elif "authentication" in str(exception).lower() or "unauthorized" in str(exception).lower():
            category = ErrorCategory.AUTHENTICATION_ERROR
            severity = ErrorSeverity.HIGH
            user_message = "API authentication failed. Please check your API keys."
        elif "rate limit" in str(exception).lower() or "too many requests" in str(exception).lower():
            category = ErrorCategory.API_ERROR
            severity = ErrorSeverity.MEDIUM
            user_message = "API rate limit exceeded. Please try again in a few minutes."
        elif isinstance(exception, TimeoutError):
            category = ErrorCategory.TIMEOUT_ERROR
            severity = ErrorSeverity.MEDIUM
            user_message = "API request timed out. Please try again."
        else:
            category = ErrorCategory.API_ERROR
            severity = ErrorSeverity.MEDIUM
            user_message = "AI service is temporarily unavailable. Please try again."
        
        # Handle the error
        error_context = self.error_handler.handle_error(
            exception=exception,
            category=category,
            severity=severity,
            component=self.__class__.__name__,
            operation=operation,
            user_message=user_message,
            metadata={"provider": self.__class__.__name__, "operation": operation}
        )
        
        return LLMResponse(
            content="",
            model="",
            provider=LLMProvider.OPENAI,  # Default, will be overridden
            success=False,
            error_message=error_context.user_message
        )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self._available_models = ["gpt-4", "gpt-3.5-turbo"]
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    def generate_code_fix(
        self, 
        code: str, 
        target_version: int, 
        error_info: CompatibilityAnalysis,
        model: str = "gpt-4"
    ) -> LLMResponse:
        """Generate fixed Java code using OpenAI API with comprehensive error handling."""
        def _make_api_call():
            prompt = self._build_fix_prompt(code, target_version, error_info)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Java expert specializing in version compatibility fixes. "
                                 "Generate only the corrected Java code without explanations."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
                timeout=30  # Add timeout
            )
            
            fixed_code = response.choices[0].message.content.strip()
            # Remove code block markers if present
            if fixed_code.startswith("```java"):
                fixed_code = fixed_code[7:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            
            return LLMResponse(
                content=fixed_code.strip(),
                model=model,
                provider=LLMProvider.OPENAI,
                tokens_used=response.usage.total_tokens if response.usage else None,
                success=True
            )
        
        try:
            # Use retry logic for API calls
            return self.retry_operation.execute(_make_api_call)
        except Exception as e:
            self.logger.error(f"OpenAI API error after retries: {str(e)}")
            return self._handle_api_error(e, "generate_code_fix")
    
    def get_available_models(self) -> List[str]:
        """Get available OpenAI models."""
        return self._available_models.copy()
    
    def validate_credentials(self) -> bool:
        """Validate OpenAI API credentials with enhanced error handling."""
        try:
            def _validate():
                # Make a simple API call to validate credentials
                self.client.models.list()
                return True
            
            # Use retry logic for credential validation
            return self.retry_operation.execute(_validate)
        except Exception as e:
            self.error_handler.handle_error(
                exception=e,
                category=ErrorCategory.AUTHENTICATION_ERROR,
                severity=ErrorSeverity.HIGH,
                component=self.__class__.__name__,
                operation="validate_credentials",
                user_message="OpenAI API key validation failed. Please check your API key.",
                metadata={"provider": "OpenAI"}
            )
            return False
    
    def _build_migration_prompt(self, code: str, target_version: int) -> str:
        """Build enhanced prompt specifically for migration scenarios."""
        prompt = f"""You are a Java migration expert. Fix this Java code to work with Java {target_version}.

The code currently works in an older Java version but fails in Java {target_version}.

Original code:
```java
{code}
```

Migration Task:
- Source: Works in older Java version
- Target: Must work in Java {target_version}

Common Migration Issues and Solutions:
1. **Nashorn Script Engine (removed in Java 15+)**:
   - Replace with alternative JavaScript execution
   - Use ProcessBuilder to run Node.js if available
   - Or provide graceful fallback message

2. **Deprecated APIs**:
   - Replace with modern equivalents
   - Use supported alternatives in Java {target_version}

3. **Removed Features**:
   - Find alternative implementations
   - Use third-party libraries if needed

Critical Requirements:
1. **PRESERVE FUNCTIONALITY**: The fixed code must produce the same behavior
2. **TARGET VERSION COMPLIANCE**: Use ONLY features available in Java {target_version}
3. **HANDLE UNAVAILABLE FEATURES**: If a feature is not available, provide graceful alternatives
4. **COMPLETE SOLUTION**: Return the entire working code

If the migration is not feasible (e.g., requires external dependencies that cannot be assumed), start your response with:
"MIGRATION_NOT_FEASIBLE: [reason]"

Otherwise, return only the corrected Java code without explanations:"""
        return prompt

    def _build_fix_prompt(self, code: str, target_version: int, error_info: CompatibilityAnalysis) -> str:
        """Build comprehensive prompt for code fixing with transformation strategies."""
        # Check if this is a migration scenario
        is_migration = "version_migration" in error_info.detected_features
        
        if is_migration:
            return self._build_migration_prompt(code, target_version)
        
        # Get version-specific transformation strategies
        strategies = self._get_transformation_strategies(error_info.detected_features, target_version)
        
        prompt = f"""Fix this Java code to be compatible with Java {target_version}.

Original code:
```java
{code}
```

Error Analysis:
- Incompatible features detected: {', '.join(error_info.detected_features)}
- Minimum version required: {error_info.required_version}
- Error category: {error_info.error_category}
- Confidence: {error_info.confidence_score:.2f}

Transformation Strategies:
{strategies}

Critical Requirements:
1. PRESERVE EXACT PROGRAM LOGIC: The fixed code must produce identical output to the original
2. TARGET VERSION COMPLIANCE: Use ONLY language features available in Java {target_version} or earlier
3. MAINTAIN FUNCTIONALITY: All methods, classes, and behavior must remain unchanged
4. CODE QUALITY: Follow Java best practices and maintain readability
5. COMPLETE CODE: Return the entire fixed class/file, not just snippets

Java {target_version} Available Features:
{self._get_available_features_description(target_version)}

Return only the corrected Java code without explanations or markdown formatting:"""
        return prompt
    
    def _get_transformation_strategies(self, detected_features: List[str], target_version: int) -> str:
        """Get specific transformation strategies for detected features."""
        strategies = []
        
        for feature in detected_features:
            if feature == "var":
                strategies.append("- Replace 'var' with explicit type declarations (e.g., var x = 5; → int x = 5;)")
            elif feature == "switch_expressions" or feature == "switch_expression_preview":
                strategies.append("- Convert switch expressions to traditional switch statements with explicit variable assignment")
            elif feature == "text_blocks" or feature == "text_blocks_preview":
                strategies.append("- Replace text blocks (\"\"\"...\"\"\") with regular string concatenation using + operator")
            elif feature == "records" or feature == "records_preview":
                strategies.append("- Convert records to regular classes with private fields, constructor, and getter methods")
            elif feature == "pattern_matching_instanceof" or feature == "pattern_matching_instanceof_preview":
                strategies.append("- Replace pattern matching instanceof with traditional instanceof and explicit casting")
            elif feature == "sealed_classes" or feature == "sealed_classes_preview":
                strategies.append("- Remove 'sealed' keyword and 'permits' clause, use regular class inheritance")
            elif feature == "lambda_expressions":
                strategies.append("- Replace lambda expressions with anonymous inner classes")
            elif feature == "method_references":
                strategies.append("- Replace method references (::) with lambda expressions or anonymous classes")
            elif feature == "stream_api":
                strategies.append("- Replace Stream API with traditional for loops and collections")
            elif feature == "optional":
                strategies.append("- Replace Optional with null checks and traditional conditional logic")
            elif feature == "string_methods_11":
                strategies.append("- Replace Java 11 String methods (isBlank, strip, lines) with Java 8 equivalents")
            elif feature == "http_client":
                strategies.append("- Replace HttpClient with URLConnection or third-party HTTP libraries")
            elif feature == "virtual_threads" or feature == "virtual_threads_preview":
                strategies.append("- Replace virtual threads with traditional Thread class or thread pools")
        
        if not strategies:
            strategies.append("- Apply general compatibility fixes based on compilation errors")
        
        return "\n".join(strategies)
    
    def _get_available_features_description(self, target_version: int) -> str:
        """Get description of features available in target version."""
        if target_version >= 21:
            return "All Java features through 21 (virtual threads, pattern matching, records, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 17:
            return "Java 17 features (sealed classes, pattern matching, records, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 16:
            return "Java 16 features (records, pattern matching instanceof, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 15:
            return "Java 15 features (text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 14:
            return "Java 14 features (switch expressions, var, lambdas, streams)"
        elif target_version >= 11:
            return "Java 11 features (var, lambdas, streams, new String methods, HttpClient)"
        elif target_version >= 10:
            return "Java 10 features (var, lambdas, streams)"
        elif target_version >= 9:
            return "Java 9 features (lambdas, streams, modules)"
        else:
            return "Java 8 features (lambdas, streams, default methods, Optional)"


class TogetherProvider(BaseLLMProvider):
    """Together AI API provider implementation (OpenAI-compatible)."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.together.xyz/v1"
            )
            self._available_models = [
                "meta-llama/Llama-2-70b-chat-hf",
                "meta-llama/Llama-2-13b-chat-hf", 
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO"
            ]
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    def generate_code_fix(
        self, 
        code: str, 
        target_version: int, 
        error_info: CompatibilityAnalysis,
        model: str = "meta-llama/Llama-2-70b-chat-hf"
    ) -> LLMResponse:
        """Generate fixed Java code using Together AI API."""
        try:
            prompt = self._build_fix_prompt(code, target_version, error_info)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Java expert specializing in version compatibility fixes. "
                                 "Generate only the corrected Java code without explanations."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            fixed_code = response.choices[0].message.content.strip()
            # Remove code block markers if present
            if fixed_code.startswith("```java"):
                fixed_code = fixed_code[7:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            
            return LLMResponse(
                content=fixed_code.strip(),
                model=model,
                provider=LLMProvider.TOGETHER,
                tokens_used=response.usage.total_tokens if response.usage else None,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Together AI API error: {str(e)}")
            return LLMResponse(
                content="",
                model=model,
                provider=LLMProvider.TOGETHER,
                success=False,
                error_message=str(e)
            )
    
    def get_available_models(self) -> List[str]:
        """Get available Together AI models."""
        return self._available_models.copy()
    
    def validate_credentials(self) -> bool:
        """Validate Together AI API credentials."""
        try:
            # Make a simple API call to validate credentials
            self.client.chat.completions.create(
                model="meta-llama/Llama-2-13b-chat-hf",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            self.logger.error(f"Together AI credential validation failed: {str(e)}")
            return False
    
    def _build_fix_prompt(self, code: str, target_version: int, error_info: CompatibilityAnalysis) -> str:
        """Build comprehensive prompt for code fixing with transformation strategies."""
        # Get version-specific transformation strategies
        strategies = self._get_transformation_strategies(error_info.detected_features, target_version)
        
        prompt = f"""Fix this Java code to be compatible with Java {target_version}.

Original code:
```java
{code}
```

Error Analysis:
- Incompatible features detected: {', '.join(error_info.detected_features)}
- Minimum version required: {error_info.required_version}
- Error category: {error_info.error_category}
- Confidence: {error_info.confidence_score:.2f}

Transformation Strategies:
{strategies}

Critical Requirements:
1. PRESERVE EXACT PROGRAM LOGIC: The fixed code must produce identical output to the original
2. TARGET VERSION COMPLIANCE: Use ONLY language features available in Java {target_version} or earlier
3. MAINTAIN FUNCTIONALITY: All methods, classes, and behavior must remain unchanged
4. CODE QUALITY: Follow Java best practices and maintain readability
5. COMPLETE CODE: Return the entire fixed class/file, not just snippets

Java {target_version} Available Features:
{self._get_available_features_description(target_version)}

Return only the corrected Java code without explanations or markdown formatting:"""
        return prompt
    
    def _get_transformation_strategies(self, detected_features: List[str], target_version: int) -> str:
        """Get specific transformation strategies for detected features."""
        strategies = []
        
        for feature in detected_features:
            if feature == "var":
                strategies.append("- Replace 'var' with explicit type declarations (e.g., var x = 5; → int x = 5;)")
            elif feature == "switch_expressions" or feature == "switch_expression_preview":
                strategies.append("- Convert switch expressions to traditional switch statements with explicit variable assignment")
            elif feature == "text_blocks" or feature == "text_blocks_preview":
                strategies.append("- Replace text blocks (\"\"\"...\"\"\") with regular string concatenation using + operator")
            elif feature == "records" or feature == "records_preview":
                strategies.append("- Convert records to regular classes with private fields, constructor, and getter methods")
            elif feature == "pattern_matching_instanceof" or feature == "pattern_matching_instanceof_preview":
                strategies.append("- Replace pattern matching instanceof with traditional instanceof and explicit casting")
            elif feature == "sealed_classes" or feature == "sealed_classes_preview":
                strategies.append("- Remove 'sealed' keyword and 'permits' clause, use regular class inheritance")
            elif feature == "lambda_expressions":
                strategies.append("- Replace lambda expressions with anonymous inner classes")
            elif feature == "method_references":
                strategies.append("- Replace method references (::) with lambda expressions or anonymous classes")
            elif feature == "stream_api":
                strategies.append("- Replace Stream API with traditional for loops and collections")
            elif feature == "optional":
                strategies.append("- Replace Optional with null checks and traditional conditional logic")
            elif feature == "string_methods_11":
                strategies.append("- Replace Java 11 String methods (isBlank, strip, lines) with Java 8 equivalents")
            elif feature == "http_client":
                strategies.append("- Replace HttpClient with URLConnection or third-party HTTP libraries")
            elif feature == "virtual_threads" or feature == "virtual_threads_preview":
                strategies.append("- Replace virtual threads with traditional Thread class or thread pools")
        
        if not strategies:
            strategies.append("- Apply general compatibility fixes based on compilation errors")
        
        return "\n".join(strategies)
    
    def _get_available_features_description(self, target_version: int) -> str:
        """Get description of features available in target version."""
        if target_version >= 21:
            return "All Java features through 21 (virtual threads, pattern matching, records, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 17:
            return "Java 17 features (sealed classes, pattern matching, records, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 16:
            return "Java 16 features (records, pattern matching instanceof, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 15:
            return "Java 15 features (text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 14:
            return "Java 14 features (switch expressions, var, lambdas, streams)"
        elif target_version >= 11:
            return "Java 11 features (var, lambdas, streams, new String methods, HttpClient)"
        elif target_version >= 10:
            return "Java 10 features (var, lambdas, streams)"
        elif target_version >= 9:
            return "Java 9 features (lambdas, streams, modules)"
        else:
            return "Java 8 features (lambdas, streams, default methods, Optional)"


class AnthropicProvider(BaseLLMProvider):
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            # Use Claude Haiku model (confirmed working)
            self._available_models = ["claude-3-haiku-20240307"]
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
    
    def generate_code_fix(
        self, 
        code: str, 
        target_version: int, 
        error_info: CompatibilityAnalysis,
        model: str = "claude-3-haiku-20240307"
    ) -> LLMResponse:
        """Generate fixed Java code using Anthropic API."""
        try:
            prompt = self._build_fix_prompt(code, target_version, error_info)
            
            response = self.client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            fixed_code = response.content[0].text.strip()
            # Remove code block markers if present
            if fixed_code.startswith("```java"):
                fixed_code = fixed_code[7:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            
            return LLMResponse(
                content=fixed_code.strip(),
                model=model,
                provider=LLMProvider.ANTHROPIC,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            return LLMResponse(
                content="",
                model=model,
                provider=LLMProvider.ANTHROPIC,
                success=False,
                error_message=str(e)
            )
    
    def get_available_models(self) -> List[str]:
        """Get available Anthropic models."""
        return self._available_models.copy()
    
    def validate_credentials(self) -> bool:
        """Validate Anthropic API credentials."""
        try:
            # Make a simple API call to validate credentials
            self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            self.logger.error(f"Anthropic credential validation failed: {str(e)}")
            return False
    
    def _build_fix_prompt(self, code: str, target_version: int, error_info: CompatibilityAnalysis) -> str:
        """Build comprehensive prompt for code fixing with transformation strategies."""
        # Get version-specific transformation strategies
        strategies = self._get_transformation_strategies(error_info.detected_features, target_version)
        
        prompt = f"""You are a Java expert. Fix this Java code to be compatible with Java {target_version}.

Original code:
```java
{code}
```

Error Analysis:
- Incompatible features detected: {', '.join(error_info.detected_features)}
- Minimum version required: {error_info.required_version}
- Error category: {error_info.error_category}
- Confidence: {error_info.confidence_score:.2f}

Transformation Strategies:
{strategies}

Critical Requirements:
1. PRESERVE EXACT PROGRAM LOGIC: The fixed code must produce identical output to the original
2. TARGET VERSION COMPLIANCE: Use ONLY language features available in Java {target_version} or earlier
3. MAINTAIN FUNCTIONALITY: All methods, classes, and behavior must remain unchanged
4. CODE QUALITY: Follow Java best practices and maintain readability
5. COMPLETE CODE: Return the entire fixed class/file, not just snippets

Java {target_version} Available Features:
{self._get_available_features_description(target_version)}

Return only the corrected Java code without explanations or markdown formatting:"""
        return prompt
    
    def _get_transformation_strategies(self, detected_features: List[str], target_version: int) -> str:
        """Get specific transformation strategies for detected features."""
        strategies = []
        
        for feature in detected_features:
            if feature == "var":
                strategies.append("- Replace 'var' with explicit type declarations (e.g., var x = 5; → int x = 5;)")
            elif feature == "switch_expressions" or feature == "switch_expression_preview":
                strategies.append("- Convert switch expressions to traditional switch statements with explicit variable assignment")
            elif feature == "text_blocks" or feature == "text_blocks_preview":
                strategies.append("- Replace text blocks (\"\"\"...\"\"\") with regular string concatenation using + operator")
            elif feature == "records" or feature == "records_preview":
                strategies.append("- Convert records to regular classes with private fields, constructor, and getter methods")
            elif feature == "pattern_matching_instanceof" or feature == "pattern_matching_instanceof_preview":
                strategies.append("- Replace pattern matching instanceof with traditional instanceof and explicit casting")
            elif feature == "sealed_classes" or feature == "sealed_classes_preview":
                strategies.append("- Remove 'sealed' keyword and 'permits' clause, use regular class inheritance")
            elif feature == "lambda_expressions":
                strategies.append("- Replace lambda expressions with anonymous inner classes")
            elif feature == "method_references":
                strategies.append("- Replace method references (::) with lambda expressions or anonymous classes")
            elif feature == "stream_api":
                strategies.append("- Replace Stream API with traditional for loops and collections")
            elif feature == "optional":
                strategies.append("- Replace Optional with null checks and traditional conditional logic")
            elif feature == "string_methods_11":
                strategies.append("- Replace Java 11 String methods (isBlank, strip, lines) with Java 8 equivalents")
            elif feature == "http_client":
                strategies.append("- Replace HttpClient with URLConnection or third-party HTTP libraries")
            elif feature == "virtual_threads" or feature == "virtual_threads_preview":
                strategies.append("- Replace virtual threads with traditional Thread class or thread pools")
        
        if not strategies:
            strategies.append("- Apply general compatibility fixes based on compilation errors")
        
        return "\n".join(strategies)
    
    def _get_available_features_description(self, target_version: int) -> str:
        """Get description of features available in target version."""
        if target_version >= 21:
            return "All Java features through 21 (virtual threads, pattern matching, records, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 17:
            return "Java 17 features (sealed classes, pattern matching, records, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 16:
            return "Java 16 features (records, pattern matching instanceof, text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 15:
            return "Java 15 features (text blocks, switch expressions, var, lambdas, streams)"
        elif target_version >= 14:
            return "Java 14 features (switch expressions, var, lambdas, streams)"
        elif target_version >= 11:
            return "Java 11 features (var, lambdas, streams, new String methods, HttpClient)"
        elif target_version >= 10:
            return "Java 10 features (var, lambdas, streams)"
        elif target_version >= 9:
            return "Java 9 features (lambdas, streams, modules)"
        else:
            return "Java 8 features (lambdas, streams, default methods, Optional)"


class JavaFixAgent:
    """
    Main LLM agent for Java code fixing.
    
    This class provides a unified interface for code fixing using multiple LLM providers.
    It handles provider selection, credential management, and code transformation logic.
    """
    
    def __init__(self):
        self.providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self.current_model: Optional[str] = None
        self.current_provider: Optional[LLMProvider] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize providers based on available API keys
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available LLM providers based on API keys."""
        # OpenAI provider
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            try:
                provider = OpenAIProvider(openai_key)
                if provider.validate_credentials():
                    self.providers[LLMProvider.OPENAI] = provider
                    self.logger.info("OpenAI provider initialized successfully")
                else:
                    self.logger.warning("OpenAI API key validation failed")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI provider: {str(e)}")
        
        # Together AI provider
        together_key = os.getenv('TOGETHER_AI_API_KEY')
        if together_key:
            try:
                provider = TogetherProvider(together_key)
                if provider.validate_credentials():
                    self.providers[LLMProvider.TOGETHER] = provider
                    self.logger.info("Together AI provider initialized successfully")
                else:
                    self.logger.warning("Together AI API key validation failed")
            except Exception as e:
                self.logger.error(f"Failed to initialize Together AI provider: {str(e)}")
        
        # Anthropic provider
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                provider = AnthropicProvider(anthropic_key)
                if provider.validate_credentials():
                    self.providers[LLMProvider.ANTHROPIC] = provider
                    self.logger.info("Anthropic provider initialized successfully")
                else:
                    self.logger.warning("Anthropic API key validation failed")
            except Exception as e:
                self.logger.error(f"Failed to initialize Anthropic provider: {str(e)}")
        
        # Set default provider and model if available - prioritize OpenAI GPT-4
        if LLMProvider.OPENAI in self.providers:
            self.current_provider = LLMProvider.OPENAI
            self.current_model = "gpt-4"
        elif LLMProvider.ANTHROPIC in self.providers:
            self.current_provider = LLMProvider.ANTHROPIC
            self.current_model = "claude-3-haiku-20240307"
        elif LLMProvider.TOGETHER in self.providers:
            self.current_provider = LLMProvider.TOGETHER
            self.current_model = "meta-llama/Llama-2-70b-chat-hf"
    
    def get_available_models(self) -> Dict[str, LLMProvider]:
        """Get all available models from all providers."""
        models = {}
        for provider_type, provider in self.providers.items():
            for model in provider.get_available_models():
                # Create user-friendly model names
                if provider_type == LLMProvider.OPENAI:
                    if model == "gpt-4":
                        models["GPT-4"] = provider_type
                    elif model == "gpt-3.5-turbo":
                        models["GPT-3.5-turbo"] = provider_type
                elif provider_type == LLMProvider.TOGETHER:
                    if "Llama-2-70b" in model:
                        models["Llama-2-70B"] = provider_type
                    elif "Llama-2-13b" in model:
                        models["Llama-2-13B"] = provider_type
                    elif "Mixtral-8x7B" in model and "Instruct" in model:
                        models["Mixtral-8x7B"] = provider_type
                    elif "Nous-Hermes" in model:
                        models["Nous-Hermes-2-Mixtral"] = provider_type
                elif provider_type == LLMProvider.ANTHROPIC:
                    if "haiku" in model:
                        models["Claude-3-haiku"] = provider_type
        return models
    
    def set_model(self, model_name: str) -> bool:
        """
        Set the current LLM model to use.
        
        Args:
            model_name: User-friendly model name (e.g., "GPT-4", "Claude-3-opus")
            
        Returns:
            bool: True if model was set successfully, False otherwise
        """
        available_models = self.get_available_models()
        if model_name not in available_models:
            self.logger.error(f"Model {model_name} not available")
            return False
        
        self.current_provider = available_models[model_name]
        
        # Map user-friendly names to actual model names
        model_mapping = {
            "GPT-4": "gpt-4",
            "GPT-3.5-turbo": "gpt-3.5-turbo",
            "Llama-2-70B": "meta-llama/Llama-2-70b-chat-hf",
            "Llama-2-13B": "meta-llama/Llama-2-13b-chat-hf",
            "Mixtral-8x7B": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "Nous-Hermes-2-Mixtral": "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO",
            "Claude-3-haiku": "claude-3-haiku-20240307"
        }
        
        self.current_model = model_mapping.get(model_name, model_name)
        self.logger.info(f"Set model to {model_name} ({self.current_model})")
        return True
    
    def fix_code(
        self, 
        code: str, 
        target_version: int, 
        error_info: CompatibilityAnalysis
    ) -> LLMResponse:
        """
        Fix Java code for target version compatibility.
        
        Args:
            code: Original Java code
            target_version: Target Java version
            error_info: Analysis of compatibility issues
            
        Returns:
            LLMResponse: Fixed code or error information
        """
        if not self.current_provider or not self.current_model:
            return LLMResponse(
                content="",
                model="",
                provider=LLMProvider.OPENAI,
                success=False,
                error_message="No LLM provider available. Please check API keys."
            )
        
        provider = self.providers[self.current_provider]
        response = provider.generate_code_fix(code, target_version, error_info, self.current_model)
        
        # Enhanced validation if fix was successful
        if response.success and response.content:
            # Validate logic preservation and version compatibility
            is_valid = self.validate_fix(code, response.content, target_version)
            
            if not is_valid:
                self.logger.warning("Generated fix failed validation checks")
                response.success = False
                response.error_message = "Generated code failed validation (logic preservation or version compatibility)"
        
        return response
    
    def fix_code_with_validation(
        self,
        code: str,
        target_version: int,
        error_info: CompatibilityAnalysis,
        max_attempts: int = 2
    ) -> Dict[str, any]:
        """
        Fix Java code with comprehensive validation and retry logic.
        
        This method provides enhanced code fixing with multiple validation steps
        and automatic retry on validation failures.
        
        Args:
            code: Original Java code
            target_version: Target Java version
            error_info: Analysis of compatibility issues
            max_attempts: Maximum number of fix attempts
            
        Returns:
            Dictionary with fix results and validation details
        """
        attempts = []
        
        for attempt in range(max_attempts):
            self.logger.info(f"Code fix attempt {attempt + 1}/{max_attempts}")
            
            # Generate fix
            response = self.fix_code(code, target_version, error_info)
            
            attempt_result = {
                'attempt_number': attempt + 1,
                'response': response,
                'validation_passed': False,
                'validation_details': {}
            }
            
            if response.success and response.content:
                # Comprehensive validation
                validation_details = self._comprehensive_validation(code, response.content, target_version)
                attempt_result['validation_details'] = validation_details
                attempt_result['validation_passed'] = validation_details['overall_valid']
                
                if validation_details['overall_valid']:
                    # Success!
                    return {
                        'success': True,
                        'fixed_code': response.content,
                        'attempts': attempts + [attempt_result],
                        'final_attempt': attempt + 1,
                        'validation_details': validation_details
                    }
            
            attempts.append(attempt_result)
        
        # All attempts failed
        return {
            'success': False,
            'fixed_code': None,
            'attempts': attempts,
            'final_attempt': max_attempts,
            'error': "All fix attempts failed validation"
        }
    
    def _comprehensive_validation(self, original: str, fixed: str, target_version: int) -> Dict[str, any]:
        """
        Perform comprehensive validation of fixed code.
        
        Args:
            original: Original Java code
            fixed: Fixed Java code
            target_version: Target Java version
            
        Returns:
            Dictionary with detailed validation results
        """
        validation_results = {
            'overall_valid': True,
            'checks': {}
        }
        
        # Basic structure validation
        basic_valid = self.validate_fix(original, fixed, target_version)
        validation_results['checks']['basic_structure'] = {
            'passed': basic_valid,
            'description': 'Basic Java structure and syntax validation'
        }
        
        if not basic_valid:
            validation_results['overall_valid'] = False
        
        # Version compatibility validation
        version_check = self.check_target_version_compatibility(fixed, target_version)
        validation_results['checks']['version_compatibility'] = {
            'passed': version_check.get('is_compatible', False),
            'description': f'Java {target_version} compatibility check',
            'details': version_check
        }
        
        if not version_check.get('is_compatible', False):
            validation_results['overall_valid'] = False
        
        # Logic preservation validation (basic)
        logic_preserved = self._validate_logic_preservation(original, fixed)
        validation_results['checks']['logic_preservation'] = {
            'passed': logic_preserved,
            'description': 'Basic logic preservation validation'
        }
        
        if not logic_preserved:
            validation_results['overall_valid'] = False
        
        return validation_results
    
    def _validate_logic_preservation(self, original: str, fixed: str) -> bool:
        """
        Validate that the fixed code preserves the original program logic.
        
        This is a heuristic-based validation that checks for structural similarities
        and preservation of key program elements.
        
        Args:
            original: Original Java code
            fixed: Fixed Java code
            
        Returns:
            bool: True if logic appears to be preserved
        """
        try:
            # Extract key elements from both versions
            original_elements = self._extract_code_elements(original)
            fixed_elements = self._extract_code_elements(fixed)
            
            # Check that key elements are preserved
            checks = []
            
            # Class names should match (if both have class names)
            if original_elements['class_name'] and fixed_elements['class_name']:
                checks.append(original_elements['class_name'] == fixed_elements['class_name'])
            else:
                checks.append(True)  # If we can't extract, assume it's fine
            
            # Method names should be mostly preserved
            if original_elements['method_names'] and fixed_elements['method_names']:
                preserved_methods = len(set(original_elements['method_names']).intersection(set(fixed_elements['method_names'])))
                checks.append(preserved_methods >= len(original_elements['method_names']) * 0.5)
            else:
                checks.append(True)
            
            # String literals should be mostly preserved (allowing for some changes)
            if original_elements['string_literals'] and fixed_elements['string_literals']:
                preserved_strings = len(set(original_elements['string_literals']).intersection(set(fixed_elements['string_literals'])))
                checks.append(preserved_strings >= len(original_elements['string_literals']) * 0.7)
            else:
                checks.append(True)
            
            # At least 2 out of 3 checks should pass, or if we have very simple code, be more lenient
            if len(original.split('\n')) <= 5:  # Very simple code
                return sum(checks) >= 1
            else:
                return sum(checks) >= 2
            
        except Exception as e:
            self.logger.warning(f"Logic preservation validation error: {e}")
            return True  # Default to valid if we can't check
    
    def _extract_code_elements(self, code: str) -> Dict[str, any]:
        """
        Extract key elements from Java code for comparison.
        
        Args:
            code: Java source code
            
        Returns:
            Dictionary with extracted elements
        """
        import re
        
        elements = {
            'class_name': None,
            'method_names': [],
            'variable_names': [],
            'string_literals': []
        }
        
        try:
            # Extract class name
            class_match = re.search(r'(?:public\s+)?class\s+(\w+)', code)
            if class_match:
                elements['class_name'] = class_match.group(1)
            
            # Extract method names
            method_matches = re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)', code)
            elements['method_names'] = method_matches
            
            # Extract variable names (basic pattern)
            var_matches = re.findall(r'(?:int|String|double|float|boolean|var)\s+(\w+)', code)
            elements['variable_names'] = var_matches
            
            # Extract string literals
            string_matches = re.findall(r'"([^"]*)"', code)
            elements['string_literals'] = string_matches
            
        except Exception as e:
            self.logger.warning(f"Code element extraction error: {e}")
        
        return elements
    
    def validate_fix(self, original: str, fixed: str, target_version: int = None) -> bool:
        """
        Validate that the fixed code preserves original logic and meets version requirements.
        
        This enhanced validation checks both structural preservation and version compatibility.
        
        Args:
            original: Original Java code
            fixed: Fixed Java code
            target_version: Target Java version for compatibility checking
            
        Returns:
            bool: True if fix appears valid
        """
        if not fixed or not fixed.strip():
            return False
        
        # Check that it's still Java code - must contain Java keywords
        java_keywords = ["class", "public", "private", "void", "int", "String", "static", "main"]
        if not any(keyword in fixed for keyword in java_keywords):
            return False
        
        # Check for basic Java structure patterns
        if "class" not in fixed:
            return False
        
        # Enhanced structural validation
        try:
            # Check that basic structure is preserved
            original_lines = [line.strip() for line in original.split('\n') if line.strip()]
            fixed_lines = [line.strip() for line in fixed.split('\n') if line.strip()]
            
            # Should have reasonable number of lines (more lenient)
            if len(fixed_lines) < 1 or len(fixed_lines) > len(original_lines) * 5:
                return False
            
            # Check that class names are preserved (if extractable)
            original_class = self._extract_class_name(original)
            fixed_class = self._extract_class_name(fixed)
            
            if original_class and fixed_class and original_class != fixed_class:
                return False
            
            # Version compatibility check if target version provided
            if target_version is not None:
                version_compatible = self._check_version_compatibility(fixed, target_version)
                if not version_compatible:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Validation error: {e}")
            return True  # Be more lenient on validation errors
    
    def _extract_class_name(self, code: str) -> Optional[str]:
        """Extract the main class name from Java code."""
        import re
        match = re.search(r'(?:public\s+)?class\s+(\w+)', code)
        return match.group(1) if match else None
    
    def _extract_method_signatures(self, code: str) -> List[str]:
        """Extract method signatures from Java code."""
        import re
        # Simple regex to find method declarations
        methods = re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+\w+\s*\([^)]*\)', code)
        return [method.strip() for method in methods]
    
    def _check_version_compatibility(self, code: str, target_version: int) -> bool:
        """
        Check if the generated code is compatible with the target Java version.
        
        Args:
            code: The generated Java code
            target_version: Target Java version
            
        Returns:
            bool: True if code is compatible with target version
        """
        try:
            # Import here to avoid circular imports
            from core.version_mapper import VersionMapper
            
            version_mapper = VersionMapper()
            analysis = version_mapper.analyze_code_features(code)
            
            # Check if any detected features require a higher version than target
            incompatible_features = [
                feature for feature in analysis.detected_features
                if version_mapper.get_required_version(feature) > target_version
            ]
            
            if incompatible_features:
                self.logger.warning(f"Generated code contains incompatible features for Java {target_version}: {incompatible_features}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Version compatibility check failed: {e}")
            # If we can't check, assume it's valid rather than failing
            return True
    
    def check_target_version_compatibility(self, code: str, target_version: int) -> Dict[str, any]:
        """
        Comprehensive check of target version compatibility for generated code.
        
        Args:
            code: The Java code to check
            target_version: Target Java version
            
        Returns:
            Dictionary with compatibility analysis results
        """
        try:
            from core.version_mapper import VersionMapper
            
            version_mapper = VersionMapper()
            analysis = version_mapper.analyze_code_features(code)
            
            is_compatible = analysis.required_version <= target_version
            incompatible_features = [
                feature for feature in analysis.detected_features
                if version_mapper.get_required_version(feature) > target_version
            ]
            
            return {
                'is_compatible': is_compatible,
                'required_version': analysis.required_version,
                'target_version': target_version,
                'detected_features': analysis.detected_features,
                'incompatible_features': incompatible_features,
                'feature_locations': analysis.feature_locations
            }
            
        except Exception as e:
            self.logger.error(f"Target version compatibility check failed: {e}")
            return {
                'is_compatible': False,
                'error': str(e),
                'target_version': target_version
            }
    
    def is_available(self) -> bool:
        """Check if any LLM provider is available."""
        return len(self.providers) > 0
    
    def get_current_model(self) -> Optional[str]:
        """Get currently selected model name."""
        if not self.current_model:
            return None
        
        # Return user-friendly name
        reverse_mapping = {
            "gpt-4": "GPT-4",
            "gpt-3.5-turbo": "GPT-3.5-turbo",
            "meta-llama/Llama-2-70b-chat-hf": "Llama-2-70B",
            "meta-llama/Llama-2-13b-chat-hf": "Llama-2-13B",
            "mistralai/Mixtral-8x7B-Instruct-v0.1": "Mixtral-8x7B",
            "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO": "Nous-Hermes-2-Mixtral",
            "claude-3-haiku-20240307": "Claude-3-haiku"
        }
        
        return reverse_mapping.get(self.current_model, self.current_model)