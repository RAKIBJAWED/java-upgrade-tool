#!/bin/bash

# AWS App Runner Deployment Script
echo "🚀 Deploying to AWS App Runner"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    echo "   git branch -M main"
    echo "   git remote add origin <your-github-repo-url>"
    echo "   git push -u origin main"
    exit 1
fi

# Check if there are uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Uncommitted changes detected. Committing them..."
    git add .
    git commit -m "App Runner deployment updates - $(date)"
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push origin main || {
    echo "❌ Failed to push to GitHub. Please check your remote repository."
    echo "   Make sure you have set up the remote:"
    echo "   git remote add origin <your-github-repo-url>"
    exit 1
}

echo "✅ Code pushed to GitHub successfully!"
echo ""
echo "🎯 Next Steps:"
echo ""
echo "1. 🌐 Go to AWS App Runner Console:"
echo "   https://console.aws.amazon.com/apprunner/"
echo ""
echo "2. 📋 Create Service with these settings:"
echo "   • Source: Source code repository"
echo "   • Provider: GitHub"
echo "   • Repository: $(git remote get-url origin 2>/dev/null || echo 'your-repository')"
echo "   • Branch: main"
echo "   • Configuration file: apprunner.yaml"
echo ""
echo "3. 🔑 Add Environment Variables:"
echo "   • OPENAI_API_KEY=your-openai-key"
echo "   • ANTHROPIC_API_KEY=your-anthropic-key"
echo ""
echo "4. ⚙️ Recommended Settings:"
echo "   • Service name: java-migration-tool"
echo "   • vCPU: 1"
echo "   • Memory: 2 GB"
echo "   • Auto scaling: 1-10 instances"
echo ""
echo "5. 🚀 Click 'Create & Deploy'"
echo ""
echo "📖 For detailed instructions, see: AWS_APP_RUNNER_DEPLOYMENT.md"
echo ""
echo "🎉 Your application will be available at the App Runner URL once deployed!"

# Create a reminder file
cat > app-runner-deployment-reminder.txt << 'EOF'
AWS App Runner Deployment Reminder
==================================

Your code has been pushed to GitHub and is ready for App Runner deployment.

Next Steps:
1. Go to: https://console.aws.amazon.com/apprunner/
2. Click "Create service"
3. Select "Source code repository" → GitHub
4. Choose your repository and main branch
5. Use configuration file: apprunner.yaml
6. Add environment variables for API keys
7. Deploy!

Configuration Files Created:
- apprunner.yaml (App Runner configuration)
- AWS_APP_RUNNER_DEPLOYMENT.md (Detailed guide)
- Dockerfile (Updated for App Runner)

Your app will be available at: https://[random-id].awsapprunner.com/

Don't forget to:
- Set your API keys in environment variables
- Test the deployment thoroughly
- Set up custom domain (optional)
EOF

echo "📝 Created app-runner-deployment-reminder.txt for reference"