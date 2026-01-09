#!/bin/bash

# Simple deployment script for Java Migration Tool
echo "🚀 Deploying Java Version Migration Tool"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the project root directory."
    exit 1
fi

# Test Docker build locally first
echo "🔧 Testing Docker build locally..."
docker build -t java-migration-tool-test . || {
    echo "❌ Docker build failed. Please fix the Dockerfile."
    exit 1
}

echo "✅ Docker build successful!"

# Test the application locally
echo "🧪 Testing application locally..."
echo "Starting container on port 8501..."
docker run -d --name java-migration-test -p 8501:8501 java-migration-tool-test

# Wait for the application to start
sleep 10

# Test health endpoint
if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "✅ Application health check passed!"
else
    echo "⚠️ Health check failed, but continuing with deployment..."
fi

# Clean up test container
docker stop java-migration-test > /dev/null 2>&1
docker rm java-migration-test > /dev/null 2>&1

echo "🎯 Local testing completed!"
echo ""
echo "📋 Next steps for AWS deployment:"
echo ""
echo "1. 🔐 Set up AWS credentials:"
echo "   aws configure"
echo ""
echo "2. 🚀 Deploy using one of these methods:"
echo ""
echo "   Method A - AWS App Runner (Recommended):"
echo "   • Go to AWS App Runner Console"
echo "   • Create service from source code"
echo "   • Connect your GitHub repository"
echo "   • Use the apprunner.yaml configuration file"
echo "   • Add environment variables for API keys"
echo ""
echo "   Method B - AWS ECS Fargate:"
echo "   • Push image to ECR"
echo "   • Create ECS task definition"
echo "   • Deploy as Fargate service"
echo ""
echo "   Method C - AWS Lightsail:"
echo "   • Create container service"
echo "   • Upload Docker image"
echo "   • Configure environment variables"
echo ""
echo "3. 🔑 Configure API keys in your chosen service:"
echo "   • OPENAI_API_KEY=your-openai-key"
echo "   • ANTHROPIC_API_KEY=your-anthropic-key"
echo ""
echo "4. 🌐 Access your deployed application!"
echo ""
echo "💡 For detailed deployment instructions, see deploy.md"

# Create a deployment checklist
cat > deployment-checklist.md << 'EOF'
# Deployment Checklist

## Pre-deployment
- [ ] Docker build successful locally
- [ ] Application runs locally on port 8501
- [ ] Health check endpoint responds
- [ ] API keys available for configuration

## AWS Setup
- [ ] AWS CLI configured with appropriate credentials
- [ ] AWS account has necessary permissions
- [ ] Chosen deployment method (App Runner/ECS/Lightsail)

## Deployment Steps
- [ ] Repository pushed to GitHub (for App Runner)
- [ ] Docker image built and tested
- [ ] AWS service created and configured
- [ ] Environment variables set (API keys)
- [ ] Health checks configured
- [ ] Custom domain configured (optional)

## Post-deployment
- [ ] Application accessible via public URL
- [ ] Java code execution working
- [ ] LLM integration working (API keys valid)
- [ ] Migration functionality tested
- [ ] Monitoring and logging configured

## Testing Checklist
- [ ] Simple Java code execution (Hello World)
- [ ] Java 8 to Java 17 migration test
- [ ] Nashorn script engine migration test
- [ ] Error handling and user feedback
- [ ] Performance under load

## Troubleshooting
- [ ] Check application logs
- [ ] Verify environment variables
- [ ] Test API key validity
- [ ] Check Java runtime availability
- [ ] Verify network connectivity
EOF

echo "📝 Created deployment-checklist.md for tracking progress"
echo "🎉 Deployment preparation completed!"