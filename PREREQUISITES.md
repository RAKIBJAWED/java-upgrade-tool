# Prerequisites for Java Version Compatibility Fixer

This document outlines all the prerequisites and setup steps required to run the Java Version Compatibility Fixer application successfully.

## 📋 System Requirements

### Minimum Hardware Requirements
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free disk space (for Docker images and application data)
- **CPU**: Any modern x64 processor
- **Network**: Internet connection for LLM API calls and Docker image downloads

### Supported Operating Systems
- **Linux**: Ubuntu 18.04+, Debian 10+, CentOS 7+, or equivalent
- **macOS**: macOS 10.14+ (Mojave or later)
- **Windows**: Windows 10 version 2004+ or Windows 11 (with WSL 2 support)

## 🐍 Python Environment

### Python Version
- **Required**: Python 3.8 or higher
- **Recommended**: Python 3.10 or 3.11

### Check Python Version
```bash
python --version
# or
python3 --version
```

### Install Python (if needed)
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update
  sudo apt install python3 python3-pip python3-venv
  ```
- **macOS**: 
  ```bash
  brew install python3
  ```
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

## 🐳 Docker Installation

Docker is **required** for secure Java code execution. The application will not function without Docker.

### Docker Installation by OS

#### 🐧 Linux (Ubuntu/Debian)
```bash
# Update package index
sudo apt update

# Install prerequisites
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Log out and log back in, then test
docker --version
```

#### 🍎 macOS
1. Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. Install the downloaded `.dmg` file
3. Launch Docker Desktop from Applications
4. Complete the setup wizard

#### 🪟 Windows
1. **Enable WSL 2**:
   ```powershell
   # Run as Administrator
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```
2. **Restart your computer**
3. **Install WSL 2 kernel update** from [Microsoft](https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi)
4. **Set WSL 2 as default**:
   ```powershell
   wsl --set-default-version 2
   ```
5. **Download and install** [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)

### Verify Docker Installation
```bash
docker --version
docker run hello-world
```

### Pull Required Java Images
```bash
# Pull all Java versions used by the application (Eclipse Temurin - official replacement for OpenJDK)
docker pull eclipse-temurin:8-jdk
docker pull eclipse-temurin:11-jdk
docker pull eclipse-temurin:17-jdk
docker pull eclipse-temurin:21-jdk
```

## 🔑 API Keys Setup

The application requires LLM API keys for code fixing functionality.

### Supported LLM Providers
You need **at least one** of the following API keys:

#### OpenAI (Recommended)
- **Models**: GPT-4, GPT-3.5-turbo
- **Sign up**: [OpenAI Platform](https://platform.openai.com/)
- **Pricing**: Pay-per-use
- **Environment Variable**: `OPENAI_API_KEY`

#### Anthropic
- **Models**: Claude-3-haiku, Claude-3-sonnet, Claude-3-opus
- **Sign up**: [Anthropic Console](https://console.anthropic.com/)
- **Pricing**: Pay-per-use
- **Environment Variable**: `ANTHROPIC_API_KEY`

#### Together AI (Optional)
- **Models**: Llama-2, Mixtral, and other open-source models
- **Sign up**: [Together AI](https://together.ai/)
- **Pricing**: Pay-per-use
- **Environment Variable**: `TOGETHER_AI_API_KEY`

### API Key Configuration
1. **Copy environment template**:
   ```bash
   cp .env.template .env
   ```

2. **Edit `.env` file** and add your API keys:
   ```bash
   # OpenAI API Key (recommended)
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Anthropic API Key
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   
   # Together AI API Key (optional)
   TOGETHER_AI_API_KEY=your_together_ai_key_here
   ```

## 📦 Python Dependencies

### Install Dependencies
```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### Required Python Packages
The application requires these packages (automatically installed with `requirements.txt`):
- `streamlit` - Web application framework
- `docker` - Docker SDK for Python
- `openai` - OpenAI API client
- `anthropic` - Anthropic API client
- `requests` - HTTP library
- `python-dotenv` - Environment variable management
- `hypothesis` - Property-based testing framework
- `pytest` - Testing framework
- `psutil` - System monitoring

## 🔧 System Configuration

### File Permissions (Linux/macOS)
Ensure Docker socket has proper permissions:
```bash
sudo chmod 666 /var/run/docker.sock
```

### Firewall Configuration
Ensure these ports are accessible:
- **8501**: Streamlit web interface (default)
- **Docker daemon**: For container management

### Resource Limits
The application uses Docker containers with these limits:
- **Memory**: 512MB per container
- **CPU**: 1 core per container
- **Execution timeout**: 30 seconds
- **Network**: Disabled for security

## ✅ Verification Steps

Run these commands to verify your setup:

### 1. Check Python Installation
```bash
python --version
pip --version
```

### 2. Verify Docker
```bash
docker --version
docker ps
docker run --rm eclipse-temurin:8-jdk java -version
```

### 3. Test Application Setup
```bash
# Run setup verification
python test_setup.py

# Expected output: All tests should pass
```

### 4. Verify API Keys
```bash
# Test LLM agent functionality
python test_llm_agent.py

# Expected output: Should detect available API keys
```

### 5. Run Core Tests
```bash
# Test core functionality
python test_validation_core.py

# Expected output: All core tests should pass
```

## 🚀 Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] Docker installed and running
- [ ] Java Docker images pulled
- [ ] At least one LLM API key configured
- [ ] Python dependencies installed
- [ ] All verification tests pass
- [ ] Docker containers can execute Java code

## 🔧 Troubleshooting

### Common Issues and Solutions

#### "Docker daemon not running"
```bash
# Linux
sudo systemctl start docker

# macOS/Windows
# Restart Docker Desktop application
```

#### "Permission denied" accessing Docker
```bash
# Linux - add user to docker group
sudo usermod -aG docker $USER
# Log out and log back in
```

#### "No LLM provider available"
- Verify API keys are correctly set in `.env` file
- Check API key validity by running `python test_llm_agent.py`
- Ensure at least one provider (OpenAI, Anthropic, or Together AI) is configured

#### "Java images not found"
```bash
# Pull missing images (using Eclipse Temurin - official replacement for deprecated OpenJDK)
docker pull eclipse-temurin:8-jdk
docker pull eclipse-temurin:11-jdk
docker pull eclipse-temurin:17-jdk
docker pull eclipse-temurin:21-jdk
```

#### "Module not found" errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific missing packages
pip install streamlit docker openai anthropic
```

## 📞 Support

If you encounter issues not covered in this guide:

1. **Check logs**: Look for error messages in the terminal output
2. **Run diagnostics**: Use `python test_setup.py` to identify specific issues
3. **Verify prerequisites**: Ensure all items in the checklist are completed
4. **Check Docker**: Most issues are related to Docker configuration

## 🎯 Next Steps

Once all prerequisites are met:

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Access the web interface**:
   - Open your browser to `http://localhost:8501`

3. **Test functionality**:
   - Enter Java code in the text area
   - Select a Java version
   - Click "Run Java Code" to test execution
   - Try the code fixing features with version-incompatible code

The application is now ready for use!