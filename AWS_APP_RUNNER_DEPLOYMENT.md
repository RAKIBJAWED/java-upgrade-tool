# AWS App Runner Deployment Guide

## 🚀 Quick Deployment Steps

### Prerequisites
- ✅ AWS Account with appropriate permissions
- ✅ GitHub repository with your code
- ✅ API keys for OpenAI/Anthropic (optional but recommended)

### Step 1: Push Code to GitHub
```bash
# If not already done
git add .
git commit -m "Ready for App Runner deployment"
git push origin main
```

### Step 2: Create App Runner Service

1. **Go to AWS App Runner Console**
   - Navigate to: https://console.aws.amazon.com/apprunner/
   - Click "Create service"

2. **Configure Source**
   - Source type: **Source code repository**
   - Repository provider: **GitHub**
   - Connect to GitHub (if first time)
   - Repository: Select your repository
   - Branch: **main** (or your default branch)
   - Deployment trigger: **Automatic** (recommended)

3. **Configure Build**
   - Configuration file: **Use configuration file** 
   - Configuration file location: **apprunner.yaml**
   - (This will use our pre-configured settings)

4. **Configure Service**
   - Service name: `java-migration-tool`
   - Virtual CPU: **1 vCPU** (can scale up later)
   - Virtual memory: **2 GB** (recommended for Java execution)
   - Environment variables:
     ```
     OPENAI_API_KEY=your-openai-api-key-here
     ANTHROPIC_API_KEY=your-anthropic-api-key-here
     ```

5. **Configure Auto Scaling** (Optional)
   - Concurrency: **100** (requests per instance)
   - Min size: **1** instance
   - Max size: **10** instances

6. **Configure Health Check**
   - Health check path: `/_stcore/health`
   - Interval: **10 seconds**
   - Timeout: **5 seconds**
   - Healthy threshold: **1**
   - Unhealthy threshold: **5**

7. **Configure Security** (Optional)
   - Custom domain: Add your domain if you have one
   - WAF: Enable if needed for additional security

### Step 3: Deploy and Monitor

1. **Click "Create & Deploy"**
   - App Runner will:
     - Clone your repository
     - Build the Docker image
     - Deploy the service
     - Provide a public URL

2. **Monitor Deployment**
   - Watch the deployment logs
   - Wait for status to show "Running"
   - Note the provided App Runner URL

3. **Test Your Application**
   - Visit the App Runner URL
   - Test Java code execution
   - Test migration functionality
   - Verify API integrations work

## 🔧 Configuration Details

### Environment Variables
Set these in the App Runner service configuration:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | Optional |
| `PORT` | Application port (auto-set to 8080) | Auto |

### Resource Recommendations

| Usage Level | vCPU | Memory | Cost/Month* |
|-------------|------|--------|-------------|
| **Development** | 0.25 | 0.5 GB | ~$15-25 |
| **Production** | 1.0 | 2 GB | ~$35-55 |
| **High Traffic** | 2.0 | 4 GB | ~$70-100 |

*Estimated costs based on moderate usage

### Scaling Configuration
- **Concurrency**: 100 requests per instance (recommended)
- **Min instances**: 1 (always available)
- **Max instances**: 10 (adjust based on expected traffic)

## 🔍 Troubleshooting

### Common Issues

1. **Build Fails**
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt
   - Check App Runner build logs

2. **Health Check Fails**
   - Verify application starts on port 8080
   - Check `/_stcore/health` endpoint responds
   - Review application logs

3. **Java Execution Fails**
   - Verify Java is installed in container
   - Check file permissions in /tmp/java-workspace
   - Review Java execution logs

4. **API Integration Issues**
   - Verify environment variables are set
   - Test API keys independently
   - Check network connectivity

### Monitoring and Logs
- **App Runner Logs**: Available in the AWS Console
- **CloudWatch**: Automatic integration for metrics
- **Health Checks**: Monitor in App Runner dashboard

## 🎯 Post-Deployment Checklist

- [ ] Application accessible via App Runner URL
- [ ] Health check endpoint responding
- [ ] Java code execution working
- [ ] Migration functionality tested
- [ ] API keys configured and working
- [ ] Custom domain configured (if needed)
- [ ] Monitoring and alerts set up
- [ ] Performance testing completed

## 🔄 Updates and Maintenance

### Automatic Deployments
- App Runner automatically deploys when you push to the main branch
- Monitor deployments in the App Runner console

### Manual Deployments
- Go to App Runner service
- Click "Deploy" to trigger manual deployment

### Scaling
- Adjust vCPU/memory in service configuration
- Modify auto-scaling settings as needed

## 💰 Cost Optimization

1. **Right-size Resources**
   - Start with 1 vCPU / 2 GB
   - Monitor usage and adjust

2. **Optimize Auto-scaling**
   - Set appropriate min/max instances
   - Adjust concurrency based on performance

3. **Monitor Usage**
   - Use CloudWatch to track resource usage
   - Optimize based on actual traffic patterns

## 🔗 Useful Links

- [AWS App Runner Documentation](https://docs.aws.amazon.com/apprunner/)
- [App Runner Pricing](https://aws.amazon.com/apprunner/pricing/)
- [Streamlit Deployment Guide](https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app)

---

**Need Help?** Check the troubleshooting section or review App Runner logs in the AWS Console.