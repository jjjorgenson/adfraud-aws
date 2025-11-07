# Honeypot Landing Page

A honeypot landing page designed to attract and track clicks for fraud detection testing.

## Features

- **Attractive Landing Page**: Designed to look like a legitimate ad landing page
- **Click Tracking**: Tracks all clicks, views, and user interactions
- **Behavioral Analysis**: Monitors mouse movements, visibility changes, and other behavioral signals
- **Fraud Detection Integration**: Automatically sends events to the fraud detection system
- **Real-time Processing**: Events are processed through the fraud orchestrator

## Setup

### Local Development

```bash
cd honeypot
pip install -r requirements.txt
python api.py
```

The honeypot will be available at `http://localhost:8080`

### Docker Deployment

```bash
docker build -t fraudguard-honeypot .
docker run -p 8080:8080 \
  -e INGESTION_FUNCTION=fraudguard-ai-ingestion-handler \
  -e DYNAMODB_TABLE_NAME=fraudguard-events-dev \
  fraudguard-honeypot
```

### AWS Deployment

The honeypot can be deployed to:
- **ECS Fargate**: Similar to the dashboard deployment
- **EC2**: Simple web server
- **Lambda + API Gateway**: Serverless option
- **Elastic Beanstalk**: Easy deployment option

## Usage

1. **Access the Honeypot**: Navigate to the honeypot URL
2. **Interact with the Page**: Click buttons, move mouse, etc.
3. **Events are Tracked**: All interactions are automatically sent to the fraud detection system
4. **View Results**: Check the dashboard to see honeypot events and fraud analysis

## Event Types Tracked

- **Page Views**: When users visit the page
- **Clicks**: Button clicks and interactions
- **Mouse Activity**: Mouse movement patterns
- **Visibility Changes**: When page is hidden/shown (potential bot behavior)
- **Timing Data**: View time, click timing, etc.

## Integration

The honeypot integrates with:
- **DynamoDB**: Stores all events
- **Fraud Orchestrator**: Processes events for fraud detection
- **Dashboard**: Displays honeypot events and analysis

## Configuration

Set environment variables:
- `INGESTION_FUNCTION`: Lambda function name for ingestion
- `DYNAMODB_TABLE_NAME`: DynamoDB table name
- `AWS_REGION`: AWS region (default: us-east-1)

