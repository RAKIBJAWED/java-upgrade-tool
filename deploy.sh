#!/bin/bash

# Java Version Migration Tool - AWS Deployment Script
echo "🚀 Starting deployment of Java Version Migration Tool to AWS"

# Check if AWS credentials are set
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ AWS credentials not found in environment variables"
    echo "Please set the following environment variables:"
    echo "  export AWS_ACCESS_KEY_ID=your-access-key"
    echo "  export AWS_SECRET_ACCESS_KEY=your-secret-key"
    echo "  export AWS_SESSION_TOKEN=your-session-token (if using temporary credentials)"
    echo ""
    echo "Or run: aws configure"
    exit 1
fi

# Configuration
AWS_REGION="us-east-1"
APP_NAME="java-migration-tool"
ECR_REPOSITORY="java-migration-tool"
SERVICE_ROLE_NAME="AppRunnerECRAccessRole"

echo "📋 Configuration:"
echo "  - AWS Region: $AWS_REGION"
echo "  - App Name: $APP_NAME"
echo "  - ECR Repository: $ECR_REPOSITORY"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Installing..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
fi

# Verify AWS credentials
echo "🔐 Verifying AWS credentials..."
aws sts get-caller-identity
if [ $? -ne 0 ]; then
    echo "❌ AWS credentials verification failed"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ AWS Account ID: $AWS_ACCOUNT_ID"

# Create ECR repository if it doesn't exist
echo "🏗️ Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# Get ECR login token
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build Docker image
echo "� Building Docker image..."
docker build -t $ECR_REPOSITORY .

# Tag image for ECR
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
docker tag $ECR_REPOSITORY:latest $ECR_URI

# Push image to ECR
echo "📤 Pushing image to ECR..."
docker push $ECR_URI

# Create IAM role for App Runner if it doesn't exist
echo "🔐 Creating IAM role for App Runner..."
aws iam get-role --role-name $SERVICE_ROLE_NAME 2>/dev/null || {
    echo "Creating App Runner service role..."
    
    # Create trust policy
    cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "build.apprunner.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # Create the role
    aws iam create-role \
        --role-name $SERVICE_ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json

    # Attach ECR access policy
    aws iam attach-role-policy \
        --role-name $SERVICE_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

    # Clean up
    rm trust-policy.json
    
    echo "✅ IAM role created successfully"
}

# Get the role ARN
SERVICE_ROLE_ARN=$(aws iam get-role --role-name $SERVICE_ROLE_NAME --query 'Role.Arn' --output text)
echo "✅ Service Role ARN: $SERVICE_ROLE_ARN"

# Create App Runner service configuration
echo "📝 Creating App Runner service configuration..."
cat > apprunner-config.json << EOF
{
    "ServiceName": "$APP_NAME",
    "SourceConfiguration": {
        "ImageRepository": {
            "ImageIdentifier": "$ECR_URI",
            "ImageConfiguration": {
                "Port": "8501",
                "RuntimeEnvironmentVariables": {
                    "PORT": "8501",
                    "PYTHONPATH": "/app",
                    "STREAMLIT_SERVER_HEADLESS": "true",
                    "STREAMLIT_SERVER_ENABLE_CORS": "false",
                    "STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION": "false"
                }
            },
            "ImageRepositoryType": "ECR"
        },
        "AutoDeploymentsEnabled": false
    },
    "InstanceConfiguration": {
        "Cpu": "1 vCPU",
        "Memory": "2 GB"
    },
    "HealthCheckConfiguration": {
        "Protocol": "HTTP",
        "Path": "/_stcore/health",
        "Interval": 10,
        "Timeout": 5,
        "HealthyThreshold": 1,
        "UnhealthyThreshold": 5
    }
}
EOF

# Check if App Runner service already exists
echo "🔍 Checking if App Runner service exists..."
SERVICE_ARN=$(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='$APP_NAME'].ServiceArn" --output text 2>/dev/null)

if [ -n "$SERVICE_ARN" ]; then
    echo "🔄 Updating existing App Runner service..."
    aws apprunner update-service \
        --service-arn "$SERVICE_ARN" \
        --source-configuration file://apprunner-config.json \
        --region $AWS_REGION
else
    echo "🚀 Creating new App Runner service..."
    aws apprunner create-service \
        --cli-input-json file://apprunner-config.json \
        --region $AWS_REGION
fi

# Clean up temporary files
rm apprunner-config.json

# Wait for service to be ready
echo "⏳ Waiting for service to be ready..."
sleep 30

# Get service URL
SERVICE_URL=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --query 'Service.ServiceUrl' --output text 2>/dev/null)

if [ -n "$SERVICE_URL" ]; then
    echo "✅ Deployment completed successfully!"
    echo "🌐 Service URL: https://$SERVICE_URL"
    echo ""
    echo "📋 Next steps:"
    echo "  1. Wait 2-3 minutes for the service to fully start"
    echo "  2. Visit the URL above to access your application"
    echo "  3. Configure your API keys in the application settings"
    echo ""
    echo "🔧 To update the application:"
    echo "  1. Make your changes"
    echo "  2. Run this script again"
    echo "  3. App Runner will automatically deploy the new version"
else
    echo "⚠️ Service created but URL not available yet. Check AWS Console for status."
fi

echo "🎉 Deployment script completed!"