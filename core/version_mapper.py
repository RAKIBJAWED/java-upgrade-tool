"""
Version Mapper for Java Version Compatibility Fixer.

This module provides functionality to map Java language features to their minimum
required versions and analyze Java code to detect which features are being used.
"""

import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass


@dataclass
class FeatureDetection:
    """Result of analyzing code for Java language features."""
    detected_features: List[str]
    required_version: int
    feature_locations: Dict[str, List[int]]  # feature -> line numbers
    
    def __post_init__(self):
        if not self.detected_features:
            self.detected_features = []
        if not self.feature_locations:
            self.feature_locations = {}


class VersionMapper:
    """
    Maps Java language features to their minimum required versions and analyzes code.
    
    This class maintains a comprehensive mapping of Java language features to the
    minimum Java version required to use them, and provides methods to analyze
    Java source code to detect which features are being used.
    """
    
    # Comprehensive mapping of Java features to minimum required versions
    JAVA_FEATURES = {
        # Java 8 features (baseline)
        "lambda_expressions": 8,
        "method_references": 8,
        "default_methods": 8,
        "stream_api": 8,
        "optional": 8,
        "date_time_api": 8,
        
        # Java 9 features
        "modules": 9,
        "private_interface_methods": 9,
        "try_with_resources_improvements": 9,
        "diamond_operator_anonymous": 9,
        
        # Java 10 features
        "var": 10,
        "local_variable_type_inference": 10,
        
        # Java 11 features
        "string_methods_11": 11,  # isBlank(), lines(), strip(), etc.
        "files_methods_11": 11,   # Files.readString(), writeString()
        "http_client": 11,
        
        # Java 12 features
        "switch_expression_preview": 12,
        
        # Java 13 features
        "text_blocks_preview": 13,
        
        # Java 14 features
        "switch_expressions": 14,  # Standard (non-preview)
        "pattern_matching_instanceof_preview": 14,
        "records_preview": 14,
        "helpful_nullpointerexceptions": 14,
        
        # Java 15 features
        "text_blocks": 15,  # Standard (non-preview)
        "sealed_classes_preview": 15,
        
        # Java 16 features
        "records": 16,  # Standard (non-preview)
        "pattern_matching_instanceof": 16,  # Standard (non-preview)
        
        # Java 17 features
        "sealed_classes": 17,  # Standard (non-preview)
        "always_strict_floating_point": 17,
        
        # Java 18 features
        "utf8_by_default": 18,
        "simple_web_server": 18,
        
        # Java 19 features
        "virtual_threads_preview": 19,
        "pattern_matching_switch_preview": 19,
        "record_patterns_preview": 19,
        
        # Java 20 features
        "scoped_values_preview": 20,
        "record_patterns_preview_2": 20,
        "pattern_matching_switch_preview_2": 20,
        
        # Java 21 features
        "virtual_threads": 21,
        "pattern_matching_switch": 21,
        "record_patterns": 21,
        "string_templates_preview": 21,
        "sequenced_collections": 21,
    }
    
    # Regex patterns to detect features in code
    FEATURE_PATTERNS = {
        "var": [
            r'\bvar\s+\w+\s*=',  # var variable = ...
            r'\bvar\s+\w+\s*\(',  # var variable(
        ],
        "lambda_expressions": [
            r'\([^)]*\)\s*->',  # (params) -> 
            r'\w+\s*->',        # param ->
        ],
        "method_references": [
            r'\w+::\w+',        # Class::method
            r'this::\w+',       # this::method
            r'super::\w+',      # super::method
        ],
        "switch_expressions": [
            r'switch\s*\([^)]+\)\s*\{[^}]*yield\s+',  # switch with yield
            r'\w+\s*=\s*switch\s*\(',                 # assignment from switch
        ],
        "switch_expression_preview": [
            r'switch\s*\([^)]+\)\s*\{[^}]*->',  # switch with arrow syntax
        ],
        "text_blocks": [
            r'"""[\s\S]*?"""',  # Text blocks with triple quotes
        ],
        "text_blocks_preview": [
            r'"""[\s\S]*?"""',  # Same pattern, different version
        ],
        "records": [
            r'\brecord\s+\w+\s*\(',  # record declaration
        ],
        "records_preview": [
            r'\brecord\s+\w+\s*\(',  # Same pattern, preview version
        ],
        "pattern_matching_instanceof": [
            r'\binstanceof\s+\w+\s+\w+',  # instanceof with pattern variable
        ],
        "pattern_matching_instanceof_preview": [
            r'\binstanceof\s+\w+\s+\w+',  # Same pattern, preview version
        ],
        "sealed_classes": [
            r'\bsealed\s+(?:class|interface)',  # sealed class/interface
            r'\bpermits\s+',                    # permits clause
        ],
        "sealed_classes_preview": [
            r'\bsealed\s+(?:class|interface)',  # Same patterns, preview version
            r'\bpermits\s+',
        ],
        "pattern_matching_switch": [
            r'switch\s*\([^)]+\)\s*\{[^}]*case\s+\w+\s+\w+\s*->',  # case Type var ->
        ],
        "pattern_matching_switch_preview": [
            r'switch\s*\([^)]+\)\s*\{[^}]*case\s+\w+\s+\w+\s*->',  # Same pattern
        ],
        "record_patterns": [
            r'case\s+\w+\s*\([^)]*\)\s*->',  # case Record(pattern) ->
        ],
        "record_patterns_preview": [
            r'case\s+\w+\s*\([^)]*\)\s*->',  # Same pattern
        ],
        "string_templates_preview": [
            r'STR\."[^"]*\\{[^}]+}[^"]*"',  # STR."text \{expr} text"
        ],
        "virtual_threads": [
            r'Thread\.ofVirtual\(\)',
            r'Thread\.startVirtualThread\(',
        ],
        "virtual_threads_preview": [
            r'Thread\.ofVirtual\(\)',
            r'Thread\.startVirtualThread\(',
        ],
        "stream_api": [
            r'\.stream\(\)',
            r'Stream\.',
            r'Collectors\.',
        ],
        "optional": [
            r'Optional\.',
            r'OptionalInt\.',
            r'OptionalLong\.',
            r'OptionalDouble\.',
        ],
        "modules": [
            r'module\s+[\w.]+\s*\{',  # module declaration
            r'requires\s+[\w.]+',     # requires directive
            r'exports\s+[\w.]+',      # exports directive
        ],
        "try_with_resources_improvements": [
            r'try\s*\(\s*\w+\s*\)\s*\{',  # try with effectively final variable
        ],
        "string_methods_11": [
            r'\.isBlank\(\)',
            r'\.lines\(\)',
            r'\.strip\(\)',
            r'\.stripLeading\(\)',
            r'\.stripTrailing\(\)',
            r'\.repeat\(',
        ],
        "http_client": [
            r'HttpClient\.',
            r'HttpRequest\.',
            r'HttpResponse\.',
        ],
        "sequenced_collections": [
            r'SequencedCollection',
            r'SequencedSet',
            r'SequencedMap',
            r'\.addFirst\(',
            r'\.addLast\(',
            r'\.getFirst\(\)',
            r'\.getLast\(\)',
        ],
    }
    
    def __init__(self):
        """Initialize the VersionMapper."""
        pass
    
    def get_required_version(self, feature: str) -> int:
        """
        Get the minimum Java version required for a specific feature.
        
        Args:
            feature: The name of the Java language feature
            
        Returns:
            The minimum Java version required, or 8 if feature is unknown
        """
        return self.JAVA_FEATURES.get(feature, 8)
    
    def get_features_for_version(self, version: int) -> List[str]:
        """
        Get all Java features available in a specific version.
        
        Args:
            version: The Java version number
            
        Returns:
            List of feature names available in that version or earlier
        """
        return [
            feature for feature, required_version in self.JAVA_FEATURES.items()
            if required_version <= version
        ]
    
    def get_features_requiring_version(self, version: int) -> List[str]:
        """
        Get all Java features that require exactly the specified version.
        
        Args:
            version: The Java version number
            
        Returns:
            List of feature names that were introduced in that version
        """
        return [
            feature for feature, required_version in self.JAVA_FEATURES.items()
            if required_version == version
        ]
    
    def analyze_code_features(self, code: str) -> FeatureDetection:
        """
        Analyze Java source code to detect which language features are being used.
        
        Args:
            code: The Java source code to analyze
            
        Returns:
            FeatureDetection object containing detected features and required version
        """
        detected_features = []
        feature_locations = {}
        lines = code.split('\n')
        
        # Check each feature pattern against the code
        for feature, patterns in self.FEATURE_PATTERNS.items():
            feature_found = False
            locations = []
            
            for pattern in patterns:
                # Check each line for the pattern
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        feature_found = True
                        locations.append(line_num)
                
                # Also check the entire code as one string for multi-line patterns
                if re.search(pattern, code, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                    feature_found = True
                    if not locations:  # Only add if we haven't found line-specific matches
                        locations.append(0)  # 0 indicates multi-line match
            
            if feature_found:
                detected_features.append(feature)
                feature_locations[feature] = list(set(locations))  # Remove duplicates
        
        # Calculate the minimum required version
        required_version = 8  # Default to Java 8
        if detected_features:
            required_version = max(
                self.get_required_version(feature) for feature in detected_features
            )
        
        return FeatureDetection(
            detected_features=detected_features,
            required_version=required_version,
            feature_locations=feature_locations
        )
    
    def is_compatible_with_version(self, code: str, target_version: int) -> bool:
        """
        Check if the given code is compatible with the target Java version.
        
        Args:
            code: The Java source code to check
            target_version: The target Java version
            
        Returns:
            True if the code is compatible, False otherwise
        """
        analysis = self.analyze_code_features(code)
        return analysis.required_version <= target_version
    
    def get_incompatible_features(self, code: str, target_version: int) -> List[str]:
        """
        Get a list of features in the code that are incompatible with the target version.
        
        Args:
            code: The Java source code to check
            target_version: The target Java version
            
        Returns:
            List of incompatible feature names
        """
        analysis = self.analyze_code_features(code)
        return [
            feature for feature in analysis.detected_features
            if self.get_required_version(feature) > target_version
        ]
    
    def suggest_minimum_version(self, detected_features: List[str]) -> int:
        """
        Suggest the minimum Java version needed for the given features.
        
        Args:
            detected_features: List of detected feature names
            
        Returns:
            The minimum Java version that supports all features
        """
        if not detected_features:
            return 8
        
        return max(
            self.get_required_version(feature) for feature in detected_features
        )
    
    def get_version_migration_path(self, from_version: int, to_version: int) -> List[Dict[str, any]]:
        """
        Get a migration path showing what features become available between versions.
        
        Args:
            from_version: Starting Java version
            to_version: Target Java version
            
        Returns:
            List of dictionaries with version and new features
        """
        migration_path = []
        
        for version in range(from_version + 1, to_version + 1):
            new_features = self.get_features_requiring_version(version)
            if new_features:
                migration_path.append({
                    'version': version,
                    'new_features': new_features
                })
        
        return migration_path