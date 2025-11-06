# Bedrock AI Analysis Setup Guide

This guide explains how to set up and configure Amazon Bedrock for AI-powered fraud analysis.

## Overview

The AI Analyzer Lambda function uses Amazon Bedrock with Claude 3.5 Sonnet to perform deep fraud analysis on borderline cases (ML scores between 0.3 and 0.8).

## Prerequisites

1. **AWS Account** with Bedrock access
2. **Bedrock Model Access**: Request access to Claude 3.5 Sonnet in Bedrock console
3. **IAM Permissions**: Lambda execution role needs `bedrock:InvokeModel` permission

## Model Configuration

### Model ID

- **Claude 3.5 Sonnet**: `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Region**: `us-east-1` (default)
- **API Format**: Anthropic Messages API

### Environment Variables

Set in Lambda function configuration:

```bash
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

## Prompt Engineering

### Base Prompt Structure

The prompt includes:

1. **Event Data**: All event fields (IP, user agent, device, campaign, etc.)
2. **Behavioral Context**: Click counts, timing patterns, historical data
3. **ML Model Assessment**: ML score and context
4. **Industry Benchmarks**: Normal vs. suspicious patterns
5. **Analysis Framework**: Systematic analysis requirements
6. **Output Format**: Strict JSON structure requirements

### Prompt Optimization

- **Temperature**: 0.1 (low for consistent results)
- **Max Tokens**: 1000 (sufficient for JSON response)
- **System Instructions**: Clear role definition and output format

### JSON Output Requirements

The AI must return valid JSON with:

```json
{
    "is_fraud": true,
    "confidence": 0.85,
    "fraud_signals": ["bot_user_agent", "high_click_velocity", "datacenter_ip"],
    "reasoning": "This event shows clear signs of bot traffic...",
    "recommended_action": "block",
    "primary_fraud_type": "bot_traffic",
    "ai_score": 0.87
}
```

## IAM Permissions

### Lambda Execution Role

Add the following policy to your Lambda execution role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
        }
    ]
}
```

## Testing

### Test AI Analyzer Lambda

```bash
# Install dependencies
pip install -r scripts/sagemaker_training_requirements.txt

# Test AI analyzer
python scripts/test_bedrock_ai.py \
  --function-name fraudguard-ai-analyzer \
  --num-tests 10 \
  --output bedrock_test_results.json
```

### Test Scenarios

1. **Bot Traffic**: Headless browser, high click velocity
2. **Click Farm**: Datacenter IPs, coordinated patterns
3. **Device Farm**: Similar devices, mobile patterns
4. **Legitimate**: Normal patterns, valid user agents

## Error Handling

### Common Errors

1. **Access Denied**: Check IAM permissions and Bedrock model access
2. **Invalid Model ID**: Verify model ID is correct and available in your region
3. **JSON Parse Errors**: AI may return markdown or extra text - handled with fallback parsing
4. **Timeout**: Increase Lambda timeout if analysis takes too long

### Fallback Behavior

- If Bedrock fails, return default response with low confidence
- If JSON parsing fails, extract fraud signals from text response
- Always return a response (never fail completely)

## Cost Estimation

### Bedrock Pricing (Claude 3.5 Sonnet)

- **Input**: $3.00 per 1M tokens
- **Output**: $15.00 per 1M tokens

### Estimated Costs

For 100k events/month with 20% requiring AI analysis:
- Average prompt: ~500 tokens
- Average response: ~200 tokens
- Monthly cost: ~$15-20

## Monitoring

### CloudWatch Metrics

- `BedrockInvocationCount`: Number of AI analyses
- `BedrockLatency`: AI analysis latency
- `BedrockErrors`: Error count
- `BedrockCost`: Estimated cost per analysis

### Custom Metrics

- `AI_FraudDetected`: Count of fraud detections by AI
- `AI_Confidence`: Distribution of AI confidence scores
- `AI_FraudTypes`: Distribution of fraud types detected

## Troubleshooting

### Common Issues

1. **Model Not Available**: Request access in Bedrock console
2. **High Latency**: Consider using Claude 3 Haiku for faster responses
3. **Inconsistent JSON**: Improve prompt instructions or add retry logic
4. **High Costs**: Optimize prompt length or use AI only for high-value cases

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check CloudWatch Logs:
- `/aws/lambda/fraudguard-ai-analyzer`

## Best Practices

1. **Prompt Optimization**: Keep prompts concise but comprehensive
2. **JSON Validation**: Always validate and parse JSON responses
3. **Error Handling**: Implement robust fallback mechanisms
4. **Cost Management**: Monitor usage and optimize prompt length
5. **Performance**: Cache common patterns to reduce API calls

## Next Steps

1. Test AI analyzer with various scenarios
2. Monitor performance and costs
3. Optimize prompts based on results
4. Integrate with decision combiner
5. Set up CloudWatch alarms for errors

