#!/usr/bin/env python3
"""
Honeypot Lambda Function
Receives and processes clicks from honeypot landing page via API Gateway
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

import boto3

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Configuration
INGESTION_FUNCTION = os.environ.get('INGESTION_FUNCTION', 'fraudguard-ai-ingestion-handler')
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'fraudguard-events-dev')


def convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj


def get_client_ip(event: Dict[str, Any]) -> str:
    """Get client IP address from API Gateway event"""
    # Try different headers for IP
    headers = event.get('headers', {}) or {}
    
    # Handle case-insensitive headers
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    if 'x-forwarded-for' in headers_lower:
        return headers_lower['x-forwarded-for'].split(',')[0].strip()
    elif 'x-real-ip' in headers_lower:
        return headers_lower['x-real-ip']
    elif 'requestcontext' in event:
        # API Gateway V2
        request_context = event.get('requestContext', {})
        if 'http' in request_context:
            return request_context['http'].get('sourceIp', '0.0.0.0')
        elif 'identity' in request_context:
            return request_context['identity'].get('sourceIp', '0.0.0.0')
    
    return '0.0.0.0'


def serve_html() -> Dict[str, Any]:
    """Serve the honeypot landing page HTML"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exclusive Offer - Limited Time!</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }
        h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle { color: #666; font-size: 1.2em; margin-bottom: 30px; }
        .offer-box {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin: 30px 0;
        }
        .cta-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 20px 50px;
            font-size: 1.3em;
            font-weight: bold;
            border-radius: 50px;
            cursor: pointer;
            transition: transform 0.2s;
            margin: 20px 10px;
            text-decoration: none;
            display: inline-block;
        }
        .cta-button:hover { transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎁 Exclusive Offer!</h1>
        <p class="subtitle">Don't miss out on this limited-time opportunity</p>
        <div class="offer-box">
            <h2>Special Discount</h2>
            <p>Claim your reward now!</p>
        </div>
        <a href="#" class="cta-button" id="claimButton" onclick="trackClick(event)">Claim Now - Free!</a>
        <a href="#" class="cta-button" id="learnMoreButton" onclick="trackClick(event)">Learn More</a>
    </div>
    <script>
        const trackingId = 'honeypot-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const campaignId = 'honeypot-campaign-1';
        sessionStorage.setItem('honeypot_tracking_id', trackingId);
        sessionStorage.setItem('page_load_time', Date.now().toString());
        
        function trackPageView() {
            const event = {
                event_id: trackingId + '-view',
                event_type: 'view',
                campaign_id: campaignId,
                publisher_id: 'honeypot-publisher',
                device_id: getDeviceId(),
                view_timestamp: Math.floor(Date.now() / 1000),
                page_url: window.location.href,
                honeypot: true
            };
            sendEvent(event);
        }
        
        function trackClick(e) {
            e.preventDefault();
            const event = {
                event_id: trackingId + '-click-' + Date.now(),
                event_type: 'click',
                campaign_id: campaignId,
                publisher_id: 'honeypot-publisher',
                device_id: getDeviceId(),
                click_timestamp: Math.floor(Date.now() / 1000),
                click_id: trackingId + '-click',
                page_url: window.location.href,
                button_id: e.target.id || 'unknown',
                honeypot: true,
                view_time_ms: Date.now() - (parseInt(sessionStorage.getItem('page_load_time')) || Date.now())
            };
            sendEvent(event);
            e.target.textContent = '✓ Click Tracked!';
            e.target.style.background = '#4CAF50';
            setTimeout(() => {
                e.target.textContent = e.target.id === 'claimButton' ? 'Claim Now - Free!' : 'Learn More';
                e.target.style.background = '';
            }, 2000);
        }
        
        function getDeviceId() {
            let deviceId = localStorage.getItem('device_id');
            if (!deviceId) {
                deviceId = 'device-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('device_id', deviceId);
            }
            return deviceId;
        }
        
        function sendEvent(event) {
            fetch('/api/track', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(event)
            })
            .then(response => response.json())
            .then(data => console.log('Honeypot event tracked:', data))
            .catch(err => console.log('Honeypot event tracked (fallback):', event));
        }
        
        window.addEventListener('load', () => { trackPageView(); });
    </script>
</body>
</html>
"""
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*'
        },
        'body': html_content
    }


def track_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Track honeypot events"""
    try:
        # Parse request body
        body = event.get('body', '{}')
        if isinstance(body, str):
            event_data = json.loads(body)
        else:
            event_data = body
        
        if not event_data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No data provided', 'status': 'error'})
            }
        
        # Enrich event with server-side data
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())
        client_ip = get_client_ip(event)
        
        # Get user agent from headers
        headers = event.get('headers', {}) or {}
        headers_lower = {k.lower(): v for k, v in headers.items()}
        user_agent = headers_lower.get('user-agent', event_data.get('user_agent', ''))
        referrer = headers_lower.get('referer', event_data.get('referrer', ''))
        
        # Create enriched event
        enriched_event = {
            'event_id': event_data.get('event_id', str(uuid4())),
            'timestamp': timestamp,
            'event_type': event_data.get('event_type', 'click'),
            'campaign_id': event_data.get('campaign_id', 'honeypot-campaign-1'),
            'publisher_id': event_data.get('publisher_id', 'honeypot-publisher'),
            'device_id': event_data.get('device_id', 'unknown'),
            'ip_address': client_ip,
            'user_agent': user_agent,
            'referrer': referrer,
            'click_id': event_data.get('click_id', ''),
            'raw_data': event_data,
            'honeypot': True,
            'ttl': timestamp + (7 * 24 * 60 * 60),  # 7 days TTL
            'created_at': now.isoformat(),
            'ip_click_count_24h': 0,
            'device_click_count_1h': 0,
            'time_since_last_click': None,
        }
        
        # Add honeypot-specific fields
        if 'view_time_ms' in event_data:
            enriched_event['view_time_ms'] = event_data['view_time_ms']
        if 'button_id' in event_data:
            enriched_event['button_id'] = event_data['button_id']
        if 'page_url' in event_data:
            enriched_event['page_url'] = event_data['page_url']
        
        # Convert floats to Decimal
        enriched_event = convert_floats_to_decimal(enriched_event)
        
        # Store in DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=enriched_event)
        
        # Trigger fraud orchestrator asynchronously
        try:
            # Convert Decimal back to float for JSON serialization
            def convert_decimal_to_float(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_decimal_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimal_to_float(item) for item in obj]
                else:
                    return obj
            
            event_for_lambda = convert_decimal_to_float(enriched_event)
            
            lambda_client.invoke(
                FunctionName=INGESTION_FUNCTION,
                InvocationType='Event',  # Async
                Payload=json.dumps({
                    'body': json.dumps(event_for_lambda)
                })
            )
        except Exception as e:
            print(f"Error triggering orchestrator: {str(e)}")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'status': 'success',
                'event_id': enriched_event['event_id'],
                'message': 'Event tracked successfully'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': str(e),
                'status': 'error'
            })
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for honeypot API Gateway
    
    Routes:
    - GET / -> Serve HTML landing page
    - POST /api/track -> Track events
    """
    try:
        # Get request path and method
        request_context = event.get('requestContext', {})
        
        # API Gateway V2 (HTTP API)
        if 'http' in request_context:
            path = request_context['http'].get('path', '/')
            method = request_context['http'].get('method', 'GET')
        # API Gateway V1 (REST API)
        else:
            path = event.get('path', '/')
            method = event.get('httpMethod', 'GET')
        
        # Route requests
        if path == '/' and method == 'GET':
            return serve_html()
        elif path == '/api/track' and method == 'POST':
            return track_event(event)
        else:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

