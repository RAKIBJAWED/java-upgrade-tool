# Java Version Compatibility Fixer

A web-based tool that helps developers automatically identify and fix Java version compatibility issues in their code using AI-powered code transformation.

## Features

- **Multi-Version Support**: Test code compatibility with Java 8, 11, 17, and 21
- **Secure Execution**: Run Java code in isolated Docker containers with resource limits
- **AI-Powered Fixes**: Use OpenAI GPT or Anthropic Claude models to automatically fix compatibility issues
- **Side-by-Side Comparison**: View original and fixed code with syntax highlighting
- **Comprehensive Error Analysis**: Detailed compilation and runtime error reporting

## Setup

### Prerequisites

- Python 3.8+
- Docker
- OpenAI API key and/or Anthropic API key

### Installation

1. Clone the repository and navigate to the project directory

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.template .env
# Edit .env and add your API keys
```

4. Ensure Docker is running and pull required Java images:
```bash
docker pull openjdk:8-jdk-alpine
docker pull openjdk:11-jdk-alpine
docker pull openjdk:17-jdk-alpine
docker pull openjdk:21-jdk-alpine
```

### Running the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

## Project Structure

```
├── app.py                 # Streamlit application entry point
├── config/
│   ├── __init__.py
│   ├── settings.py        # Configuration management
│   └── java_versions.json # Java version to Docker image mappings
├── core/                  # Core functionality (to be implemented)
│   └── __init__.py
├── agent/                 # LLM integration (to be implemented)
│   └── __init__.py
├── utils/                 # Utility functions (to be implemented)
│   └── __init__.py
├── requirements.txt       # Python dependencies
├── .env.template         # Environment variables template
└── README.md             # This file
```

## Configuration

The system configuration is managed through:

- `config/java_versions.json`: Java version mappings and system settings
- `.env`: Environment variables for API keys
- Environment variables for sensitive data (API keys)

## Development

This project follows a modular architecture with clear separation of concerns:

- **Presentation Layer**: Streamlit UI (`app.py`)
- **Configuration Layer**: Settings and validation (`config/`)
- **Core Logic**: Java execution and error analysis (`core/`)
- **Intelligence Layer**: LLM integration (`agent/`)
- **Utilities**: Helper functions (`utils/`)

## Security

- Java code execution is isolated in Docker containers
- Resource limits enforced (512MB memory, 1 CPU core, 30-second timeout)
- Network access disabled for executing containers
- API keys loaded securely from environment variables