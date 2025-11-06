# Safe Programmatic Secret Deployment

This document explains how to safely deploy secrets programmatically to GitHub.

## ✅ Safe Methods

### 1. GitHub CLI (Recommended - Safest)

**Why it's safe:**
- Secrets are encrypted by GitHub CLI before transmission
- Uses OAuth authentication (no tokens stored)
- Secrets never appear in command history
- GitHub handles encryption/decryption

**Usage:**
```bash
# Authenticate (one-time)
gh auth login

# Set secrets (encrypted automatically)
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_KEY"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_SECRET"
```

**Security features:**
- ✅ Secrets encrypted before transmission
- ✅ OAuth-based authentication
- ✅ No secrets in shell history
- ✅ GitHub manages encryption keys

### 2. GitHub API (Secure but Complex)

**Why it's safe:**
- Uses GitHub's public key encryption
- Secrets encrypted client-side before transmission
- Requires proper implementation

**Requirements:**
1. GitHub Personal Access Token (PAT) with `repo` scope
2. Repository public key (from GitHub API)
3. Client-side encryption using public key

**Process:**
```bash
# 1. Get repository public key
curl -H "Authorization: token YOUR_PAT" \
  https://api.github.com/repos/OWNER/REPO/actions/secrets/public-key

# 2. Encrypt secret using public key (requires libsodium)
# 3. Send encrypted secret via API
curl -X PUT \
  -H "Authorization: token YOUR_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/secrets/AWS_ACCESS_KEY_ID \
  -d '{"encrypted_value":"ENCRYPTED_VALUE","key_id":"PUBLIC_KEY_ID"}'
```

**Security features:**
- ✅ End-to-end encryption
- ✅ Secrets never sent in plain text
- ⚠️  Requires proper implementation
- ⚠️  PAT must be secured

## ❌ Unsafe Methods (Never Use)

### 1. Committing Secrets to Git
```bash
# ❌ NEVER DO THIS
echo "AWS_ACCESS_KEY_ID=AKIA..." >> .env
git add .env
git commit -m "Add secrets"  # ❌ Secret exposed in git history
```

### 2. Storing Secrets in Code
```python
# ❌ NEVER DO THIS
AWS_ACCESS_KEY_ID = "AKIA..."  # Exposed in source code
```

### 3. Plain Text in Scripts
```bash
# ❌ NEVER DO THIS
export AWS_ACCESS_KEY_ID="AKIA..."  # Visible in process list
```

### 4. Environment Variables in CI/CD
```yaml
# ❌ NEVER DO THIS
env:
  AWS_ACCESS_KEY_ID: "AKIA..."  # Visible in workflow logs
```

## Best Practices

### 1. Use GitHub CLI (Easiest & Safest)

```bash
# Install GitHub CLI
brew install gh  # macOS
# or see: https://cli.github.com/manual/installation

# Authenticate (one-time, interactive)
gh auth login

# Set secrets (encrypted automatically)
gh secret set AWS_ACCESS_KEY_ID --body "$(aws configure get aws_access_key_id)"
gh secret set AWS_SECRET_ACCESS_KEY --body "$(aws configure get aws_secret_access_key)"
```

### 2. Use Dedicated IAM User

Create a separate IAM user for GitHub Actions:

```bash
# Create IAM user
aws iam create-user --user-name github-actions-dashboard-deploy

# Create access key
aws iam create-access-key --user-name github-actions-dashboard-deploy

# Attach minimal permissions policy
aws iam attach-user-policy \
  --user-name github-actions-dashboard-deploy \
  --policy-arn arn:aws:iam::aws:policy/YourMinimalPolicy
```

### 3. Rotate Credentials Regularly

```bash
# Create new access key
aws iam create-access-key --user-name github-actions-dashboard-deploy

# Update GitHub secret
gh secret set AWS_ACCESS_KEY_ID --body "NEW_KEY"

# Delete old access key
aws iam delete-access-key \
  --user-name github-actions-dashboard-deploy \
  --access-key-id OLD_KEY_ID
```

### 4. Use Environment-Specific Secrets

For production, use GitHub Environments:

```bash
# Set secret for specific environment
gh secret set AWS_ACCESS_KEY_ID \
  --body "PROD_KEY" \
  --env production
```

### 5. Audit Secret Access

```bash
# List all secrets
gh secret list

# Check secret usage in workflows
gh workflow list
```

## Security Checklist

- [ ] Use GitHub CLI for secret management
- [ ] Create dedicated IAM user for GitHub Actions
- [ ] Use minimal IAM permissions
- [ ] Rotate credentials regularly
- [ ] Never commit secrets to git
- [ ] Use environment-specific secrets for production
- [ ] Enable MFA on IAM user (if possible)
- [ ] Monitor secret usage in GitHub Actions
- [ ] Review workflow logs for secret exposure
- [ ] Use secret scanning tools

## Troubleshooting

### GitHub CLI Not Authenticated

```bash
# Authenticate interactively
gh auth login

# Or use token
gh auth login --with-token < token.txt
```

### Secrets Not Accessible in Workflow

- Verify secret names match exactly (case-sensitive)
- Check secrets are set at repository level
- Ensure workflow has access to secrets
- Check environment restrictions

### Access Denied in AWS

- Verify IAM user has correct permissions
- Check IAM policy is attached
- Verify AWS credentials are correct
- Check region matches (us-east-1)

## Additional Resources

- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [GitHub Secrets API](https://docs.github.com/en/rest/actions/secrets)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security/security-advisories)

