"""
Test Bedrock AI Analysis
Tests the AI analyzer Lambda function with various fraud scenarios
"""
import json
import boto3
from typing import Dict, Any, List
from datetime import datetime, timezone

# Configuration
LAMBDA_FUNCTION_NAME = 'fraudguard-ai-analyzer'
REGION = 'us-east-1'


def create_test_event(is_fraud: bool = False, ml_score: float = 0.5) -> Dict[str, Any]:
    """
    Create a test event for AI analysis
    
    Args:
        is_fraud: Whether to create a fraudulent event
        ml_score: ML fraud score
        
    Returns:
        Test event dictionary
    """
    if is_fraud:
        # Fraudulent event
        return {
            'event_id': 'test-fraud-123',
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'event_type': 'click',
            'ip_address': '10.0.0.1',  # Datacenter IP
            'user_agent': 'HeadlessChrome/91.0.4472.124',  # Bot user agent
            'device_id': 'device-fraud-123',
            'campaign_id': 'campaign-1',
            'publisher_id': 'publisher-1',
            'referrer': '',
            'click_id': 'click-123',
            'ip_click_count_24h': 500,  # High click count
            'device_click_count_1h': 50,  # Very high hourly clicks
            'time_since_last_click': 1.0,  # Very fast clicks
            'click_to_view_time_ms': 50,  # Very fast
            'campaign_fraud_rate': 0.8,  # High fraud rate
            'publisher_quality': 0.2,  # Low quality
            'device_fingerprint_entropy': 0.2,  # Similar devices
            'is_mobile': False,
            'is_repeated_click': True,
            'ip_country': 'US',
            'device_os': 'Windows',
            'ml_score': ml_score,
            'features': {
                'ip_click_count_24h': 500,
                'device_click_count_1h': 50,
                'time_since_last_click': 1.0
            }
        }
    else:
        # Legitimate event
        return {
            'event_id': 'test-legit-456',
            'timestamp': int(datetime.now(timezone.utc).timestamp()),
            'event_type': 'click',
            'ip_address': '192.168.1.100',  # Residential IP
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'device_id': 'device-legit-456',
            'campaign_id': 'campaign-1',
            'publisher_id': 'publisher-1',
            'referrer': 'https://example.com',
            'click_id': 'click-456',
            'ip_click_count_24h': 3,  # Normal click count
            'device_click_count_1h': 1,  # Normal hourly clicks
            'time_since_last_click': 300.0,  # Normal timing
            'click_to_view_time_ms': 5000,  # Normal viewing time
            'campaign_fraud_rate': 0.1,  # Low fraud rate
            'publisher_quality': 0.9,  # High quality
            'device_fingerprint_entropy': 0.8,  # Unique device
            'is_mobile': False,
            'is_repeated_click': False,
            'ip_country': 'US',
            'device_os': 'Windows',
            'ml_score': ml_score,
            'features': {
                'ip_click_count_24h': 3,
                'device_click_count_1h': 1,
                'time_since_last_click': 300.0
            }
        }


def test_ai_analyzer_lambda(
    lambda_function_name: str,
    test_events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Test AI analyzer Lambda function
    
    Args:
        lambda_function_name: Lambda function name
        test_events: List of test events
        
    Returns:
        Test results dictionary
    """
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    results = {
        'total_tests': len(test_events),
        'successful': 0,
        'failed': 0,
        'responses': [],
        'errors': []
    }
    
    for i, event in enumerate(test_events):
        try:
            print(f"\nTest {i+1}/{len(test_events)}: {event.get('event_id')}")
            print(f"  ML Score: {event.get('ml_score', 0.5):.2f}")
            print(f"  IP: {event.get('ip_address')}")
            print(f"  User Agent: {event.get('user_agent', '')[:50]}...")
            
            # Invoke Lambda
            response = lambda_client.invoke(
                FunctionName=lambda_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(event)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            if response_payload.get('statusCode') == 200:
                ai_result = json.loads(response_payload.get('body', '{}'))
                
                results['successful'] += 1
                results['responses'].append({
                    'event_id': event.get('event_id'),
                    'is_fraud': ai_result.get('is_fraud'),
                    'ai_score': ai_result.get('ai_score'),
                    'confidence': ai_result.get('confidence'),
                    'primary_fraud_type': ai_result.get('primary_fraud_type'),
                    'fraud_signals': ai_result.get('fraud_signals', []),
                    'reasoning': ai_result.get('reasoning', '')
                })
                
                print(f"  ✅ Success")
                print(f"    Fraud: {ai_result.get('is_fraud')}")
                print(f"    AI Score: {ai_result.get('ai_score', 0):.4f}")
                print(f"    Confidence: {ai_result.get('confidence', 0):.4f}")
                print(f"    Type: {ai_result.get('primary_fraud_type', 'unknown')}")
                print(f"    Signals: {', '.join(ai_result.get('fraud_signals', [])[:3])}")
            else:
                results['failed'] += 1
                error_msg = response_payload.get('body', 'Unknown error')
                results['errors'].append({
                    'event_id': event.get('event_id'),
                    'error': error_msg
                })
                print(f"  ❌ Failed: {error_msg}")
                
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'event_id': event.get('event_id'),
                'error': str(e)
            })
            print(f"  ❌ Error: {str(e)}")
    
    return results


def print_test_results(results: Dict[str, Any]) -> None:
    """Print test results"""
    print("\n" + "=" * 60)
    print("Bedrock AI Analysis Test Results")
    print("=" * 60)
    
    print(f"\nTest Statistics:")
    print(f"  Total tests: {results['total_tests']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Success rate: {results['successful']/results['total_tests']*100:.2f}%")
    
    if results['responses']:
        print(f"\nAI Analysis Results:")
        
        fraud_detected = sum(1 for r in results['responses'] if r.get('is_fraud', False))
        print(f"  Fraud detected: {fraud_detected}/{len(results['responses'])}")
        
        avg_confidence = sum(r.get('confidence', 0) for r in results['responses']) / len(results['responses'])
        print(f"  Average confidence: {avg_confidence:.4f}")
        
        print(f"\n  Fraud Types:")
        fraud_types = {}
        for r in results['responses']:
            fraud_type = r.get('primary_fraud_type', 'unknown')
            fraud_types[fraud_type] = fraud_types.get(fraud_type, 0) + 1
        for fraud_type, count in fraud_types.items():
            print(f"    {fraud_type}: {count}")
        
        print(f"\n  Sample Responses:")
        for r in results['responses'][:3]:
            print(f"\n    Event: {r.get('event_id')}")
            print(f"      Fraud: {r.get('is_fraud')}")
            print(f"      AI Score: {r.get('ai_score', 0):.4f}")
            print(f"      Type: {r.get('primary_fraud_type')}")
            print(f"      Signals: {', '.join(r.get('fraud_signals', [])[:3])}")
            print(f"      Reasoning: {r.get('reasoning', '')[:100]}...")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:5]:
            print(f"  {error.get('event_id')}: {error.get('error')}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Bedrock AI analysis')
    parser.add_argument('--function-name', type=str, default=LAMBDA_FUNCTION_NAME, help='Lambda function name')
    parser.add_argument('--num-tests', type=int, default=5, help='Number of test events')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Bedrock AI Analysis Testing")
    print("=" * 60)
    
    # Create test events
    test_events = []
    for i in range(args.num_tests):
        is_fraud = (i % 3 == 0)  # 33% fraud, 67% legitimate
        ml_score = 0.6 if is_fraud else 0.4  # Borderline scores
        test_events.append(create_test_event(is_fraud=is_fraud, ml_score=ml_score))
    
    print(f"\nCreated {len(test_events)} test events")
    print(f"Fraud events: {sum(1 for e in test_events if e.get('ip_click_count_24h', 0) > 100)}")
    print(f"Legitimate events: {sum(1 for e in test_events if e.get('ip_click_count_24h', 0) <= 100)}")
    
    # Test AI analyzer
    results = test_ai_analyzer_lambda(args.function_name, test_events)
    
    # Print results
    print_test_results(results)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()

