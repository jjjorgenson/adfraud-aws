# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD automation.

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

Runs on every push and pull request to `main` and `develop` branches.

**Jobs:**
- **Lint**: Code linting with flake8, black, isort, and mypy
- **Test**: Run unit tests with pytest and coverage
- **Build**: Build SAM application and validate template
- **Security**: Security scanning with Bandit and Safety

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

### 2. CD Workflow (`.github/workflows/cd.yml`)

Deploys the application to AWS when code is pushed to `main` or manually triggered.

**Jobs:**
- **Deploy**: Build and deploy SAM application to AWS

**Environments:**
- `dev` (default)
- `staging`
- `prod`

**Required Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

**Triggers:**
- Push to `main` branch
- Manual workflow dispatch

### 3. Dashboard Deployment Workflow (`.github/workflows/dashboard-deploy.yml`)

Automatically deploys the Streamlit dashboard to AWS App Runner when dashboard code changes.

**Jobs:**
- **Build and Deploy**: Build Docker image, push to ECR, and update App Runner service

**Environments:**
- `dev` (default)
- `staging`
- `prod`

**Required Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `APP_RUNNER_AUTO_SCALING_ARN` (optional, for auto-scaling configuration)

**Triggers:**
- Push to `main` or `develop` (when dashboard files change)
- Manual workflow dispatch

**Features:**
- Automatic Docker image building
- ECR image push
- App Runner service creation/update
- Environment-specific configuration
- Deployment status tracking

### 4. Test Workflow (`.github/workflows/test.yml`)

Runs comprehensive test suites.

**Jobs:**
- **Unit Tests**: Run unit tests with coverage
- **Integration Tests**: Run integration tests (only on PRs and main branch)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`
- Manual workflow dispatch

### 4. Code Quality Workflow (`.github/workflows/code-quality.yml`)

Performs code quality checks.

**Checks:**
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8, pylint)
- Type checking (mypy)
- Security scanning (bandit, safety)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

### 5. Dependency Review (`.github/workflows/dependency-review.yml`)

Reviews dependencies for security vulnerabilities.

**Triggers:**
- Pull requests to `main` or `develop`

## Setup

### Required Secrets

Configure the following secrets in GitHub Settings > Secrets and variables > Actions:

1. **AWS_ACCESS_KEY_ID**: AWS access key for deployment
2. **AWS_SECRET_ACCESS_KEY**: AWS secret key for deployment

### Required Environments

Create the following environments in GitHub Settings > Environments:

1. **dev**: Development environment
2. **staging**: Staging environment
3. **prod**: Production environment

### Status Badges

Add status badges to your README:

```markdown
![CI](https://github.com/your-org/fraudguard-ai/workflows/CI/badge.svg)
![CD](https://github.com/your-org/fraudguard-ai/workflows/CD/badge.svg)
![Test](https://github.com/your-org/fraudguard-ai/workflows/Test/badge.svg)
```

## Workflow Status

View workflow runs in the Actions tab of your GitHub repository.

## Troubleshooting

### Common Issues

1. **Build failures**: Check SAM template syntax and dependencies
2. **Deployment failures**: Verify AWS credentials and permissions
3. **Test failures**: Check test files and dependencies
4. **Linting failures**: Run `black` and `isort` locally to fix formatting

### Local Testing

Test workflows locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act

# Run CI workflow
act -j lint
act -j test
act -j build
```

