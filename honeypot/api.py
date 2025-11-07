#!/usr/bin/env python3
"""
Honeypot API Endpoint
Receives and processes clicks from honeypot landing page
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

import boto3
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

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


def get_client_ip() -> str:
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or '0.0.0.0'


@app.route('/')
def index():
    """Serve honeypot landing page"""
    try:
        return send_from_directory('.', 'index.html')
    except Exception:
        # Fallback: return simple HTML
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Exclusive Offer</title></head>
        <body>
            <h1>🎁 Exclusive Offer!</h1>
            <p>Click the button below to claim your reward!</p>
            <button onclick="trackClick()">Claim Now - Free!</button>
            <script>
                function trackClick() {
                    fetch('/api/track', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            event_type: 'click',
                            campaign_id: 'honeypot-campaign-1',
                            device_id: 'device-' + Date.now()
                        })
                    });
                    alert('Click tracked!');
                }
            </script>
        </body>
        </html>
        '''


@app.route('/api/track', methods=['POST'])
def track_event():
    """Track honeypot events"""
    try:
        event_data = request.get_json()
        
        if not event_data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Enrich event with server-side data
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())
        
        # Get client IP
        client_ip = get_client_ip()
        
        # Create enriched event
        enriched_event = {
            'event_id': event_data.get('event_id', str(uuid4())),
            'timestamp': timestamp,
            'event_type': event_data.get('event_type', 'click'),
            'campaign_id': event_data.get('campaign_id', 'honeypot-campaign-1'),
            'publisher_id': event_data.get('publisher_id', 'honeypot-publisher'),
            'device_id': event_data.get('device_id', 'unknown'),
            'ip_address': client_ip,
            'user_agent': request.headers.get('User-Agent', event_data.get('user_agent', '')),
            'referrer': request.headers.get('Referer', event_data.get('referrer', '')),
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
        
        return jsonify({
            'status': 'success',
            'event_id': enriched_event['event_id'],
            'message': 'Event tracked successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

