#!/bin/bash
# Programmatic GitHub Secrets Setup
# This script safely sets GitHub secrets using GitHub CLI or API

set -e

echo "=========================================="
echo "Programmatic GitHub Secrets Setup"
echo "=========================================="
echo ""

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) is not installed."
    echo "   Installing GitHub CLI..."
    echo ""
    echo "   macOS: brew install gh"
    echo "   Linux: See https://cli.github.com/manual/installation"
    echo "   Windows: winget install GitHub.cli"
    echo ""
    read -p "Do you want to continue with API method instead? [y/N]: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    USE_API=true
else
    USE_API=false
fi

# Method 1: GitHub CLI (Recommended - Safest)
if [ "$USE_API" = false ]; then
    echo "Using GitHub CLI method (recommended)"
    echo ""
    
    # Check authentication
    if ! gh auth status &> /dev/null; then
        echo "GitHub CLI is not authenticated."
        echo "Starting authentication process..."
        echo ""
        gh auth login
    fi
    
    echo "✅ GitHub CLI is authenticated"
    echo ""
    
    # Get AWS credentials
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI is not installed."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo "❌ AWS credentials are not configured."
        echo "   Run: aws configure"
        exit 1
    fi
    
    echo "Getting AWS credentials..."
    AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
    AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
    
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        echo "❌ Could not retrieve AWS credentials."
        exit 1
    fi
    
    echo "✅ AWS credentials retrieved"
    echo ""
    
    # Set secrets using GitHub CLI
    echo "Setting GitHub secrets..."
    echo ""
    
    # Set AWS_ACCESS_KEY_ID
    echo -n "Setting AWS_ACCESS_KEY_ID... "
    if gh secret set AWS_ACCESS_KEY_ID --body "${AWS_ACCESS_KEY_ID}" &> /dev/null; then
        echo "✅"
    else
        echo "⚠️  (may already exist)"
    fi
    
    # Set AWS_SECRET_ACCESS_KEY
    echo -n "Setting AWS_SECRET_ACCESS_KEY... "
    if gh secret set AWS_SECRET_ACCESS_KEY --body "${AWS_SECRET_ACCESS_KEY}" &> /dev/null; then
        echo "✅"
    else
        echo "⚠️  (may already exist)"
    fi
    
    # Optional: App Runner Auto Scaling ARN
    read -p "Do you want to set APP_RUNNER_AUTO_SCALING_ARN? (optional) [y/N]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter App Runner Auto Scaling Configuration ARN: " AUTO_SCALING_ARN
        if [ -n "$AUTO_SCALING_ARN" ]; then
            echo -n "Setting APP_RUNNER_AUTO_SCALING_ARN... "
            if gh secret set APP_RUNNER_AUTO_SCALING_ARN --body "${AUTO_SCALING_ARN}" &> /dev/null; then
                echo "✅"
            else
                echo "⚠️  (may already exist)"
            fi
        fi
    fi
    
    echo ""
    echo "✅ Secrets configured successfully"
    echo ""
    
    # List secrets
    echo "Current secrets:"
    gh secret list
fi

# Method 2: GitHub API (Alternative)
if [ "$USE_API" = true ]; then
    echo "Using GitHub API method"
    echo ""
    echo "⚠️  This method requires:"
    echo "   1. GitHub Personal Access Token (PAT) with repo scope"
    echo "   2. GitHub's public key for encryption"
    echo ""
    echo "For security, GitHub CLI is recommended instead."
    echo ""
    echo "To use API method, you need to:"
    echo "1. Create a PAT: https://github.com/settings/tokens"
    echo "2. Get repository public key"
    echo "3. Encrypt secrets using the public key"
    echo "4. Send encrypted secrets via API"
    echo ""
    echo "See: https://docs.github.com/en/rest/actions/secrets"
    exit 0
fi

echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo "1. Verify secrets: gh secret list"
echo "2. Test deployment workflow"
echo "3. Monitor deployments in GitHub Actions"
echo ""

