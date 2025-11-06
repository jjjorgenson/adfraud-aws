# Manual GitHub Secrets Setup Guide

Since GitHub CLI is not authenticated, here's how to set up GitHub secrets manually.

## Step 1: Get Your AWS Credentials

### Option A: From AWS CLI Config

```bash
# Get AWS Access Key ID
aws configure get aws_access_key_id

# Get AWS Secret Access Key
aws configure get aws_secret_access_key
```

### Option B: From AWS IAM Console

1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Navigate to **Users** → Select your user → **Security credentials** tab
3. If you don't have an access key, click **Create access key**
4. Save the **Access key ID** and **Secret access key**

### Option C: Create New IAM User for GitHub Actions (Recommended)

For better security, create a dedicated IAM user for GitHub Actions:

```bash
# Create IAM user
aws iam create-user --user-name github-actions-dashboard-deploy

# Create access key
aws iam create-access-key --user-name github-actions-dashboard-deploy

# Save the AccessKeyId and SecretAccessKey from the output
```

Then attach the required policy (see IAM Policy section below).

## Step 2: Set GitHub Secrets

### Method 1: Via GitHub Web UI (Easiest)

1. **Go to your GitHub repository**
   - Navigate to: `https://github.com/YOUR_USERNAME/YOUR_REPO`

2. **Open Settings**
   - Click **Settings** tab (top menu)

3. **Go to Secrets**
   - In the left sidebar, click **Secrets and variables** → **Actions**

4. **Add Secrets**
   - Click **New repository secret** button
   - Add each secret one by one:

   **Secret 1: AWS_ACCESS_KEY_ID**
   - Name: `AWS_ACCESS_KEY_ID`
   - Value: Your AWS access key ID
   - Click **Add secret**

   **Secret 2: AWS_SECRET_ACCESS_KEY**
   - Name: `AWS_SECRET_ACCESS_KEY`
   - Value: Your AWS secret access key
   - Click **Add secret**

   **Secret 3: APP_RUNNER_AUTO_SCALING_ARN** (Optional)
   - Name: `APP_RUNNER_AUTO_SCALING_ARN`
   - Value: Your App Runner auto-scaling configuration ARN (if you have one)
   - Click **Add secret**

### Method 2: Via GitHub CLI (If Authenticated)

First authenticate:
```bash
gh auth login
```

Then set secrets:
```bash
# Set AWS credentials
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_ACCESS_KEY_ID"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_SECRET_ACCESS_KEY"

# Optional: Set auto-scaling ARN
gh secret set APP_RUNNER_AUTO_SCALING_ARN --body "YOUR_AUTO_SCALING_ARN"
```

### Method 3: Via GitHub API

```bash
# Set AWS_ACCESS_KEY_ID
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/actions/secrets/AWS_ACCESS_KEY_ID \
  -d '{"encrypted_value":"YOUR_ENCRYPTED_VALUE","key_id":"YOUR_KEY_ID"}'
```

Note: This method requires encryption using GitHub's public key. See [GitHub API documentation](https://docs.github.com/en/rest/actions/secrets).

## Step 3: Verify Secrets

### Via GitHub Web UI

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. You should see:
   - ✅ `AWS_ACCESS_KEY_ID`
   - ✅ `AWS_SECRET_ACCESS_KEY`
   - ✅ `APP_RUNNER_AUTO_SCALING_ARN` (if set)

### Via GitHub CLI

```bash
gh secret list
```

## Step 4: Create IAM User and Policy (If Needed)

If you created a new IAM user, attach the required policy:

### Create Policy Document

```bash
cat > dashboard-deploy-policy.json <<'EOF'
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
```

### Create and Attach Policy

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create policy
aws iam create-policy \
  --policy-name GitHubActionsDashboardDeploy \
  --policy-document file://dashboard-deploy-policy.json

# Get policy ARN
POLICY_ARN=$(aws iam list-policies --query "Policies[?PolicyName=='GitHubActionsDashboardDeploy'].Arn" --output text)

# Attach policy to user
aws iam attach-user-policy \
  --user-name github-actions-dashboard-deploy \
  --policy-arn ${POLICY_ARN}
```

## Step 5: Test the Setup

1. **Make a small change to dashboard code:**
   ```bash
   echo "# Test" >> dashboard/app.py
   git add dashboard/app.py
   git commit -m "test: trigger dashboard deployment"
   git push
   ```

2. **Check GitHub Actions:**
   - Go to **Actions** tab in your repository
   - Look for "Deploy Dashboard" workflow
   - Verify it runs successfully

3. **Check AWS App Runner:**
   - Go to [AWS App Runner Console](https://console.aws.amazon.com/apprunner/)
   - Verify service is created/updated

## Troubleshooting

### Secrets Not Found in Workflow

- Verify secret names match exactly (case-sensitive)
- Check that secrets are set at repository level (not environment-specific)
- Ensure workflow has access to secrets

### Access Denied Errors

- Verify IAM user has correct permissions
- Check IAM policy is attached correctly
- Verify AWS credentials are correct

### Workflow Fails

- Check workflow logs in GitHub Actions
- Verify ECR repository exists
- Check AWS region matches (us-east-1)

## Security Best Practices

1. **Use dedicated IAM user** for GitHub Actions (not your personal AWS account)
2. **Limit permissions** to only what's needed (ECR + App Runner)
3. **Rotate credentials** regularly
4. **Use environment-specific secrets** for production
5. **Enable MFA** on IAM user if possible

## Next Steps

1. ✅ ECR repository created
2. ✅ GitHub secrets configured
3. ✅ IAM user/policy created (if needed)
4. ✅ Test deployment workflow
5. ✅ Monitor deployments

