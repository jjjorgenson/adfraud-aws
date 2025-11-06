# Dashboard Deployment Setup Guide

This guide walks you through setting up the ECR repository and GitHub secrets needed for automated dashboard deployment.

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws --version
   aws configure
   ```

2. **GitHub CLI** (optional, for automated secret setup)
   ```bash
   gh --version
   gh auth login
   ```

3. **AWS Account** with appropriate permissions:
   - ECR repository creation
   - App Runner service creation
   - IAM role management

## Step 1: Create ECR Repository

### Option A: Using the Setup Script (Recommended)

```bash
cd scripts
chmod +x setup_ecr.sh
./setup_ecr.sh
```

The script will:
- Check AWS CLI configuration
- Create the ECR repository if it doesn't exist
- Display repository details
- Show recommended IAM policies

### Option B: Manual Setup

```bash
aws ecr create-repository \
  --repository-name fraudguard-dashboard \
  --region us-east-1 \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256
```

### Verify Repository

```bash
aws ecr describe-repositories \
  --repository-names fraudguard-dashboard \
  --region us-east-1
```

## Step 2: Configure GitHub Secrets

### Option A: Using the Setup Script (Recommended)

```bash
cd scripts
chmod +x setup_github_secrets.sh
./setup_github_secrets.sh
```

The script will:
- Check GitHub CLI authentication
- Retrieve AWS credentials from AWS CLI config
- Set GitHub secrets automatically

### Option B: Manual Setup via GitHub Web UI

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

#### Required Secrets

**AWS_ACCESS_KEY_ID**
- Description: AWS access key ID for deployment
- Value: Your AWS access key ID
- How to get: `aws configure get aws_access_key_id` or AWS IAM Console

**AWS_SECRET_ACCESS_KEY**
- Description: AWS secret access key for deployment
- Value: Your AWS secret access key
- How to get: `aws configure get aws_secret_access_key` or AWS IAM Console

#### Optional Secrets

**APP_RUNNER_AUTO_SCALING_ARN**
- Description: App Runner auto-scaling configuration ARN
- Value: ARN of your auto-scaling configuration (if you have one)
- How to get: AWS App Runner Console → Auto Scaling Configurations

### Option C: Manual Setup via GitHub CLI

```bash
# Set AWS credentials
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_ACCESS_KEY_ID"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_SECRET_ACCESS_KEY"

# Optional: Set auto-scaling ARN
gh secret set APP_RUNNER_AUTO_SCALING_ARN --body "YOUR_AUTO_SCALING_ARN"
```

### Verify Secrets

```bash
gh secret list
```

## Step 3: Create IAM User/Role for GitHub Actions

### Option A: Create IAM User (Recommended for GitHub Actions)

1. **Create IAM User:**
   ```bash
   aws iam create-user --user-name github-actions-dashboard-deploy
   ```

2. **Create Access Key:**
   ```bash
   aws iam create-access-key --user-name github-actions-dashboard-deploy
   ```
   Save the `AccessKeyId` and `SecretAccessKey` - you'll need these for GitHub secrets.

3. **Attach Policy:**
   ```bash
   # Create policy document
   cat > dashboard-deploy-policy.json <<EOF
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
         "Resource": "arn:aws:iam::*:role/service-role/*"
       }
     ]
   }
   EOF

   # Create policy
   aws iam create-policy \
     --policy-name GitHubActionsDashboardDeploy \
     --policy-document file://dashboard-deploy-policy.json

   # Attach policy to user
   POLICY_ARN=$(aws iam list-policies --query 'Policies[?PolicyName==`GitHubActionsDashboardDeploy`].Arn' --output text)
   aws iam attach-user-policy \
     --user-name github-actions-dashboard-deploy \
     --policy-arn ${POLICY_ARN}
   ```

### Option B: Use Existing IAM Role

If you already have an IAM role with the necessary permissions, you can use it with OIDC:

1. Configure GitHub OIDC provider in AWS
2. Update the workflow to use OIDC instead of access keys
3. This is more secure but requires additional setup

## Step 4: Test the Setup

### Test ECR Access

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Test push (if you have a Docker image)
docker tag fraudguard-dashboard:latest \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/fraudguard-dashboard:test

docker push \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/fraudguard-dashboard:test
```

### Test GitHub Secrets

1. Go to GitHub Actions tab
2. Select "Deploy Dashboard" workflow
3. Click "Run workflow"
4. Choose environment (dev)
5. Check if workflow runs successfully

## Step 5: Configure Environments (Optional)

For environment-specific deployments (dev, staging, prod):

1. Go to **Settings** → **Environments**
2. Create environments: `dev`, `staging`, `prod`
3. Configure environment-specific secrets if needed
4. Set deployment protection rules if needed

## Troubleshooting

### ECR Repository Not Found

**Error:** `RepositoryNotFoundException`

**Solution:**
```bash
./scripts/setup_ecr.sh
```

### Access Denied

**Error:** `AccessDeniedException`

**Solution:**
- Verify IAM user has correct permissions
- Check IAM policy is attached correctly
- Verify AWS credentials in GitHub secrets

### GitHub Secrets Not Working

**Error:** Secrets not accessible in workflow

**Solution:**
- Verify secrets are set in the correct repository
- Check secret names match workflow expectations
- Ensure secrets are not environment-specific if workflow doesn't use environments

### App Runner Service Creation Fails

**Error:** Service creation fails

**Solution:**
- Check IAM permissions include `apprunner:CreateService`
- Verify `iam:PassRole` permission for App Runner service role
- Check App Runner service quotas

## Verification Checklist

- [ ] ECR repository created and accessible
- [ ] GitHub secrets configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- [ ] IAM user/role has correct permissions
- [ ] GitHub Actions workflow can access secrets
- [ ] Test deployment succeeds
- [ ] Dashboard is accessible after deployment

## Next Steps

1. ✅ Complete setup (ECR + GitHub secrets)
2. ✅ Test deployment workflow
3. ✅ Monitor first deployment
4. ✅ Verify dashboard accessibility
5. ✅ Set up monitoring and alerts

## Additional Resources

- [ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [App Runner Documentation](https://docs.aws.amazon.com/apprunner/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Actions Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments)

