#!/bin/bash
# Setup ECR Repository for Dashboard Deployment
# This script creates the ECR repository needed for dashboard Docker images

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-fraudguard-dashboard}"

echo "=========================================="
echo "Setting up ECR Repository for Dashboard"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    echo "   Visit: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials are not configured."
    echo "   Run: aws configure"
    exit 1
fi

echo "✅ AWS CLI is configured"
echo ""

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: ${AWS_ACCOUNT_ID}"
echo "Region: ${AWS_REGION}"
echo "Repository: ${ECR_REPOSITORY}"
echo ""

# Check if repository already exists
if aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" &> /dev/null; then
    echo "⚠️  Repository '${ECR_REPOSITORY}' already exists"
    REPO_URI=$(aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" --query 'repositories[0].repositoryUri' --output text)
    echo "Repository URI: ${REPO_URI}"
    echo ""
    echo "✅ Repository is ready to use"
else
    echo "Creating ECR repository..."
    
    # Create repository
    aws ecr create-repository \
        --repository-name "${ECR_REPOSITORY}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        --image-tag-mutability MUTABLE \
        --output json
    
    echo ""
    echo "✅ Repository created successfully"
    
    # Get repository URI
    REPO_URI=$(aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" --query 'repositories[0].repositoryUri' --output text)
    echo "Repository URI: ${REPO_URI}"
    echo ""
fi

# Display repository details
echo "=========================================="
echo "ECR Repository Details"
echo "=========================================="
echo "Repository Name: ${ECR_REPOSITORY}"
echo "Repository URI: ${REPO_URI}"
echo "Region: ${AWS_REGION}"
echo ""

# Display lifecycle policy recommendation
echo "=========================================="
echo "Recommended Lifecycle Policy"
echo "=========================================="
echo "Consider setting up a lifecycle policy to manage old images:"
echo ""
cat <<EOF
aws ecr put-lifecycle-policy \\
    --repository-name ${ECR_REPOSITORY} \\
    --region ${AWS_REGION} \\
    --lifecycle-policy-text '{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}'
EOF
echo ""

# Display IAM policy recommendation
echo "=========================================="
echo "Required IAM Permissions"
echo "=========================================="
echo "The IAM user/role used in GitHub Actions needs these permissions:"
echo ""
cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "apprunner:CreateService",
        "apprunner:DescribeService",
        "apprunner:ListServices",
        "apprunner:StartDeployment",
        "apprunner:UpdateService"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/service-role/*"
    }
  ]
}
EOF
echo ""

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo "1. Configure GitHub Secrets (see setup_github_secrets.sh)"
echo "2. Test the deployment workflow"
echo "3. Monitor deployments in GitHub Actions"
echo ""

