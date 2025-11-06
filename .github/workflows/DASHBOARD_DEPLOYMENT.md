# Dashboard Deployment Workflow

This document explains the GitHub Actions workflow for deploying the Fraud Analytics Dashboard to AWS App Runner.

## Overview

The dashboard deployment workflow (`dashboard-deploy.yml`) automatically builds, pushes, and deploys the Streamlit dashboard to AWS App Runner whenever dashboard code changes.

## Workflow Triggers

### Automatic Deployment

The workflow runs automatically when:
- Code is pushed to `main` or `develop` branches
- Changes are made to files in the `dashboard/` directory
- The workflow file itself is updated

### Manual Deployment

You can manually trigger the workflow:
1. Go to GitHub Actions tab
2. Select "Deploy Dashboard" workflow
3. Click "Run workflow"
4. Choose the environment (dev, staging, prod)
5. Click "Run workflow"

## Workflow Steps

### 1. Checkout Code
- Checks out the repository code

### 2. Configure AWS Credentials
- Configures AWS credentials from GitHub secrets
- Required secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### 3. Login to Amazon ECR
- Authenticates with Amazon ECR
- Retrieves ECR registry URL

### 4. Build Docker Image
- Builds Docker image from `dashboard/Dockerfile`
- Tags image with commit SHA and environment
- Creates both versioned and `latest` tags

### 5. Push Docker Image to ECR
- Pushes image to ECR repository
- Both versioned and `latest` tags are pushed

### 6. Get App Runner Service ARN
- Checks if App Runner service exists
- Retrieves service ARN if found

### 7. Create or Update App Runner Service
- **If service doesn't exist**: Creates new App Runner service
- **If service exists**: Starts new deployment with updated image

### 8. Wait for Deployment
- Waits for deployment to complete
- Monitors service status

### 9. Get Service URL
- Retrieves the App Runner service URL
- Displays in workflow summary

## Configuration

### Environment Variables

The workflow uses these environment variables:

- `AWS_REGION`: AWS region (default: `us-east-1`)
- `ECR_REPOSITORY`: ECR repository name (default: `fraudguard-dashboard`)
- `APP_RUNNER_SERVICE`: App Runner service name (default: `fraudguard-dashboard`)

### Environment-Specific Configuration

Each environment has different DynamoDB table names:

- **dev**: `fraudguard-events-dev`
- **staging**: `fraudguard-events-staging`
- **prod**: `fraudguard-events-prod`

### Required GitHub Secrets

1. **AWS_ACCESS_KEY_ID**: AWS access key ID
2. **AWS_SECRET_ACCESS_KEY**: AWS secret access key
3. **APP_RUNNER_AUTO_SCALING_ARN** (optional): Auto-scaling configuration ARN

### Required AWS Resources

1. **ECR Repository**: Must exist before first deployment
   ```bash
   aws ecr create-repository --repository-name fraudguard-dashboard --region us-east-1
   ```

2. **App Runner Service**: Created automatically on first deployment

3. **IAM Permissions**: The AWS credentials need:
   - `ecr:*` permissions for the ECR repository
   - `apprunner:*` permissions
   - `iam:PassRole` for App Runner service role

## Setup Instructions

### 1. Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name fraudguard-dashboard \
  --region us-east-1 \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256
```

### 2. Configure GitHub Secrets

Go to GitHub repository → Settings → Secrets and variables → Actions:

1. Add `AWS_ACCESS_KEY_ID`
2. Add `AWS_SECRET_ACCESS_KEY`
3. Add `APP_RUNNER_AUTO_SCALING_ARN` (optional)

### 3. Create IAM User/Role

Create an IAM user or role with these permissions:

```json
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
```

### 4. Test Deployment

1. Make a change to `dashboard/app.py`
2. Commit and push to `main` or `develop`
3. Check GitHub Actions tab for workflow execution
4. Verify deployment in AWS App Runner console

## Troubleshooting

### Workflow Fails: ECR Repository Not Found

**Error:** `RepositoryNotFoundException`

**Solution:**
```bash
aws ecr create-repository --repository-name fraudguard-dashboard --region us-east-1
```

### Workflow Fails: Access Denied

**Error:** `AccessDeniedException`

**Solution:**
- Verify AWS credentials in GitHub secrets
- Check IAM permissions include ECR and App Runner access
- Ensure IAM user has `iam:PassRole` permission

### Workflow Fails: App Runner Service Creation Failed

**Error:** Service creation fails

**Solution:**
- Check if service name already exists
- Verify auto-scaling configuration ARN (if provided)
- Check App Runner service quotas

### Deployment Takes Too Long

**Solution:**
- App Runner deployments typically take 5-10 minutes
- The workflow waits up to 30 attempts (5 minutes)
- Check App Runner console for deployment status

### Service URL Not Retrieved

**Solution:**
- Deployment may still be in progress
- Check App Runner console manually
- Service URL will be available once deployment completes

## Monitoring

### GitHub Actions

- View workflow runs in GitHub Actions tab
- Check workflow logs for detailed output
- Review deployment summary in workflow run

### AWS App Runner Console

- Monitor service status
- View deployment history
- Check service logs
- Monitor metrics and alarms

### CloudWatch

- App Runner service logs: `/aws/apprunner/fraudguard-dashboard-{env}/service/application`
- Service metrics: CPU, memory, request count, latency

## Best Practices

1. **Test Locally First**: Test dashboard changes locally before pushing
2. **Use Feature Branches**: Test on feature branches before merging to main
3. **Monitor Deployments**: Check deployment status after each push
4. **Review Logs**: Check App Runner logs if dashboard doesn't work
5. **Environment Separation**: Use different environments for dev/staging/prod

## Next Steps

1. ✅ Set up ECR repository
2. ✅ Configure GitHub secrets
3. ✅ Test deployment workflow
4. ✅ Monitor first deployment
5. ✅ Verify dashboard accessibility

