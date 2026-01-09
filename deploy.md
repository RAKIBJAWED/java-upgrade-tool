# AWS App Runner Deployment Guide

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Docker** installed locally (for testing)
4. **Git repository** (GitHub recommended)

## Step-by-Step Deployment

### Step 1: Test Locally with Docker

```bash
# Build the Docker image
docker build -t java-migration-tool .

# Run locally to test
docker run -p 8501:8501 \
  -e OPENAI_API_KEY="your-openai-key" \
  -e ANTHROPIC_API_KEY="your-anthropic-key" \
  java-migration-tool

# Test at http://localhost:8501
```

### Step 2: Push to GitHub

```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit for App Runner deployment"

# Push to GitHub
git remote add origin https://github.com/yourusername/java-migration-tool.git
git branch -M main
git push -u origin main
```

### Step 3: Create App Runner Service

#### Option A: Using AWS Console (Recommended)

1. **Go to AWS App Runner Console**
   - Navigate to https://console.aws.amazon.com/apprunner/
   - Click "Create service"

2. **Configure Source**
   - Source type: "Source code repository"
   - Repository provider: "GitHub"
   - Connect to GitHub (authorize AWS)
   - Select your repository
   - Branch: "main"
   - Deployment trigger: "Automatic"

3. **Configure Build**
   - Configuration file: "Use configuration file" (apprunner.yaml)
   - Or manually configure:
     - Runtime: "Docker"
     - Build command: `docker build -t java-migration-tool .`
     - Start command: `streamlit run app.py --server.port=8501 --server.address=0.0.0.0`

4. **Configure Service**
   - Service name: "java-migration-tool"
   - Port: 8501
   - Environment variables:
     - `OPENAI_API_KEY`: your-openai-api-key
     - `ANTHROPIC_API_KEY`: your-anthropic-api-key
     - `PORT`: 8501

5. **Configure Auto Scaling**
   - Min instances: 1
   - Max instances: 10
   - Max concurrency: 100

6. **Configure Health Check**
   - Protocol: HTTP
   - Path: /_stcore/health
   - Interval: 20 seconds
   - Timeout: 10 seconds
   - Healthy threshold: 1
   - Unhealthy threshold: 5

#### Option B: Using AWS CLI

```bash
# Create service configuration
aws apprunner create-service \
  --service-name java-migration-tool \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "public.ecr.aws/docker/library/python:3.9-slim",
      "ImageConfiguration": {
        "Port": "8501"
      },
      "ImageRepositoryType": "ECR_PUBLIC"
    },
    "CodeRepository": {
      "RepositoryUrl": "https://github.com/yourusername/java-migration-tool",
      "SourceCodeVersion": {
        "Type": "BRANCH",
        "Value": "main"
      },
      "CodeConfiguration": {
        "ConfigurationSource": "CONFIGURATION_FILE"
      }
    }
  }' \
  --instance-configuration '{
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB",
    "InstanceRoleArn": "arn:aws:iam::YOUR-ACCOUNT:role/AppRunnerInstanceRole"
  }' \
  --auto-scaling-configuration-arn "arn:aws:apprunner:region:account:autoscalingconfiguration/DefaultConfiguration"
```

### Step 4: Configure Environment Variables

In the App Runner console:

1. Go to your service
2. Click "Configuration" tab
3. Click "Configure" in Environment variables section
4. Add:
   - `OPENAI_API_KEY`: your-openai-api-key
   - `ANTHROPIC_API_KEY`: your-anthropic-api-key
   - `STREAMLIT_SERVER_HEADLESS`: true
   - `STREAMLIT_SERVER_ENABLE_CORS`: false

### Step 5: Configure Custom Domain (Optional)

1. In App Runner console, go to "Custom domains"
2. Click "Link domain"
3. Enter your domain name
4. Follow DNS configuration instructions
5. Add CNAME record to your DNS provider

### Step 6: Monitor Deployment

1. **Check Logs**:
   - Go to "Logs" tab in App Runner console
   - Monitor build and runtime logs

2. **Test Application**:
   - Use the provided App Runner URL
   - Test Java code migration functionality

## Troubleshooting

### Common Issues:

1. **Build Failures**:
   ```bash
   # Check Dockerfile syntax
   docker build -t test .
   ```

2. **Port Issues**:
   - Ensure Streamlit runs on port 8501
   - Check health check endpoint

3. **Environment Variables**:
   - Verify API keys are set correctly
   - Check logs for authentication errors

4. **Docker Socket Issues**:
   - App Runner doesn't support Docker-in-Docker
   - Consider using AWS Lambda for Java execution
   - Or use ECS Fargate with privileged containers

### Alternative Architecture for Docker Issues:

If Docker-in-Docker doesn't work in App Runner, consider:

1. **Separate Java Execution Service**:
   - Deploy Java execution as separate ECS service
   - Use API calls from Streamlit to Java service

2. **AWS Lambda for Java Execution**:
   - Create Lambda function for Java compilation/execution
   - Call from Streamlit app via API Gateway

## Cost Estimation

- **App Runner**: ~$25-50/month
- **Data Transfer**: ~$5-10/month
- **Total**: ~$30-60/month for moderate usage

## Security Best Practices

1. **API Keys**: Store in AWS Systems Manager Parameter Store
2. **VPC**: Configure VPC connector for private resources
3. **IAM**: Use least privilege access
4. **HTTPS**: Enable automatic HTTPS (included)

## Monitoring

1. **CloudWatch**: Automatic metrics and logs
2. **X-Ray**: Enable tracing for performance monitoring
3. **Health Checks**: Configure appropriate health check endpoints