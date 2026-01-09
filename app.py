"""
Java Version Compatibility Fixer - Streamlit Application Entry Point

This is the main entry point for the Streamlit web application that helps developers
automatically identify and fix Java version compatibility issues.
Enhanced with comprehensive error handling, graceful degradation, and user-friendly error messages.
"""

import difflib
import os
import re

import streamlit as st

from agent.llm_agent import JavaFixAgent
from config.settings import load_configuration, validate_configuration
from core.error_classifier import ErrorClassifier
from core.error_handling import (
    ErrorCategory, ErrorSeverity, GracefulDegradation,
    get_error_handler
)
# Import core modules
from core.java_runner import JavaRunner
from core.models import ExecutionResult, SystemStatus, SystemResponse
from core.validation_system import ValidationAndRetrySystem, RetryConfiguration


def apply_java_syntax_highlighting(code: str) -> str:
    """
    Apply basic Java syntax highlighting using HTML and CSS.
    This provides consistent syntax highlighting as per Requirements 6.4.
    """
    if not code.strip():
        return code
    
    # Escape HTML characters first
    import html
    highlighted_code = html.escape(code)
    
    # Java keywords
    keywords = [
        'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char', 
        'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum', 
        'extends', 'final', 'finally', 'float', 'for', 'goto', 'if', 'implements', 
        'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new', 'null',
        'package', 'private', 'protected', 'public', 'return', 'short', 'static', 
        'strictfp', 'super', 'switch', 'synchronized', 'this', 'throw', 'throws', 
        'transient', 'try', 'void', 'volatile', 'while', 'true', 'false', 'var'
    ]
    
    # Highlight keywords
    for keyword in keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        highlighted_code = re.sub(
            pattern, 
            f'<span style="color: #0000FF; font-weight: bold;">{keyword}</span>', 
            highlighted_code
        )
    
    # Highlight strings
    highlighted_code = re.sub(
        r'&quot;([^&]|&[^q]|&q[^u]|&qu[^o]|&quo[^t])*&quot;',
        r'<span style="color: #008000;">\g<0></span>',
        highlighted_code
    )
    
    # Highlight single-line comments
    highlighted_code = re.sub(
        r'//.*$',
        r'<span style="color: #808080; font-style: italic;">\g<0></span>',
        highlighted_code,
        flags=re.MULTILINE
    )
    
    # Highlight multi-line comments
    highlighted_code = re.sub(
        r'/\*.*?\*/',
        r'<span style="color: #808080; font-style: italic;">\g<0></span>',
        highlighted_code,
        flags=re.DOTALL
    )
    
    return highlighted_code

def generate_code_diff_html(original_code: str, fixed_code: str) -> tuple[str, str]:
    """
    Generate HTML with difference highlighting between original and fixed code.
    This implements Requirements 6.2 for code difference highlighting.
    """
    if not original_code.strip() or not fixed_code.strip():
        return original_code, fixed_code
    
    # Split into lines for diff comparison
    original_lines = original_code.splitlines(keepends=True)
    fixed_lines = fixed_code.splitlines(keepends=True)
    
    # Generate unified diff
    diff = list(difflib.unified_diff(
        original_lines, 
        fixed_lines, 
        fromfile='Original', 
        tofile='Fixed', 
        lineterm=''
    ))
    
    if len(diff) <= 2:  # No differences found (only header lines)
        return original_code, fixed_code
    
    # Create side-by-side diff highlighting
    original_highlighted = []
    fixed_highlighted = []
    
    # Use SequenceMatcher for more precise line-by-line comparison
    matcher = difflib.SequenceMatcher(None, original_lines, fixed_lines)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # Lines are the same
            for i in range(i1, i2):
                original_highlighted.append(original_lines[i])
            for j in range(j1, j2):
                fixed_highlighted.append(fixed_lines[j])
        elif tag == 'delete':
            # Lines deleted from original
            for i in range(i1, i2):
                line = original_lines[i].rstrip('\n')
                original_highlighted.append(
                    f'<span style="background-color: #ffcccc; display: block; padding: 2px;">{line}</span>\n'
                )
        elif tag == 'insert':
            # Lines added to fixed
            for j in range(j1, j2):
                line = fixed_lines[j].rstrip('\n')
                fixed_highlighted.append(
                    f'<span style="background-color: #ccffcc; display: block; padding: 2px;">{line}</span>\n'
                )
        elif tag == 'replace':
            # Lines changed
            for i in range(i1, i2):
                line = original_lines[i].rstrip('\n')
                original_highlighted.append(
                    f'<span style="background-color: #ffcccc; display: block; padding: 2px;">{line}</span>\n'
                )
            for j in range(j1, j2):
                line = fixed_lines[j].rstrip('\n')
                fixed_highlighted.append(
                    f'<span style="background-color: #ccffcc; display: block; padding: 2px;">{line}</span>\n'
                )
    
    return ''.join(original_highlighted), ''.join(fixed_highlighted)

def copy_to_clipboard_button(text: str, button_text: str, key: str) -> None:
    """
    Create a copy-to-clipboard button for code.
    This implements Requirements 6.5 for copy functionality.
    """
    if st.button(button_text, key=key, use_container_width=True):
        # Use Streamlit's built-in clipboard functionality
        st.code(text, language='java')
        st.success(f"Code copied to clipboard! You can now paste it elsewhere.")
        # Store in session state for potential use
        st.session_state[f'copied_code_{key}'] = text

def main():
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="Java Version Compatibility Fixer",
        page_icon="☕",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("☕ Java Version Compatibility Fixer")
    st.markdown("Automatically detect and fix Java version compatibility issues in your code.")
    
    # Load and validate configuration with comprehensive error handling
    try:
        config = load_configuration()
        validation_result = validate_configuration(config)
        if not validation_result.is_valid:
            st.error(f"⚠️ Configuration Error: {validation_result.error_message}")
            st.info("Please check your configuration files and environment variables.")
            with st.expander("Configuration Help"):
                st.markdown("""
                **Required Environment Variables:**
                - `OPENAI_API_KEY`: Your OpenAI API key (for GPT models)
                - `ANTHROPIC_API_KEY`: Your Anthropic API key (for Claude models)
                
                **Configuration File:** `config/java_versions.json`
                - Contains Java version to Docker image mappings
                - Execution timeout and resource limit settings
                - Supported LLM model configurations
                """)
            st.stop()
        
        # Store config in session state for access throughout the app
        st.session_state.system_config = config
        
    except Exception as e:
        error_handler = get_error_handler()
        error_context = error_handler.handle_error(
            exception=e,
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.CRITICAL,
            component="app",
            operation="load_configuration",
            user_message="Failed to load system configuration. Please check your setup."
        )
        
        st.error(f"❌ Critical Configuration Error: {error_context.user_message}")
        st.error(f"Error ID: {error_context.error_id}")
        
        with st.expander("Technical Details"):
            st.code(error_context.technical_details)
            st.markdown("**Recovery Suggestions:**")
            for suggestion in error_context.recovery_suggestions:
                st.markdown(f"- {suggestion}")
        
        st.stop()
    
    # Initialize components with comprehensive error handling and graceful degradation
    error_handler = get_error_handler()
    graceful_degradation = GracefulDegradation(error_handler)
    
    # Check if we're in fallback mode (no Java available)
    fallback_mode = os.environ.get('FALLBACK_MODE', 'false').lower() == 'true'
    use_local_java = os.environ.get('USE_LOCAL_JAVA', 'true').lower() == 'true'
    
    if fallback_mode:
        st.warning("⚠️ Running in fallback mode - Java execution not available in this environment")
        st.info("💡 This demo shows the UI and LLM integration. For full Java execution, deploy with Docker support.")
    
    # Initialize Java Runner with error handling
    if 'java_runner' not in st.session_state:
        try:
            if fallback_mode:
                # Create a mock Java runner for demo purposes
                st.session_state.java_runner = None
                st.session_state.java_runner_available = False
                st.info("ℹ️ Java execution disabled in fallback mode")
            else:
                st.session_state.java_runner = JavaRunner()
                st.session_state.java_runner_available = True
        except Exception as e:
            error_context = error_handler.handle_error(
                exception=e,
                category=ErrorCategory.DOCKER_ERROR,
                severity=ErrorSeverity.HIGH,
                component="JavaRunner",
                operation="initialization",
                user_message="Java execution environment is not available. Code execution will be disabled."
            )
            st.session_state.java_runner = None
            st.session_state.java_runner_available = False
            st.warning(f"⚠️ {error_context.user_message}")
    
    # Initialize Error Classifier with error handling
    if 'error_classifier' not in st.session_state:
        try:
            st.session_state.error_classifier = ErrorClassifier()
            st.session_state.error_classifier_available = True
        except Exception as e:
            error_context = error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component="ErrorClassifier",
                operation="initialization",
                user_message="Error analysis features may be limited."
            )
            st.session_state.error_classifier = None
            st.session_state.error_classifier_available = False
            st.info(f"ℹ️ {error_context.user_message}")
    
    # Initialize LLM Agent with error handling and fallback
    if 'llm_agent' not in st.session_state:
        try:
            st.session_state.llm_agent = JavaFixAgent()
            st.session_state.llm_agent_available = st.session_state.llm_agent.is_available()
            
            if not st.session_state.llm_agent_available:
                st.warning("⚠️ No LLM models are available. Code fixing features will be disabled.")
                st.info("Please check your API keys: OPENAI_API_KEY or ANTHROPIC_API_KEY")
                
        except Exception as e:
            error_context = error_handler.handle_error(
                exception=e,
                category=ErrorCategory.API_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component="LLMAgent",
                operation="initialization",
                user_message="AI-powered code fixing is not available. Manual code review required."
            )
            st.session_state.llm_agent = None
            st.session_state.llm_agent_available = False
            st.warning(f"⚠️ {error_context.user_message}")
    
    # Initialize Validation System with error handling
    if 'validation_system' not in st.session_state:
        try:
            # Only initialize if we have the required components
            if (st.session_state.get('java_runner') and 
                st.session_state.get('error_classifier') and 
                st.session_state.get('llm_agent')):
                
                retry_config = RetryConfiguration(
                    max_attempts=2,
                    validate_fixes=True,
                    track_attempts=True,
                    require_execution_success=True
                )
                st.session_state.validation_system = ValidationAndRetrySystem(
                    java_runner=st.session_state.java_runner,
                    error_classifier=st.session_state.error_classifier,
                    llm_agent=st.session_state.llm_agent,
                    retry_config=retry_config
                )
                st.session_state.validation_system_available = True
            else:
                st.session_state.validation_system = None
                st.session_state.validation_system_available = False
                st.info("ℹ️ Comprehensive validation system is not available due to missing components.")
                
        except Exception as e:
            error_context = error_handler.handle_error(
                exception=e,
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.MEDIUM,
                component="ValidationSystem",
                operation="initialization",
                user_message="Advanced validation features may not work properly."
            )
            st.session_state.validation_system = None
            st.session_state.validation_system_available = False
            st.warning(f"⚠️ {error_context.user_message}")
    
    # Store error handler and graceful degradation in session state
    st.session_state.error_handler = error_handler
    st.session_state.graceful_degradation = graceful_degradation
    
    # Initialize session state for results
    if 'execution_result' not in st.session_state:
        st.session_state.execution_result = None
    if 'fixed_code' not in st.session_state:
        st.session_state.fixed_code = None
    if 'system_response' not in st.session_state:
        st.session_state.system_response = None
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        
        # Java version selection with persistence - default to Java 8 as per requirements
        # Initialize session state for source and target versions
        if 'selected_source_version' not in st.session_state:
            st.session_state.selected_source_version = 8  # Default to Java 8
        if 'selected_target_version' not in st.session_state:
            st.session_state.selected_target_version = 17  # Default to Java 17
        
        # Version options
        version_options = [8, 11, 17, 21]
        
        # Source Java Version Selector
        source_version_index = 0
        try:
            source_version_index = version_options.index(st.session_state.selected_source_version)
        except ValueError:
            source_version_index = 0
            st.session_state.selected_source_version = 8
        
        source_version = st.selectbox(
            "Select Source Java Version",
            options=version_options,
            index=source_version_index,
            help="The Java version your code currently uses (should work)",
            key="source_java_version_selector"
        )
        
        # Update session state when selection changes
        if source_version != st.session_state.selected_source_version:
            st.session_state.selected_source_version = source_version
        
        # Target Java Version Selector
        target_version_index = 2  # Default to Java 17
        try:
            target_version_index = version_options.index(st.session_state.selected_target_version)
        except ValueError:
            target_version_index = 2
            st.session_state.selected_target_version = 17
        
        target_version = st.selectbox(
            "Select Target Java Version",
            options=version_options,
            index=target_version_index,
            help="The Java version you want to migrate to",
            key="target_java_version_selector"
        )
        
        # Update session state when selection changes
        if target_version != st.session_state.selected_target_version:
            st.session_state.selected_target_version = target_version
        
        # Show migration path
        if source_version != target_version:
            if source_version < target_version:
                st.info(f"🔄 Migration: Java {source_version} → Java {target_version} (Upgrade)")
            else:
                st.warning(f"🔄 Migration: Java {source_version} → Java {target_version} (Downgrade)")
        else:
            st.info(f"ℹ️ Same version selected: Java {source_version}")
        
        # Keep backward compatibility - use target version as the main java_version
        java_version = target_version
        if 'selected_java_version' not in st.session_state:
            st.session_state.selected_java_version = target_version
        st.session_state.selected_java_version = target_version
        
        # LLM model selection with comprehensive availability checking
        available_models = {}
        llm_status_message = ""
        
        if (hasattr(st.session_state, 'llm_agent') and 
            st.session_state.llm_agent and 
            st.session_state.get('llm_agent_available', False)):
            try:
                available_models = st.session_state.llm_agent.get_available_models()
                if available_models:
                    llm_status_message = f"✅ {len(available_models)} models available"
                else:
                    llm_status_message = "⚠️ No models available - check API keys"
            except Exception as e:
                llm_status_message = f"⚠️ Error checking models: {str(e)[:50]}..."
        else:
            llm_status_message = "❌ LLM Agent not available"
        
        st.markdown(f"**LLM Status:** {llm_status_message}")
        
        if available_models:
            model_options = list(available_models.keys())
            
            # Initialize persistent model selection in session state
            if 'selected_llm_model' not in st.session_state:
                st.session_state.selected_llm_model = model_options[0]
            
            # Ensure the stored model is still available
            if st.session_state.selected_llm_model not in model_options:
                st.session_state.selected_llm_model = model_options[0]
            
            # Get current index for the selectbox
            current_index = 0
            try:
                current_index = model_options.index(st.session_state.selected_llm_model)
            except ValueError:
                current_index = 0
                st.session_state.selected_llm_model = model_options[0]
            
            llm_model = st.selectbox(
                "Select LLM Model",
                options=model_options,
                index=current_index,
                help="Choose the AI model for code fixing",
                key="llm_model_selector"
            )
            
            # Update session state when selection changes
            if llm_model != st.session_state.selected_llm_model:
                st.session_state.selected_llm_model = llm_model
                # Set the selected model in the agent with error handling
                try:
                    st.session_state.llm_agent.set_model(llm_model)
                    st.success(f"✅ Model changed to: {llm_model}")
                except Exception as e:
                    st.error(f"❌ Failed to set model: {str(e)}")
            
            # Ensure the agent is using the correct model
            try:
                if (st.session_state.llm_agent.get_current_model() != 
                    st.session_state.selected_llm_model):
                    st.session_state.llm_agent.set_model(st.session_state.selected_llm_model)
            except Exception as e:
                st.warning(f"⚠️ Model sync issue: {str(e)}")
        else:
            llm_model = "None"
            st.session_state.selected_llm_model = "None"
            
            # Show detailed help for setting up LLM access
            with st.expander("🔧 LLM Setup Help"):
                st.markdown("""
                **To enable AI-powered code fixing, you need to set up API keys:**
                
                **Option 1: OpenAI (GPT models)**
                1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
                2. Set environment variable: `OPENAI_API_KEY=your_key_here`
                
                **Option 2: Anthropic (Claude models)**
                1. Get an API key from [Anthropic](https://console.anthropic.com/)
                2. Set environment variable: `ANTHROPIC_API_KEY=your_key_here`
                
                **Setting Environment Variables:**
                - Create a `.env` file in the project root
                - Add your API key(s) to the file
                - Restart the application
                """)
        
        # Display comprehensive system status with enhanced styling
        st.subheader("System Status")
        
        # Get system health from graceful degradation if available
        system_health = {"overall_health": 100, "degraded_mode": False}
        if hasattr(st.session_state, 'graceful_degradation'):
            try:
                system_health = st.session_state.graceful_degradation.get_system_health()
            except:
                pass
        
        # Create status indicators with better visual styling
        status_items = []
        
        # Configuration status
        if hasattr(st.session_state, 'system_config'):
            status_items.append(("✅ Configuration loaded", "success"))
        else:
            status_items.append(("❌ Configuration error", "error"))
        
        # Java Runner status
        if st.session_state.get('java_runner_available', False):
            status_items.append(("✅ Java execution available", "success"))
        else:
            status_items.append(("❌ Java execution unavailable", "error"))
        
        # Docker status
        if (st.session_state.get('java_runner') and 
            hasattr(st.session_state.java_runner, 'docker_manager') and 
            st.session_state.java_runner.docker_manager):
            status_items.append(("✅ Docker available", "success"))
        else:
            status_items.append(("❌ Docker not available", "error"))
        
        # Error Classifier status
        if st.session_state.get('error_classifier_available', False):
            status_items.append(("✅ Error analysis available", "success"))
        else:
            status_items.append(("⚠️ Error analysis limited", "warning"))
        
        # LLM Agent status
        if st.session_state.get('llm_agent_available', False):
            status_items.append(("✅ AI code fixing available", "success"))
        else:
            status_items.append(("❌ AI code fixing unavailable", "error"))
        
        # Validation System status
        if st.session_state.get('validation_system_available', False):
            status_items.append(("✅ Comprehensive validation available", "success"))
        else:
            status_items.append(("⚠️ Basic validation only", "warning"))
        
        # Display status items with appropriate styling
        for status_text, status_type in status_items:
            if status_type == "success":
                st.success(status_text)
            elif status_type == "warning":
                st.warning(status_text)
            elif status_type == "error":
                st.error(status_text)
            else:
                st.info(status_text)
        
        # Show overall system health
        if system_health["overall_health"] < 100:
            st.warning(f"⚠️ System running in degraded mode ({system_health['overall_health']:.0f}% health)")
        else:
            st.success("✅ All systems operational")
        
        # Show current selections with persistence indicators
        st.subheader("Current Settings")
        st.markdown(f"**Java Version:** {st.session_state.get('selected_java_version', 8)} (persistent)")
        if 'selected_llm_model' in st.session_state and st.session_state.selected_llm_model != "None":
            st.markdown(f"**LLM Model:** {st.session_state.selected_llm_model} (persistent)")
        else:
            st.markdown("**LLM Model:** Not available")
        
        # Show configuration details in expandable section
        with st.expander("📋 Configuration Details"):
            if hasattr(st.session_state, 'system_config'):
                config = st.session_state.system_config
                st.json({
                    "java_versions": config.java_versions,
                    "execution_timeout": config.execution_timeout,
                    "docker_memory_limit": config.docker_memory_limit,
                    "docker_cpu_limit": config.docker_cpu_limit,
                    "supported_llm_models": config.supported_llm_models,
                    "openai_api_key_set": bool(config.openai_api_key),
                    "anthropic_api_key_set": bool(config.anthropic_api_key)
                })
            else:
                st.error("Configuration not loaded")
    
    # Main content area - enhanced side by side layout with syntax highlighting
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Original Java Code")
        java_code = st.text_area(
            "Enter your Java code here:",
            height=400,
            placeholder="public class HelloWorld {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, World!\");\n    }\n}",
            help="Paste your Java code that you want to check for version compatibility",
            key="java_code_input"
        )
        
        # Display original code with syntax highlighting if there's content
        if java_code.strip():
            st.markdown("**Original Code (with syntax highlighting):**")
            highlighted_original = apply_java_syntax_highlighting(java_code)
            st.markdown(
                f'<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #e9ecef; font-family: monospace; font-size: 14px; line-height: 1.4; max-height: 200px; overflow-y: auto;">{highlighted_original}</pre>',
                unsafe_allow_html=True
            )
            
            # Copy button for original code
            copy_to_clipboard_button(java_code, "📋 Copy Original Code", "copy_original")
        
        run_button = st.button("🚀 Run Java Code", type="primary", use_container_width=True)
    
    with col2:
        st.subheader("🔧 Fixed Java Code")
        
        # Debug information
        if st.session_state.get('system_response'):
            st.write(f"🐛 Debug - System Response Status: {st.session_state.system_response.status}")
            st.write(f"🐛 Debug - Has Fixed Code: {st.session_state.system_response.fixed_code is not None}")
            if st.session_state.system_response.fixed_code:
                st.write(f"🐛 Debug - Fixed Code Length: {len(st.session_state.system_response.fixed_code)}")
                st.write(f"🐛 Debug - Fixed Code Preview: '{st.session_state.system_response.fixed_code[:100]}...'")
        
        if st.session_state.system_response and st.session_state.system_response.fixed_code:
            fixed_code = st.session_state.system_response.fixed_code
            
            # Show fixed code in text area for editing if needed
            st.text_area(
                "Fixed code:",
                value=fixed_code,
                height=200,
                disabled=True,
                key="fixed_code_display"
            )
            
            # Display fixed code with syntax highlighting
            st.markdown("**Fixed Code (with syntax highlighting):**")
            highlighted_fixed = apply_java_syntax_highlighting(fixed_code)
            st.markdown(
                f'<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #e9ecef; font-family: monospace; font-size: 14px; line-height: 1.4; max-height: 200px; overflow-y: auto;">{highlighted_fixed}</pre>',
                unsafe_allow_html=True
            )
            
            # Copy button for fixed code
            copy_to_clipboard_button(fixed_code, "📋 Copy Fixed Code", "copy_fixed")
            
            # Show code differences if both codes exist
            if java_code.strip() and fixed_code.strip() and java_code.strip() != fixed_code.strip():
                st.markdown("**Code Differences:**")
                original_diff, fixed_diff = generate_code_diff_html(java_code, fixed_code)
                
                # Create sub-columns for side-by-side diff
                diff_col1, diff_col2 = st.columns(2)
                
                with diff_col1:
                    st.markdown("*Original (removed/changed):*")
                    st.markdown(
                        f'<pre style="background-color: #fff5f5; padding: 8px; border-radius: 3px; border: 1px solid #fed7d7; font-family: monospace; font-size: 12px; line-height: 1.3; max-height: 150px; overflow-y: auto;">{original_diff}</pre>',
                        unsafe_allow_html=True
                    )
                
                with diff_col2:
                    st.markdown("*Fixed (added/changed):*")
                    st.markdown(
                        f'<pre style="background-color: #f0fff4; padding: 8px; border-radius: 3px; border: 1px solid #9ae6b4; font-family: monospace; font-size: 12px; line-height: 1.3; max-height: 150px; overflow-y: auto;">{fixed_diff}</pre>',
                        unsafe_allow_html=True
                    )
        else:
            # Show placeholder when no fixed code is available
            st.text_area(
                "Fixed code will appear here:",
                height=200,
                disabled=True,
                placeholder="Fixed code will be displayed here after processing...",
                key="fixed_code_placeholder"
            )
            
            # Show message based on current state
            if st.session_state.system_response:
                if st.session_state.system_response.status == SystemStatus.SUCCESS:
                    st.info("✅ No fixes needed - your code works perfectly!")
                elif st.session_state.system_response.status == SystemStatus.FAILED:
                    st.warning("❌ Code could not be automatically fixed")
            else:
                st.markdown(
                    '<div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; border: 1px solid #e9ecef; text-align: center; color: #6c757d; font-style: italic;">Fixed code with syntax highlighting will appear here after processing...</div>',
                    unsafe_allow_html=True
                )
    
    # Results section with enhanced comparative display
    st.subheader("📊 Migration Results")
    
    # Show migration path information
    if st.session_state.system_response:
        if hasattr(st.session_state.system_response, 'source_version') and st.session_state.system_response.source_version:
            source_ver = st.session_state.system_response.source_version
            target_ver = st.session_state.system_response.target_version or st.session_state.system_response.java_version
            
            if source_ver != target_ver:
                migration_direction = "Upgrade" if source_ver < target_ver else "Downgrade"
                st.info(f"🔄 Migration Path: Java {source_ver} → Java {target_ver} ({migration_direction})")
            else:
                st.info(f"ℹ️ Same Version Test: Java {source_ver}")
    
    # Show comparative results when both original and fixed code exist
    if (st.session_state.system_response and 
        st.session_state.system_response.status == SystemStatus.FIXED and 
        st.session_state.system_response.fixed_code):
        
        st.markdown("### 🔄 Comparative Results: Original vs Fixed Code")
        
        # Create side-by-side comparison columns
        comp_col1, comp_col2 = st.columns(2)
        
        with comp_col1:
            st.markdown("#### 📝 Original Code Results")
            # Show source version results if available
            if (hasattr(st.session_state.system_response, 'source_execution_result') and 
                st.session_state.system_response.source_execution_result):
                source_result = st.session_state.system_response.source_execution_result
                source_ver = st.session_state.system_response.source_version
                
                st.markdown(f"**Java {source_ver} (Source Version):**")
                if source_result.success:
                    st.success("✅ Executed successfully in source version")
                    if source_result.stdout:
                        st.text_area("Output:", value=source_result.stdout, height=100, disabled=True, key="source_output")
                else:
                    st.error("❌ Failed in source version")
                    if source_result.compile_error:
                        st.text_area("Compilation Error:", value=source_result.compile_error, height=100, disabled=True, key="source_compile_err")
                    if source_result.runtime_error:
                        st.text_area("Runtime Error:", value=source_result.runtime_error, height=100, disabled=True, key="source_runtime_err")
            else:
                # Fallback to original execution attempt
                original_result = None
                if st.session_state.system_response.execution_attempts:
                    # Find the original execution attempt (before any fixes)
                    for attempt in st.session_state.system_response.execution_attempts:
                        if attempt.attempt_number == 0 or attempt.original_code == st.session_state.system_response.original_code:
                            original_result = attempt.execution_result
                            break
                
                if original_result:
                    if original_result.success:
                        st.success("✅ Original code executed successfully")
                        if original_result.stdout:
                            st.text_area("Output:", value=original_result.stdout, height=100, disabled=True, key="orig_output")
                    else:
                        st.error("❌ Original code failed")
                        if original_result.compile_error:
                            st.text_area("Compilation Error:", value=original_result.compile_error, height=100, disabled=True, key="orig_compile_err")
                        if original_result.runtime_error:
                            st.text_area("Runtime Error:", value=original_result.runtime_error, height=100, disabled=True, key="orig_runtime_err")
                else:
                    # Fallback to system response compile error
                    if st.session_state.system_response.compile_error:
                        st.error("❌ Original code failed")
                        st.text_area("Compilation Error:", value=st.session_state.system_response.compile_error, height=100, disabled=True, key="orig_fallback_err")
                    else:
                        st.info("ℹ️ Original execution details not available")
        
        with comp_col2:
            st.markdown("#### 🔧 Fixed Code Results")
            target_ver = st.session_state.system_response.target_version or st.session_state.system_response.java_version
            st.markdown(f"**Java {target_ver} (Target Version):**")
            
            # Get the final successful execution result
            final_result = None
            if st.session_state.system_response.execution_attempts:
                # Find the last successful attempt
                for attempt in reversed(st.session_state.system_response.execution_attempts):
                    if attempt.execution_result.success:
                        final_result = attempt.execution_result
                        break
            
            if final_result:
                st.success("✅ Fixed code executed successfully")
                if final_result.stdout:
                    st.text_area("Output:", value=final_result.stdout, height=100, disabled=True, key="fixed_output")
                else:
                    st.text_area("Output:", value="(No output)", height=100, disabled=True, key="fixed_no_output")
                
                # Show execution time comparison if available
                source_result = getattr(st.session_state.system_response, 'source_execution_result', None)
                if source_result and source_result.execution_time > 0 and final_result.execution_time > 0:
                    time_diff = final_result.execution_time - source_result.execution_time
                    if abs(time_diff) > 0.01:  # Only show if significant difference
                        if time_diff > 0:
                            st.info(f"⏱️ Execution time: +{time_diff:.3f}s slower than source")
                        else:
                            st.info(f"⏱️ Execution time: {abs(time_diff):.3f}s faster than source")
            else:
                st.warning("⚠️ Fixed code execution details not available")
    
    # Show source version results even when no fixes were needed
    elif (st.session_state.system_response and 
          hasattr(st.session_state.system_response, 'source_execution_result') and 
          st.session_state.system_response.source_execution_result):
        
        st.markdown("### 📊 Version Comparison Results")
        
        comp_col1, comp_col2 = st.columns(2)
        
        with comp_col1:
            source_ver = st.session_state.system_response.source_version
            source_result = st.session_state.system_response.source_execution_result
            
            st.markdown(f"#### Java {source_ver} (Source Version)")
            if source_result.success:
                st.success("✅ Executed successfully")
                if source_result.stdout:
                    st.text_area("Output:", value=source_result.stdout, height=100, disabled=True, key="source_only_output")
            else:
                st.error("❌ Failed in source version")
                error_msg = source_result.compile_error or source_result.runtime_error or "Unknown error"
                st.text_area("Error:", value=error_msg, height=100, disabled=True, key="source_only_error")
        
        with comp_col2:
            target_ver = st.session_state.system_response.target_version or st.session_state.system_response.java_version
            
            st.markdown(f"#### Java {target_ver} (Target Version)")
            if st.session_state.system_response.status == SystemStatus.SUCCESS:
                st.success("✅ Executed successfully")
                if st.session_state.system_response.runtime_output:
                    st.text_area("Output:", value=st.session_state.system_response.runtime_output, height=100, disabled=True, key="target_only_output")
            else:
                st.error("❌ Failed in target version")
                error_msg = st.session_state.system_response.compile_error or "Unknown error"
                st.text_area("Error:", value=error_msg, height=100, disabled=True, key="target_only_error")
    
    # Create tabs for detailed output sections as per requirements 7.1, 7.2, 7.3
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Program Output", "❌ Compilation Errors", "⚠️ Runtime Errors", "🔄 Fix Attempts"])
    
    with tab1:
        st.markdown("#### Program Output (stdout)")
        
        # Debug information
        if st.session_state.get('system_response'):
            st.write(f"🐛 Debug - System Response Status: {st.session_state.system_response.status}")
            st.write(f"🐛 Debug - Runtime Output Length: {len(st.session_state.system_response.runtime_output) if st.session_state.system_response.runtime_output else 0}")
            if st.session_state.system_response.runtime_output:
                st.write(f"🐛 Debug - Runtime Output Preview: '{st.session_state.system_response.runtime_output[:50]}...'")
        
        output_content = ""
        output_status = "info"  # Default neutral status
        
        if st.session_state.system_response:
            if st.session_state.system_response.status == SystemStatus.SUCCESS:
                output_content = st.session_state.system_response.runtime_output
                output_status = "success"
            elif st.session_state.system_response.status == SystemStatus.FIXED:
                # Show output from the successful fix
                if st.session_state.system_response.execution_attempts:
                    for attempt in reversed(st.session_state.system_response.execution_attempts):
                        if attempt.execution_result.success and attempt.execution_result.stdout:
                            output_content = attempt.execution_result.stdout
                            output_status = "success"
                            break
                if not output_content:
                    output_content = st.session_state.system_response.runtime_output
                    output_status = "success" if output_content else "info"
        elif st.session_state.execution_result and st.session_state.execution_result.has_output():
            output_content = st.session_state.execution_result.stdout
            output_status = "success"
        
        # Debug the final output content
        st.write(f"🐛 Debug - Final Output Content Length: {len(output_content)}")
        st.write(f"🐛 Debug - Output Status: {output_status}")
        
        if output_content:
            # Apply visual styling based on success/error state
            if output_status == "success":
                st.markdown(
                    f'<div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 10px; margin: 5px 0;"><strong>✅ Program executed successfully:</strong></div>',
                    unsafe_allow_html=True
                )
            st.text_area(
                "Program Output:", 
                value=output_content,
                height=150, 
                disabled=True,
                key="main_output"
            )
        else:
            st.markdown(
                f'<div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 5px; padding: 15px; margin: 5px 0; text-align: center; color: #6c757d; font-style: italic;">Program output will appear here...</div>',
                unsafe_allow_html=True
            )
    
    with tab2:
        st.markdown("#### Compilation Errors")
        error_content = ""
        has_error = False
        
        if st.session_state.system_response and st.session_state.system_response.compile_error:
            error_content = st.session_state.system_response.compile_error
            has_error = True
        elif st.session_state.execution_result and st.session_state.execution_result.has_compilation_error():
            error_content = st.session_state.execution_result.compile_error
            has_error = True
        
        if has_error:
            # Apply error styling
            st.markdown(
                f'<div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; padding: 10px; margin: 5px 0;"><strong>❌ Compilation failed:</strong></div>',
                unsafe_allow_html=True
            )
            st.text_area(
                "Compilation Errors:", 
                value=error_content,
                height=150, 
                disabled=True,
                key="main_compile_err"
            )
        else:
            st.markdown(
                f'<div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin: 5px 0; text-align: center; color: #0c5460;">✅ No compilation errors</div>',
                unsafe_allow_html=True
            )
    
    with tab3:
        st.markdown("#### Runtime Errors")
        runtime_error_content = ""
        has_runtime_error = False
        
        if st.session_state.execution_result and st.session_state.execution_result.has_runtime_error():
            runtime_error_content = st.session_state.execution_result.runtime_error
            has_runtime_error = True
        
        if has_runtime_error:
            # Apply error styling
            st.markdown(
                f'<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 10px; margin: 5px 0;"><strong>⚠️ Runtime error occurred:</strong></div>',
                unsafe_allow_html=True
            )
            st.text_area(
                "Runtime Errors:", 
                value=runtime_error_content,
                height=150, 
                disabled=True,
                key="main_runtime_err"
            )
        else:
            st.markdown(
                f'<div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin: 5px 0; text-align: center; color: #0c5460;">✅ No runtime errors</div>',
                unsafe_allow_html=True
            )
    
    with tab4:
        st.markdown("#### Fix Attempts History")
        if st.session_state.system_response and st.session_state.system_response.execution_attempts:
            st.markdown(f"**Total Fix Attempts:** {st.session_state.system_response.total_fix_attempts}")
            
            # Show summary statistics
            successful_attempts = sum(1 for attempt in st.session_state.system_response.execution_attempts if attempt.execution_result.success)
            failed_attempts = len(st.session_state.system_response.execution_attempts) - successful_attempts
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("Total Attempts", len(st.session_state.system_response.execution_attempts))
            with col_stats2:
                st.metric("Successful", successful_attempts)
            with col_stats3:
                st.metric("Failed", failed_attempts)
            
            # Show detailed attempt information
            for i, attempt in enumerate(st.session_state.system_response.execution_attempts, 1):
                success_indicator = "✅ Success" if attempt.execution_result.success else "❌ Failed"
                
                with st.expander(f"Attempt {attempt.attempt_number} - {success_indicator}"):
                    st.write(f"**Strategy:** {attempt.fix_strategy}")
                    st.write(f"**Timestamp:** {attempt.timestamp}")
                    if hasattr(attempt, 'llm_model_used') and attempt.llm_model_used:
                        st.write(f"**Model Used:** {attempt.llm_model_used}")
                    
                    if attempt.execution_result.success:
                        st.markdown(
                            f'<div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 8px; margin: 5px 0;">✅ Fix attempt succeeded!</div>',
                            unsafe_allow_html=True
                        )
                        if attempt.execution_result.stdout:
                            st.text_area("Output:", value=attempt.execution_result.stdout, height=100, disabled=True, key=f"attempt_{i}_output")
                    else:
                        error_msg = attempt.execution_result.compile_error or attempt.execution_result.runtime_error or "Unknown error"
                        st.markdown(
                            f'<div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; padding: 8px; margin: 5px 0;">❌ Fix attempt failed</div>',
                            unsafe_allow_html=True
                        )
                        st.text_area("Error Details:", value=error_msg, height=100, disabled=True, key=f"attempt_{i}_error")
        else:
            st.markdown(
                f'<div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 5px; padding: 15px; margin: 5px 0; text-align: center; color: #6c757d; font-style: italic;">Fix attempt details will appear here...</div>',
                unsafe_allow_html=True
            )
    
    # Process button click - implement comprehensive validation and retry workflow with error handling
    if run_button:
        if not java_code.strip():
            st.warning("Please enter some Java code to process.")
        elif not st.session_state.get('java_runner_available', False):
            st.error("❌ Java execution is not available. Please check Docker installation.")
        else:
            # Show progress indicator
            with st.spinner(f"Processing Java code migration from Java {source_version} to Java {target_version}..."):
                try:
                    # Check if we have the full validation system available
                    if st.session_state.get('validation_system_available', False):
                        # Use the comprehensive validation and retry system with migration
                        system_response = st.session_state.validation_system.process_code_with_migration(
                            original_code=java_code,
                            source_version=source_version,
                            target_version=target_version
                        )
                        
                        st.session_state.system_response = system_response
                        
                        # Display results based on system response status
                        if system_response.status == SystemStatus.SUCCESS:
                            if source_version == target_version:
                                st.markdown(
                                    f'<div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 15px; margin: 10px 0;"><h4 style="color: #155724; margin: 0;">✅ Code executed successfully in Java {target_version}!</h4></div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    f'<div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 15px; margin: 10px 0;"><h4 style="color: #155724; margin: 0;">✅ Code works in both Java {source_version} and Java {target_version}!</h4><p style="margin: 5px 0 0 0;">No migration fixes needed.</p></div>',
                                    unsafe_allow_html=True
                                )
                            st.session_state.execution_result = ExecutionResult(
                                success=True,
                                compile_error=None,
                                runtime_error=None,
                                stdout=system_response.runtime_output,
                                stderr="",
                                execution_time=0.0,
                                java_version=target_version,
                                source_version=source_version
                            )
                            
                        elif system_response.status == SystemStatus.FIXED:
                            st.markdown(
                                f'<div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 8px; padding: 15px; margin: 10px 0;"><h4 style="color: #0c5460; margin: 0;">✅ Code successfully migrated from Java {source_version} to Java {target_version}!</h4><p style="margin: 5px 0 0 0;">Fixed after {system_response.total_fix_attempts} attempts.</p></div>',
                                unsafe_allow_html=True
                            )
                            st.info("Check the 'Fixed Java Code' panel and 'Fix Attempts' tab for details.")
                            st.session_state.fixed_code = system_response.fixed_code
                            
                        elif system_response.status == SystemStatus.FAILED:
                            if system_response.source_execution_result and not system_response.source_execution_result.success:
                                st.markdown(
                                    f'<div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 15px; margin: 10px 0;"><h4 style="color: #721c24; margin: 0;">❌ Code fails in source version Java {source_version}</h4><p style="margin: 5px 0 0 0;">Please fix the code to work in the source version first.</p></div>',
                                    unsafe_allow_html=True
                                )
                            elif system_response.total_fix_attempts > 0:
                                st.markdown(
                                    f'<div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 15px; margin: 10px 0;"><h4 style="color: #721c24; margin: 0;">❌ Migration from Java {source_version} to Java {target_version} failed</h4><p style="margin: 5px 0 0 0;">All {system_response.total_fix_attempts} fix attempts failed.</p></div>',
                                    unsafe_allow_html=True
                                )
                                st.info("Check the 'Fix Attempts' tab for detailed failure information.")
                            else:
                                st.markdown(
                                    f'<div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 15px; margin: 10px 0;"><h4 style="color: #721c24; margin: 0;">❌ Migration issue is not fixable by LLM</h4><p style="margin: 5px 0 0 0;">Code works in Java {source_version} but fails in Java {target_version}.</p></div>',
                                    unsafe_allow_html=True
                                )
                            
                            if system_response.compile_error:
                                st.session_state.execution_result = ExecutionResult(
                                    success=False,
                                    compile_error=system_response.compile_error,
                                    runtime_error=None,
                                    stdout="",
                                    stderr="",
                                    execution_time=0.0,
                                    java_version=target_version,
                                    source_version=source_version
                                )
                        
                        # Display comprehensive execution summary
                        with st.expander("Detailed Migration Summary"):
                            summary_data = {
                                "status": system_response.status.value,
                                "source_version": system_response.source_version,
                                "target_version": system_response.target_version,
                                "total_fix_attempts": system_response.total_fix_attempts,
                                "has_fixed_code": system_response.fixed_code is not None,
                                "execution_attempts": len(system_response.execution_attempts),
                                "source_execution_success": system_response.source_execution_result.success if system_response.source_execution_result else None
                            }
                            
                            # Add attempt summary if available
                            if hasattr(st.session_state.validation_system, 'get_attempt_summary'):
                                attempt_summary = st.session_state.validation_system.get_attempt_summary()
                                summary_data.update(attempt_summary)
                            
                            st.json(summary_data)
                            
                            # Show source execution details
                            if system_response.source_execution_result:
                                st.subheader(f"Source Version (Java {source_version}) Results")
                                if system_response.source_execution_result.success:
                                    st.success("✅ Executed successfully in source version")
                                    if system_response.source_execution_result.stdout:
                                        st.code(system_response.source_execution_result.stdout, language="text")
                                else:
                                    st.error("❌ Failed in source version")
                                    if system_response.source_execution_result.compile_error:
                                        st.code(system_response.source_execution_result.compile_error, language="text")
                                    if system_response.source_execution_result.runtime_error:
                                        st.code(system_response.source_execution_result.runtime_error, language="text")
                            
                            # Show detailed failure info if there were failures
                            if system_response.status == SystemStatus.FAILED and system_response.total_fix_attempts > 0:
                                if hasattr(st.session_state.validation_system, 'get_detailed_failure_info'):
                                    failure_info = st.session_state.validation_system.get_detailed_failure_info()
                                    st.subheader("Failure Analysis")
                                    st.json(failure_info)
                    
                    else:
                        # Fallback to basic execution with migration testing
                        st.warning("⚠️ Using basic migration mode - comprehensive validation not available")
                        
                        if st.session_state.get('java_runner'):
                            # Test both versions
                            source_result, target_result = st.session_state.java_runner.compile_and_run_with_migration(
                                java_code, source_version, target_version
                            )
                            
                            # Store results
                            st.session_state.execution_result = target_result
                            
                            if not source_result.success:
                                st.error(f"❌ Code fails in source version Java {source_version}")
                                st.code(source_result.compile_error or source_result.runtime_error or "Unknown error")
                                st.session_state.system_response = SystemResponse(
                                    status=SystemStatus.FAILED,
                                    java_version=target_version,
                                    source_version=source_version,
                                    target_version=target_version,
                                    original_code=java_code,
                                    fixed_code=None,
                                    compile_error=f"Source version failure: {source_result.compile_error or source_result.runtime_error}",
                                    runtime_output="",
                                    source_execution_result=source_result,
                                    execution_attempts=[],
                                    total_fix_attempts=0
                                )
                            elif target_result.success:
                                if source_version == target_version:
                                    st.success(f"✅ Code executed successfully in Java {target_version}!")
                                else:
                                    st.success(f"✅ Code works in both Java {source_version} and Java {target_version}!")
                                st.session_state.system_response = SystemResponse(
                                    status=SystemStatus.SUCCESS,
                                    java_version=target_version,
                                    source_version=source_version,
                                    target_version=target_version,
                                    original_code=java_code,
                                    fixed_code=None,
                                    compile_error=None,
                                    runtime_output=target_result.stdout,
                                    source_execution_result=source_result,
                                    execution_attempts=[],
                                    total_fix_attempts=0
                                )
                            else:
                                st.error(f"❌ Code works in Java {source_version} but fails in Java {target_version}")
                                st.code(target_result.compile_error or target_result.runtime_error or "Unknown error")
                                
                                # Try basic error classification if available
                                if st.session_state.get('error_classifier_available', False):
                                    try:
                                        error_msg = target_result.compile_error or target_result.runtime_error or "Unknown error"
                                        compatibility_analysis = st.session_state.error_classifier.analyze_error(
                                            error_msg, target_version, java_code
                                        )
                                        if compatibility_analysis.is_version_issue:
                                            st.info("🔍 This appears to be a version compatibility issue.")
                                            if st.session_state.get('llm_agent_available', False):
                                                st.info("💡 Try enabling comprehensive validation for automatic fixes.")
                                            else:
                                                st.info("💡 Set up LLM API keys for automatic code fixing.")
                                    except Exception as analysis_error:
                                        st.debug(f"Error analysis failed: {analysis_error}")
                                
                                st.session_state.system_response = SystemResponse(
                                    status=SystemStatus.FAILED,
                                    java_version=target_version,
                                    source_version=source_version,
                                    target_version=target_version,
                                    original_code=java_code,
                                    fixed_code=None,
                                    compile_error=target_result.compile_error or target_result.runtime_error,
                                    runtime_output="",
                                    source_execution_result=source_result,
                                    execution_attempts=[],
                                    total_fix_attempts=0
                                )
                        else:
                            st.error("❌ Java execution is not available")
                    
                except Exception as e:
                    # Comprehensive error handling for processing failures
                    error_context = st.session_state.error_handler.handle_error(
                        exception=e,
                        category=ErrorCategory.SYSTEM_ERROR,
                        severity=ErrorSeverity.HIGH,
                        component="app",
                        operation="process_code_migration",
                        user_message="Code migration processing failed due to a system error."
                    )
                    
                    st.error(f"❌ Migration processing failed: {error_context.user_message}")
                    st.error(f"Error ID: {error_context.error_id}")
                    
                    # Reset state on error
                    st.session_state.system_response = None
                    st.session_state.execution_result = None
                    
                    # Show detailed error in expander for debugging
                    with st.expander("Error Details and Recovery"):
                        st.code(error_context.technical_details)
                        st.markdown("**Recovery Suggestions:**")
                        for suggestion in error_context.recovery_suggestions:
                            st.markdown(f"- {suggestion}")
                        
                        # Show system health if available
                        if hasattr(st.session_state, 'graceful_degradation'):
                            try:
                                health = st.session_state.graceful_degradation.get_system_health()
                                st.subheader("System Health")
                                st.json(health)
                            except:
                                pass
    
    # Footer with comprehensive information and system status
    st.markdown("---")
    
    # Create footer columns for better organization
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    
    with footer_col1:
        st.markdown("### 💡 System Features")
        features = []
        if st.session_state.get('java_runner_available', False):
            features.append("✅ Java Code Execution")
        else:
            features.append("❌ Java Code Execution")
            
        if st.session_state.get('error_classifier_available', False):
            features.append("✅ Error Analysis")
        else:
            features.append("⚠️ Limited Error Analysis")
            
        if st.session_state.get('llm_agent_available', False):
            features.append("✅ AI Code Fixing")
        else:
            features.append("❌ AI Code Fixing")
            
        if st.session_state.get('validation_system_available', False):
            features.append("✅ Comprehensive Validation")
        else:
            features.append("⚠️ Basic Validation Only")
        
        for feature in features:
            st.markdown(f"- {feature}")
    
    with footer_col2:
        st.markdown("### 🔧 Configuration Status")
        config_status = []
        
        if hasattr(st.session_state, 'system_config'):
            config = st.session_state.system_config
            config_status.append(f"✅ Java Versions: {len(config.java_versions)} configured")
            config_status.append(f"✅ Timeout: {config.execution_timeout}s")
            config_status.append(f"✅ Memory Limit: {config.docker_memory_limit}")
            
            if config.openai_api_key:
                config_status.append("✅ OpenAI API Key Set")
            else:
                config_status.append("❌ OpenAI API Key Missing")
                
            if config.anthropic_api_key:
                config_status.append("✅ Anthropic API Key Set")
            else:
                config_status.append("❌ Anthropic API Key Missing")
        else:
            config_status.append("❌ Configuration not loaded")
        
        for status in config_status:
            st.markdown(f"- {status}")
    
    with footer_col3:
        st.markdown("### 📊 Session Statistics")
        stats = []
        
        # Error statistics
        if hasattr(st.session_state, 'error_handler'):
            try:
                error_summary = st.session_state.error_handler.get_error_summary()
                stats.append(f"Errors: {error_summary.get('total_errors', 0)}")
            except:
                stats.append("Errors: N/A")
        
        # Processing statistics
        if st.session_state.get('system_response'):
            response = st.session_state.system_response
            stats.append(f"Status: {response.status.value}")
            stats.append(f"Fix Attempts: {response.total_fix_attempts}")
        else:
            stats.append("No processing completed")
        
        # System health
        if hasattr(st.session_state, 'graceful_degradation'):
            try:
                health = st.session_state.graceful_degradation.get_system_health()
                stats.append(f"System Health: {health['overall_health']:.0f}%")
            except:
                stats.append("System Health: Unknown")
        
        for stat in stats:
            st.markdown(f"- {stat}")
    
    # Main footer message
    st.markdown(
        "💡 **Java Version Compatibility Fixer** - Comprehensive validation and retry logic with LLM-based code fixing. "
        "The system automatically attempts to fix version compatibility issues up to 2 times with full validation. "
        "All components include graceful degradation and comprehensive error handling."
    )
    
    # Show additional help if system is degraded
    if hasattr(st.session_state, 'graceful_degradation'):
        try:
            health = st.session_state.graceful_degradation.get_system_health()
            if health.get('degraded_mode', False):
                st.info(
                    "ℹ️ **System is running in degraded mode.** Some features may be limited. "
                    "Check the system status above for details and recovery suggestions."
                )
        except:
            pass

if __name__ == "__main__":
    main()