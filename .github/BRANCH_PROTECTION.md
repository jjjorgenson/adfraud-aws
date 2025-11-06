# Branch Protection Rules

This document describes the branch protection rules that should be configured in GitHub.

## Main Branch Protection

Configure the following rules for the `main` branch in GitHub Settings > Branches:

### Required Settings

1. **Require a pull request before merging**
   - ✅ Require approvals: 1
   - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require review from Code Owners (if CODEOWNERS file exists)

2. **Require status checks to pass before merging**
   - ✅ Require branches to be up to date before merging
   - Select required status checks:
     - `build` (if configured)
     - `test` (if configured)
     - `lint` (if configured)

3. **Require conversation resolution before merging**
   - ✅ All comments must be resolved

4. **Restrict who can push to matching branches**
   - Leave empty (allows PRs from any branch)

5. **Do not allow bypassing the above settings**
   - ✅ Even administrators must follow these rules

6. **Additional Settings**
   - ❌ Do not allow force pushes
   - ❌ Do not allow deletions
   - ✅ Include administrators

## Develop Branch Protection

Configure the following rules for the `develop` branch:

1. **Require a pull request before merging**
   - ✅ Require approvals: 1
   - ✅ Dismiss stale pull request approvals when new commits are pushed

2. **Require status checks to pass before merging**
   - ✅ Require branches to be up to date before merging

3. **Additional Settings**
   - ⚠️ Allow force pushes (for rebasing)
   - ❌ Do not allow deletions
   - ✅ Include administrators

## Setup Instructions

1. Go to GitHub repository Settings
2. Navigate to Branches
3. Click "Add rule" or "Edit" for existing branch
4. Enter branch name pattern: `main` or `develop`
5. Configure the settings as described above
6. Click "Create" or "Save changes"

## Testing Branch Protection

To verify branch protection is working:

1. Try to push directly to main:
   ```bash
   git checkout main
   git commit --allow-empty -m "test: verify branch protection"
   git push origin main
   ```
   This should fail if protection is enabled.

2. Create a pull request from a feature branch to main
3. Verify that:
   - PR requires approval
   - Status checks must pass
   - Direct push is blocked

