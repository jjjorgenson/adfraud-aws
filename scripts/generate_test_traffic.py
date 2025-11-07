#!/usr/bin/env python3
"""
Generate Test Traffic for Fraud Detection
Generates diverse test events for all fraud types and sends them to the ingestion handler
"""
import json
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from decimal import Decimal
import boto3
from uuid import uuid4

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Configuration
INGESTION_FUNCTION = 'fraudguard-ai-ingestion-handler'
TABLE_NAME = 'fraudguard-events-dev'
NUM_EVENTS = 200  # Total events to generate
FRAUD_RATIO = 0.4  # 40% fraud, 60% legitimate

# Fraud types to test
FRAUD_TYPES = [
    'bot_traffic',
    'click_farm',
    'device_farm',
    'impersonation',
    'click_injection',
    'incentivized_clicks',
    'competitor_clicking',
    'proxy_fraud'
]

# Bot user agents
BOT_USER_AGENTS = [
    'HeadlessChrome/91.0.4472.124',
    'Mozilla/5.0 (compatible; Googlebot/2.1)',
    'python-requests/2.28.0',
    'curl/7.68.0',
    'Scrapy/2.6.1',
]

# Countries
COUNTRIES = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE', 'CN', 'RU', 'IN']


def generate_event(event_id: str, is_fraud: bool, fraud_type: str = None) -> Dict[str, Any]:
    """Generate a test event"""
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())
    
    # Base event structure
    event = {
        'event_id': event_id,
        'timestamp': timestamp,
        'event_type': 'click',
        'campaign_id': f'campaign-{random.randint(1, 20)}',
        'publisher_id': f'publisher-{random.randint(1, 10)}',
        'device_id': str(uuid4()),
        'ip_address': f'{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}',
        'ip_country': random.choice(COUNTRIES),
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'referrer': 'https://example.com',
        'click_timestamp': timestamp,
        'view_time_ms': random.randint(100, 5000),
    }
    
    if is_fraud and fraud_type:
        # Add fraud-specific patterns
        if fraud_type == 'bot_traffic':
            event['user_agent'] = random.choice(BOT_USER_AGENTS)
            event['view_time_ms'] = random.randint(0, 50)  # Very fast
            event['ip_address'] = f'10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}'  # Datacenter IP
            
        elif fraud_type == 'click_farm':
            event['ip_address'] = f'10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}'
            event['view_time_ms'] = random.randint(0, 100)
            event['device_id'] = f'device-farm-{random.randint(1, 100)}'  # Reused device IDs
            
        elif fraud_type == 'device_farm':
            event['device_id'] = f'device-farm-{random.randint(1, 50)}'
            event['ip_address'] = f'172.16.{random.randint(0, 255)}.{random.randint(0, 255)}'
            event['view_time_ms'] = random.randint(0, 200)
            
        elif fraud_type == 'impersonation':
            event['user_agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
            event['ip_address'] = f'192.168.{random.randint(0, 255)}.{random.randint(0, 255)}'
            event['device_id'] = f'impersonated-{random.randint(1, 20)}'
            
        elif fraud_type == 'click_injection':
            event['event_type'] = 'install'
            event['is_mobile'] = True
            event['click_to_install_time_sec'] = Decimal(str(random.uniform(0.1, 0.9)))  # <1 second
            event['has_recent_install'] = True
            event['install_broadcast_detected'] = True
            event['click_injection_risk_score'] = Decimal('0.95')
            event['user_agent'] = 'Mozilla/5.0 (Linux; Android 10)'
            
        elif fraud_type == 'incentivized_clicks':
            conversion_rate = random.uniform(0.0, 0.001)  # <0.1%
            event['conversion_rate'] = Decimal(str(conversion_rate))
            event['engagement_score'] = Decimal(str(random.uniform(0.0, 0.3)))  # Low engagement
            event['clicks_count'] = random.randint(10, 100)
            event['conversions_count'] = int(event['clicks_count'] * conversion_rate)
            
        elif fraud_type == 'competitor_clicking':
            event['ip_address'] = f'203.0.113.{random.randint(1, 254)}'  # Business IP
            event['ip_is_business'] = True
            event['ip_is_competitor'] = random.random() < 0.5
            event['conversion_rate'] = Decimal('0.0')  # Zero conversions
            event['conversions_count'] = 0
            event['clicks_count'] = random.randint(5, 50)
            
        elif fraud_type == 'proxy_fraud':
            event['ip_address'] = f'198.51.100.{random.randint(1, 254)}'  # Proxy IP
            event['ip_is_proxy'] = True
            event['engagement_score'] = Decimal(str(random.uniform(0.0, 0.3)))  # Low engagement
            event['conversion_rate'] = Decimal('0.0')
            event['conversions_count'] = 0
    else:
        # Legitimate event
        event['view_time_ms'] = random.randint(1000, 10000)
        event['conversion_rate'] = Decimal(str(random.uniform(0.01, 0.05)))  # 1-5% normal
        event['engagement_score'] = Decimal(str(random.uniform(0.5, 1.0)))
    
    return event


def convert_decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    else:
        return obj


def send_event(event: Dict[str, Any]) -> bool:
    """Send event to ingestion handler Lambda"""
    try:
        # Convert Decimal to float for JSON serialization
        event_json = convert_decimal_to_float(event)
        
        # Create API Gateway-like event structure
        lambda_event = {
            'body': json.dumps(event_json),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=INGESTION_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(lambda_event)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            return True
        else:
            print(f"❌ Error: {result.get('body', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception sending event: {str(e)}")
        return False


def main():
    """Generate and send test traffic"""
    print(f"🚀 Generating {NUM_EVENTS} test events...")
    print(f"   Fraud ratio: {FRAUD_RATIO * 100}%")
    print(f"   Fraud types: {', '.join(FRAUD_TYPES)}")
    print()
    
    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'legitimate': 0,
        'fraud': 0,
        'by_type': {ft: 0 for ft in FRAUD_TYPES}
    }
    
    # Generate events
    for i in range(NUM_EVENTS):
        is_fraud = random.random() < FRAUD_RATIO
        fraud_type = random.choice(FRAUD_TYPES) if is_fraud else None
        
        event_id = f'test-{int(time.time())}-{i}'
        event = generate_event(event_id, is_fraud, fraud_type)
        
        # Send event
        success = send_event(event)
        
        stats['total'] += 1
        if success:
            stats['success'] += 1
            if is_fraud:
                stats['fraud'] += 1
                stats['by_type'][fraud_type] += 1
            else:
                stats['legitimate'] += 1
        else:
            stats['failed'] += 1
        
        # Progress update
        if (i + 1) % 20 == 0:
            print(f"   Progress: {i + 1}/{NUM_EVENTS} events sent ({stats['success']} successful)")
        
        # Small delay to avoid throttling
        time.sleep(0.1)
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 Test Traffic Generation Summary")
    print("=" * 60)
    print(f"Total events: {stats['total']}")
    print(f"✅ Successful: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print()
    print(f"Legitimate events: {stats['legitimate']}")
    print(f"Fraud events: {stats['fraud']}")
    print()
    print("Fraud breakdown by type:")
    for fraud_type, count in stats['by_type'].items():
        if count > 0:
            print(f"  • {fraud_type}: {count}")
    print()
    print("✅ Test traffic generation complete!")
    print(f"   Check the dashboard at: http://fraudguard-ai-dashboard-alb-1713344967.us-east-1.elb.amazonaws.com")


if __name__ == '__main__':
    main()

