"""
AI Analyzer Lambda Function
Deep fraud analysis using Amazon Bedrock Claude
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Environment variables
# Note: For Claude 3.5 Sonnet, you may need to use an inference profile
# Check AWS Bedrock Console for the correct model ID or inference profile
BEDROCK_MODEL_ID = os.environ.get(
    'BEDROCK_MODEL_ID',
    'anthropic.claude-3-5-sonnet-20240620-v1:0'  # Use v1 for on-demand, v2 requires inference profile
)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Analyze event using AI for deep fraud detection
    
    Args:
        event: Event data with ML score and features
        context: Lambda context object
        
    Returns:
        AI analysis result
    """
    try:
        # Parse event data
        if 'body' in event:
            body = json.loads(event.get('body', '{}'))
        else:
            body = event
        
        # Extract data
        ml_score = body.get('ml_score', 0.5)
        feature_vector = body.get('feature_vector', [])
        features = body.get('features', {})
        event_data = {k: v for k, v in body.items() if k not in ['ml_score', 'features', 'feature_vector']}
        
        # Build prompt for Claude
        prompt = build_fraud_analysis_prompt(event_data, ml_score, features, feature_vector)
        
        # Call Bedrock
        ai_result = call_bedrock(prompt)
        
        # Parse and validate response
        parsed_result = parse_ai_response(ai_result, body.get('event_id'))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(parsed_result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to analyze with AI',
                'is_fraud': False,
                'confidence': 0.0,
                'ai_score': 0.0
            })
        }


def build_fraud_analysis_prompt(
    event_data: Dict[str, Any],
    ml_score: float,
    features: Dict[str, Any],
    feature_vector: Optional[List[float]] = None
) -> str:
    """
    Build prompt for Claude fraud analysis
    
    Args:
        event_data: Original event data
        ml_score: ML fraud score
        features: Extracted features
        feature_vector: Feature vector array
        
    Returns:
        Formatted prompt string
    """
    # Use enhanced prompt template
    try:
        from prompt_templates import build_base_prompt
        return build_base_prompt(event_data, ml_score, features, feature_vector)
    except ImportError:
        # Fallback to inline prompt
        pass
    
    # Fallback prompt (original implementation)
    prompt = f"""You are an expert ad fraud detection analyst. Analyze the following ad event and determine if it shows signs of fraudulent activity.

EVENT DATA:
===========
Event ID: {event_data.get('event_id', 'unknown')}
Timestamp: {event_data.get('timestamp', 'unknown')}
Event Type: {event_data.get('event_type', 'unknown')}
IP Address: {event_data.get('ip_address', 'unknown')}
User Agent: {event_data.get('user_agent', 'unknown')}
Device ID: {event_data.get('device_id', 'unknown')}
Campaign ID: {event_data.get('campaign_id', 'unknown')}
Referrer: {event_data.get('referrer', 'unknown')}

BEHAVIORAL CONTEXT:
===================
- IP click count (24h): {features.get('ip_click_count_24h', event_data.get('ip_click_count_24h', 0))}
- Device click count (1h): {features.get('device_click_count_1h', event_data.get('device_click_count_1h', 0))}
- Time since last click: {features.get('time_since_last_click', event_data.get('time_since_last_click', 'unknown'))} seconds
- Click to view time: {event_data.get('click_to_view_time_ms', 0)} ms
- Campaign fraud rate: {event_data.get('campaign_fraud_rate', 0.0):.2f}
- Publisher quality: {event_data.get('publisher_quality', 0.5):.2f}

ML MODEL ASSESSMENT:
====================
The ML model scored this event as {ml_score:.2f} (0=legitimate, 1=fraud)

INDUSTRY BENCHMARKS:
====================
- Normal user clicks 1-3 ads per hour
- Normal inter-click time: 30-300 seconds
- Bot signatures: Headless browsers, missing browser features
- Datacenter IPs indicate click farms

ANALYSIS REQUIREMENTS:
======================
Analyze the following aspects systematically:

1. USER AGENT ANALYSIS:
   - Check for bot signatures: "headless", "phantom", "selenium", "webdriver", "curl", "python-requests"
   - Verify browser features: Missing common browser headers suggests automation
   - User agent entropy: Low entropy indicates automated generation

2. CLICK PATTERN ANALYSIS:
   - Inter-click timing: Normal users have 30-300 seconds between clicks
   - Click velocity: >10 clicks/hour from same device is suspicious
   - Click consistency: Perfectly regular intervals suggest automation

3. IP REPUTATION ANALYSIS:
   - Datacenter IPs: 10.x.x.x, 172.16-31.x.x, 192.168.x.x ranges indicate click farms
   - VPN/Proxy usage: High VPN usage can indicate fraud
   - Geographic consistency: IP location should match device location

4. BEHAVIORAL ANOMALIES:
   - Unnatural click sequences: Too fast, too regular, or too many
   - Missing referrer: Legitimate clicks usually have referrers
   - Low view time: <100ms suggests automated clicks

5. CONTEXTUAL FLAGS:
   - Campaign context: High fraud rate campaigns need extra scrutiny
   - Publisher quality: Low quality publishers have higher fraud rates
   - Time patterns: Fraud often occurs at unusual hours

OUTPUT FORMAT (JSON ONLY):
===========================
Return ONLY valid JSON with this exact structure. Do NOT include markdown code blocks:
{{
    "is_fraud": true or false,
    "confidence": 0.0 to 1.0,
    "fraud_signals": ["signal1", "signal2", "signal3"],
    "reasoning": "2-3 sentence explanation citing specific evidence from the analysis above",
    "recommended_action": "block" or "allow" or "review",
    "primary_fraud_type": "bot_traffic" or "click_farm" or "device_farm" or "impersonation" or "legitimate" or "unknown",
    "ai_score": 0.0 to 1.0
}}

CRITICAL: 
- Respond with ONLY the JSON object
- No markdown formatting (no ```json or ```)
- No explanatory text before or after
- Ensure all boolean values are lowercase (true/false, not True/False)
- Ensure all numeric values are numbers, not strings"""
    
    return prompt


def call_bedrock(prompt: str) -> str:
    """
    Call Amazon Bedrock Claude model
    
    Args:
        prompt: Analysis prompt
        
    Returns:
        AI response text
    """
    try:
        # Use Claude 3.5 Sonnet API format
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1000,
                'temperature': 0.1,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        # Handle Claude 3.5 response format
        if 'content' in response_body:
            # New format with content array
            content = response_body['content']
            if isinstance(content, list) and len(content) > 0:
                return content[0].get('text', '')
            return str(content)
        elif 'completion' in response_body:
            # Legacy format
            return response_body['completion']
        else:
            # Fallback
            return json.dumps(response_body)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Bedrock API error: {str(e)}")


def parse_ai_response(ai_text: str, event_id: str) -> Dict[str, Any]:
    """
    Parse AI response and extract fraud analysis
    
    Args:
        ai_text: Raw AI response text
        event_id: Event ID for error context
        
    Returns:
        Parsed analysis result
    """
    try:
        # Try to extract JSON from response
        # Remove markdown code blocks if present
        cleaned_text = ai_text.strip()
        if cleaned_text.startswith('```'):
            # Remove code block markers
            lines = cleaned_text.split('\n')
            cleaned_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned_text
        
        # Parse JSON
        result = json.loads(cleaned_text)
        
        # Validate required fields
        required_fields = ['is_fraud', 'confidence', 'ai_score']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        
        # Ensure types are correct
        return {
            'is_fraud': bool(result.get('is_fraud', False)),
            'confidence': float(result.get('confidence', 0.0)),
            'ai_score': float(result.get('ai_score', 0.0)),
            'fraud_signals': result.get('fraud_signals', []),
            'reasoning': result.get('reasoning', ''),
            'recommended_action': result.get('recommended_action', 'review'),
            'primary_fraud_type': result.get('primary_fraud_type', 'unknown')
        }
        
    except json.JSONDecodeError as e:
        # Fallback: return default result
        print(f"Error parsing AI response: {str(e)}")
        print(f"Response text: {ai_text[:500]}")
        return {
            'is_fraud': False,
            'confidence': 0.0,
            'ai_score': 0.0,
            'fraud_signals': [],
            'reasoning': 'Failed to parse AI response',
            'recommended_action': 'review',
            'primary_fraud_type': 'unknown'
        }

