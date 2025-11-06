#!/bin/bash
# Setup GitHub Secrets for Dashboard Deployment
# This script helps you configure GitHub secrets for the deployment workflow

set -e

echo "=========================================="
echo "GitHub Secrets Setup Guide"
echo "=========================================="
echo ""

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) is not installed."
    echo "   You can install it from: https://cli.github.com/"
    echo ""
    echo "   Alternatively, you can set secrets manually:"
    echo "   1. Go to your GitHub repository"
    echo "   2. Settings → Secrets and variables → Actions"
    echo "   3. Add the following secrets:"
    echo ""
    echo "   Required Secrets:"
    echo "   - AWS_ACCESS_KEY_ID"
    echo "   - AWS_SECRET_ACCESS_KEY"
    echo "   - APP_RUNNER_AUTO_SCALING_ARN (optional)"
    echo ""
    exit 0
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI is not authenticated."
    echo "   Run: gh auth login"
    exit 1
fi

# Get repository name
REPO_NAME=$(gh repo view --json name -q .name)
REPO_OWNER=$(gh repo view --json owner -q .owner.login)

echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo ""

# Check if AWS credentials are configured
if ! command -v aws &> /dev/null; then
    echo "⚠️  AWS CLI is not installed."
    echo "   Please install it and configure credentials first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "⚠️  AWS credentials are not configured."
    echo "   Run: aws configure"
    exit 1
fi

echo "✅ AWS CLI is configured"
echo ""

# Get AWS credentials
echo "Getting AWS credentials..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ Could not retrieve AWS credentials from AWS CLI config."
    echo "   Please provide them manually."
    exit 1
fi

echo "AWS Account ID: ${AWS_ACCOUNT_ID}"
echo ""

# Prompt for secrets
echo "=========================================="
echo "Setting GitHub Secrets"
echo "=========================================="
echo ""

# Set AWS_ACCESS_KEY_ID
echo "Setting AWS_ACCESS_KEY_ID..."
if gh secret set AWS_ACCESS_KEY_ID --body "${AWS_ACCESS_KEY_ID}" &> /dev/null; then
    echo "✅ AWS_ACCESS_KEY_ID set"
else
    echo "⚠️  Failed to set AWS_ACCESS_KEY_ID (may already exist)"
fi

# Set AWS_SECRET_ACCESS_KEY
echo "Setting AWS_SECRET_ACCESS_KEY..."
if gh secret set AWS_SECRET_ACCESS_KEY --body "${AWS_SECRET_ACCESS_KEY}" &> /dev/null; then
    echo "✅ AWS_SECRET_ACCESS_KEY set"
else
    echo "⚠️  Failed to set AWS_SECRET_ACCESS_KEY (may already exist)"
fi

# Optional: App Runner Auto Scaling ARN
echo ""
read -p "Do you want to set APP_RUNNER_AUTO_SCALING_ARN? (optional) [y/N]: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter App Runner Auto Scaling Configuration ARN: " AUTO_SCALING_ARN
    if [ -n "$AUTO_SCALING_ARN" ]; then
        if gh secret set APP_RUNNER_AUTO_SCALING_ARN --body "${AUTO_SCALING_ARN}" &> /dev/null; then
            echo "✅ APP_RUNNER_AUTO_SCALING_ARN set"
        else
            echo "⚠️  Failed to set APP_RUNNER_AUTO_SCALING_ARN"
        fi
    fi
fi

# List all secrets
echo ""
echo "=========================================="
echo "Current GitHub Secrets"
echo "=========================================="
gh secret list

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo "1. Verify secrets are set correctly"
echo "2. Test the deployment workflow"
echo "3. Monitor deployments in GitHub Actions"
echo ""

