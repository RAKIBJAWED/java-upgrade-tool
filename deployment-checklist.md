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
