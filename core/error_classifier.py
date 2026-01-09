"""
Error Classifier for Java Version Compatibility Fixer.

This module provides functionality to analyze Java compilation and runtime errors
to determine if they are caused by version compatibility issues, and to classify
different types of errors for appropriate handling.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import CompatibilityAnalysis
from .version_mapper import VersionMapper


class ErrorCategory(Enum):
    """Categories of Java compilation and runtime errors."""
    VERSION_COMPATIBILITY = "version_compatibility"
    SYNTAX_ERROR = "syntax_error"
    MISSING_DEPENDENCY = "missing_dependency"
    RUNTIME_EXCEPTION = "runtime_exception"
    RESOURCE_LIMIT = "resource_limit"
    UNKNOWN = "unknown"


@dataclass
class ErrorPattern:
    """Pattern for matching specific error types."""
    pattern: str
    category: ErrorCategory
    confidence: float
    java_feature: Optional[str] = None
    min_version: Optional[int] = None


class ErrorClassifier:
    """
    Analyzes Java compilation and runtime errors to determine version compatibility issues.
    
    This class uses pattern matching and integration with VersionMapper to identify
    when errors are caused by Java version incompatibility versus other issues.
    """
    
    # Common version-related error patterns
    VERSION_ERROR_PATTERNS = [
        # Java language feature errors
        ErrorPattern(
            pattern=r"cannot find symbol.*var\b",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="var",
            min_version=10
        ),
        ErrorPattern(
            pattern=r"'var' is not allowed here",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.98,
            java_feature="var",
            min_version=10
        ),
        ErrorPattern(
            pattern=r"switch expressions are not supported",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="switch_expressions",
            min_version=14
        ),
        ErrorPattern(
            pattern=r"text blocks are not supported",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="text_blocks",
            min_version=15
        ),
        ErrorPattern(
            pattern=r"records are not supported",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="records",
            min_version=16
        ),
        ErrorPattern(
            pattern=r"pattern matching in instanceof is not supported",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="pattern_matching_instanceof",
            min_version=16
        ),
        ErrorPattern(
            pattern=r"sealed classes are not supported",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="sealed_classes",
            min_version=17
        ),
        ErrorPattern(
            pattern=r"yield outside of switch expression",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.90,
            java_feature="switch_expressions",
            min_version=14
        ),
        
        # API-related version errors
        ErrorPattern(
            pattern=r"cannot find symbol.*HttpClient",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.85,
            java_feature="http_client",
            min_version=11
        ),
        ErrorPattern(
            pattern=r"package java\.net\.http does not exist",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.90,
            java_feature="http_client",
            min_version=11
        ),
        ErrorPattern(
            pattern=r"cannot find symbol.*method (isBlank|lines|strip|repeat)\(\)",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.85,
            java_feature="string_methods_11",
            min_version=11
        ),
        ErrorPattern(
            pattern=r"cannot find symbol.*Files\.readString",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.85,
            java_feature="files_methods_11",
            min_version=11
        ),
        ErrorPattern(
            pattern=r"cannot find symbol.*Thread\.ofVirtual",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.85,
            java_feature="virtual_threads",
            min_version=21
        ),
        
        # Nashorn script engine (removed in Java 15+)
        ErrorPattern(
            pattern=r".*nashorn.*not available",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="nashorn_script_engine",
            min_version=8  # Available in 8-14, removed in 15+
        ),
        ErrorPattern(
            pattern=r".*ScriptEngine.*nashorn.*null",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.90,
            java_feature="nashorn_script_engine",
            min_version=8
        ),
        ErrorPattern(
            pattern=r".*getEngineByName.*nashorn.*null",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.90,
            java_feature="nashorn_script_engine",
            min_version=8
        ),
        ErrorPattern(
            pattern=r"NullPointerException.*ScriptEngine\.eval",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.85,
            java_feature="nashorn_script_engine",
            min_version=8
        ),
        ErrorPattern(
            pattern=r"Cannot invoke.*ScriptEngine\.eval.*because.*null",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.90,
            java_feature="nashorn_script_engine",
            min_version=8
        ),
        
        # Other deprecated/removed APIs
        ErrorPattern(
            pattern=r"cannot find symbol.*Applet",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.85,
            java_feature="applet_api",
            min_version=8  # Deprecated in 9, removed in 17+
        ),
        ErrorPattern(
            pattern=r"package java\.security\.acl does not exist",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.90,
            java_feature="security_acl",
            min_version=8  # Removed in 17+
        ),
        
        # Generic version-related patterns
        ErrorPattern(
            pattern=r"source release \d+ requires target release \d+ or later",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.80
        ),
        ErrorPattern(
            pattern=r"invalid target release: \d+",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.75
        ),
        ErrorPattern(
            pattern=r"feature .* is not supported in -source \d+",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.90
        ),
        ErrorPattern(
            pattern=r"lambda expressions are not supported in -source \d+",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="lambda_expressions",
            min_version=8
        ),
        ErrorPattern(
            pattern=r"method references are not supported in -source \d+",
            category=ErrorCategory.VERSION_COMPATIBILITY,
            confidence=0.95,
            java_feature="method_references",
            min_version=8
        ),
    ]
    
    # Non-version error patterns
    OTHER_ERROR_PATTERNS = [
        ErrorPattern(
            pattern=r"cannot find symbol.*class",
            category=ErrorCategory.MISSING_DEPENDENCY,
            confidence=0.70
        ),
        ErrorPattern(
            pattern=r"package .* does not exist",
            category=ErrorCategory.MISSING_DEPENDENCY,
            confidence=0.75
        ),
        ErrorPattern(
            pattern=r"';' expected",
            category=ErrorCategory.SYNTAX_ERROR,
            confidence=0.85
        ),
        ErrorPattern(
            pattern=r"illegal start of expression",
            category=ErrorCategory.SYNTAX_ERROR,
            confidence=0.80
        ),
        ErrorPattern(
            pattern=r"reached end of file while parsing",
            category=ErrorCategory.SYNTAX_ERROR,
            confidence=0.90
        ),
        ErrorPattern(
            pattern=r"Exception in thread",
            category=ErrorCategory.RUNTIME_EXCEPTION,
            confidence=0.95
        ),
        ErrorPattern(
            pattern=r"OutOfMemoryError",
            category=ErrorCategory.RESOURCE_LIMIT,
            confidence=0.95
        ),
        ErrorPattern(
            pattern=r"killed.*timeout",
            category=ErrorCategory.RESOURCE_LIMIT,
            confidence=0.90
        ),
    ]
    
    def __init__(self, version_mapper: Optional[VersionMapper] = None):
        """
        Initialize the ErrorClassifier.
        
        Args:
            version_mapper: VersionMapper instance for feature analysis
        """
        self.version_mapper = version_mapper or VersionMapper()
        self.all_patterns = self.VERSION_ERROR_PATTERNS + self.OTHER_ERROR_PATTERNS
    
    def analyze_error(self, error_message: str, java_version: int, code: Optional[str] = None) -> CompatibilityAnalysis:
        """
        Analyze an error message to determine if it's version-related.
        
        Args:
            error_message: The compilation or runtime error message
            java_version: The Java version being used
            code: Optional source code for additional analysis
            
        Returns:
            CompatibilityAnalysis with classification results
        """
        if not error_message or not error_message.strip():
            return CompatibilityAnalysis(
                is_version_issue=False,
                detected_features=[],
                required_version=None,
                error_category=ErrorCategory.UNKNOWN.value,
                confidence_score=0.0
            )
        
        # Find the best matching pattern
        best_match = self._find_best_pattern_match(error_message)
        
        if not best_match:
            # No pattern matched, try code analysis if available
            if code:
                return self._analyze_with_code(error_message, java_version, code)
            else:
                return CompatibilityAnalysis(
                    is_version_issue=False,
                    detected_features=[],
                    required_version=None,
                    error_category=ErrorCategory.UNKNOWN.value,
                    confidence_score=0.0
                )
        
        pattern, confidence = best_match
        
        # Determine if this is a version issue
        is_version_issue = pattern.category == ErrorCategory.VERSION_COMPATIBILITY
        
        # Collect detected features and required version
        detected_features = []
        required_version = None
        
        if is_version_issue:
            if pattern.java_feature:
                detected_features.append(pattern.java_feature)
                required_version = pattern.min_version or self.version_mapper.get_required_version(pattern.java_feature)
            elif code:
                # Try to detect features from code analysis
                feature_analysis = self.version_mapper.analyze_code_features(code)
                detected_features = feature_analysis.detected_features
                required_version = feature_analysis.required_version
        
        return CompatibilityAnalysis(
            is_version_issue=is_version_issue,
            detected_features=detected_features,
            required_version=required_version,
            error_category=pattern.category.value,
            confidence_score=confidence
        )
    
    def is_version_related(self, error_message: str) -> bool:
        """
        Quick check if an error message appears to be version-related.
        
        Args:
            error_message: The error message to check
            
        Returns:
            True if the error appears to be version-related
        """
        if not error_message:
            return False
        
        # Check against version-specific patterns only
        for pattern in self.VERSION_ERROR_PATTERNS:
            if re.search(pattern.pattern, error_message, re.IGNORECASE | re.MULTILINE):
                return True
        
        return False
    
    def suggest_minimum_version(self, detected_features: List[str]) -> int:
        """
        Suggest the minimum Java version needed for the detected features.
        
        Args:
            detected_features: List of detected Java features
            
        Returns:
            The minimum Java version required
        """
        return self.version_mapper.suggest_minimum_version(detected_features)
    
    def classify_error_category(self, error_message: str) -> Tuple[ErrorCategory, float]:
        """
        Classify an error message into a category.
        
        Args:
            error_message: The error message to classify
            
        Returns:
            Tuple of (ErrorCategory, confidence_score)
        """
        best_match = self._find_best_pattern_match(error_message)
        
        if best_match:
            pattern, confidence = best_match
            return pattern.category, confidence
        
        return ErrorCategory.UNKNOWN, 0.0
    
    def extract_version_info(self, error_message: str) -> Optional[Dict[str, int]]:
        """
        Extract version information from error messages.
        
        Args:
            error_message: The error message to analyze
            
        Returns:
            Dictionary with source/target version info, or None
        """
        version_info = {}
        
        # Extract source version
        source_match = re.search(r"-source (\d+)", error_message)
        if source_match:
            version_info['source_version'] = int(source_match.group(1))
        
        # Extract target version
        target_match = re.search(r"target release (\d+)", error_message)
        if target_match:
            version_info['target_version'] = int(target_match.group(1))
        
        # Extract required version
        requires_match = re.search(r"requires target release (\d+)", error_message)
        if requires_match:
            version_info['required_version'] = int(requires_match.group(1))
        
        return version_info if version_info else None
    
    def get_fix_suggestions(self, analysis: CompatibilityAnalysis, target_version: int) -> List[str]:
        """
        Get suggestions for fixing version compatibility issues.
        
        Args:
            analysis: The compatibility analysis result
            target_version: The target Java version
            
        Returns:
            List of fix suggestions
        """
        suggestions = []
        
        if not analysis.is_version_issue:
            return suggestions
        
        if analysis.required_version and analysis.required_version > target_version:
            suggestions.append(
                f"Upgrade to Java {analysis.required_version} or later to use these features"
            )
        
        for feature in analysis.detected_features:
            if feature == "var":
                suggestions.append("Replace 'var' with explicit type declarations")
            elif feature == "switch_expressions":
                suggestions.append("Convert switch expressions to traditional switch statements")
            elif feature == "text_blocks":
                suggestions.append("Replace text blocks with regular string concatenation")
            elif feature == "records":
                suggestions.append("Convert records to regular classes with constructors and getters")
            elif feature == "pattern_matching_instanceof":
                suggestions.append("Use traditional instanceof with explicit casting")
            elif feature == "lambda_expressions":
                suggestions.append("Replace lambda expressions with anonymous inner classes")
            elif feature == "method_references":
                suggestions.append("Replace method references with lambda expressions or anonymous classes")
        
        return suggestions
    
    def _find_best_pattern_match(self, error_message: str) -> Optional[Tuple[ErrorPattern, float]]:
        """
        Find the best matching error pattern for the given message.
        
        Args:
            error_message: The error message to match
            
        Returns:
            Tuple of (ErrorPattern, confidence) or None if no match
        """
        best_match = None
        best_confidence = 0.0
        
        for pattern in self.all_patterns:
            if re.search(pattern.pattern, error_message, re.IGNORECASE | re.MULTILINE):
                if pattern.confidence > best_confidence:
                    best_match = pattern
                    best_confidence = pattern.confidence
        
        return (best_match, best_confidence) if best_match else None
    
    def _analyze_with_code(self, error_message: str, java_version: int, code: str) -> CompatibilityAnalysis:
        """
        Analyze error using code analysis when pattern matching fails.
        
        Args:
            error_message: The error message
            java_version: The Java version being used
            code: The source code
            
        Returns:
            CompatibilityAnalysis based on code feature detection
        """
        feature_analysis = self.version_mapper.analyze_code_features(code)
        
        # Check if any detected features require a higher version
        is_version_issue = feature_analysis.required_version > java_version
        
        # Lower confidence since we're inferring from code rather than error patterns
        confidence = 0.6 if is_version_issue else 0.3
        
        return CompatibilityAnalysis(
            is_version_issue=is_version_issue,
            detected_features=feature_analysis.detected_features,
            required_version=feature_analysis.required_version if is_version_issue else None,
            error_category=ErrorCategory.VERSION_COMPATIBILITY.value if is_version_issue else ErrorCategory.UNKNOWN.value,
            confidence_score=confidence
        )