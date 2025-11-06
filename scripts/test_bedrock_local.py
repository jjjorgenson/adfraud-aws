"""
Test Bedrock AI Analysis Locally
Tests the AI analyzer Lambda function code directly without deploying to AWS
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'ai_analyzer'))

# Mock Lambda context
class MockContext:
    def __init__(self):
        self.function_name = 'fraudguard-ai-analyzer'
        self.function_version = '$LATEST'
        self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:fraudguard-ai-analyzer'
        self.memory_limit_in_mb = 1024
        self.aws_request_id = 'test-request-id'
        self.log_group_name = '/aws/lambda/fraudguard-ai-analyzer'
        self.log_stream_name = 'test-stream'


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
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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


def test_ai_analyzer_local(test_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Test AI analyzer Lambda function locally
    
    Args:
        test_events: List of test events
        
    Returns:
        Test results dictionary
    """
    # Import Lambda handler
    try:
        from app import lambda_handler
    except ImportError as e:
        print(f"❌ Error importing Lambda handler: {e}")
        print("Make sure you're running from the project root directory")
        sys.exit(1)
    
    context = MockContext()
    
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
            print(f"  User Agent: {event.get('user_agent', '')[:60]}...")
            
            # Invoke Lambda handler
            response = lambda_handler(event, context)
            
            # Parse response
            if response.get('statusCode') == 200:
                ai_result = json.loads(response.get('body', '{}'))
                
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
                signals = ai_result.get('fraud_signals', [])
                if signals:
                    print(f"    Signals: {', '.join(signals[:3])}")
                if ai_result.get('reasoning'):
                    print(f"    Reasoning: {ai_result.get('reasoning', '')[:100]}...")
            else:
                results['failed'] += 1
                error_msg = response.get('body', 'Unknown error')
                results['errors'].append({
                    'event_id': event.get('event_id'),
                    'error': error_msg
                })
                print(f"  ❌ Failed: {error_msg}")
                
        except Exception as e:
            results['failed'] += 1
            import traceback
            error_trace = traceback.format_exc()
            results['errors'].append({
                'event_id': event.get('event_id'),
                'error': str(e),
                'traceback': error_trace
            })
            print(f"  ❌ Error: {str(e)}")
            print(f"  Traceback: {error_trace[:200]}...")
    
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
    if results['total_tests'] > 0:
        print(f"  Success rate: {results['successful']/results['total_tests']*100:.2f}%")
    
    if results['responses']:
        print(f"\nAI Analysis Results:")
        
        fraud_detected = sum(1 for r in results['responses'] if r.get('is_fraud', False))
        print(f"  Fraud detected: {fraud_detected}/{len(results['responses'])}")
        
        if len(results['responses']) > 0:
            avg_confidence = sum(r.get('confidence', 0) for r in results['responses']) / len(results['responses'])
            avg_ai_score = sum(r.get('ai_score', 0) for r in results['responses']) / len(results['responses'])
            print(f"  Average confidence: {avg_confidence:.4f}")
            print(f"  Average AI score: {avg_ai_score:.4f}")
        
        print(f"\n  Fraud Types:")
        fraud_types = {}
        for r in results['responses']:
            fraud_type = r.get('primary_fraud_type', 'unknown')
            fraud_types[fraud_type] = fraud_types.get(fraud_type, 0) + 1
        for fraud_type, count in sorted(fraud_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    {fraud_type}: {count}")
        
        print(f"\n  Detailed Responses:")
        for r in results['responses']:
            print(f"\n    Event: {r.get('event_id')}")
            print(f"      Fraud: {r.get('is_fraud')}")
            print(f"      AI Score: {r.get('ai_score', 0):.4f}")
            print(f"      Confidence: {r.get('confidence', 0):.4f}")
            print(f"      Type: {r.get('primary_fraud_type')}")
            signals = r.get('fraud_signals', [])
            if signals:
                print(f"      Signals: {', '.join(signals)}")
            reasoning = r.get('reasoning', '')
            if reasoning:
                print(f"      Reasoning: {reasoning}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:5]:
            print(f"  {error.get('event_id')}: {error.get('error')}")
            if 'traceback' in error:
                print(f"    {error.get('traceback', '')[:200]}...")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Bedrock AI analysis locally')
    parser.add_argument('--num-tests', type=int, default=3, help='Number of test events')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    parser.add_argument('--event-file', type=str, help='JSON file with test event(s)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Bedrock AI Analysis Local Testing")
    print("=" * 60)
    print("\n⚠️  Note: This requires AWS credentials and Bedrock model access")
    print("   Make sure BEDROCK_MODEL_ID is set or uses default")
    print("   Check IAM permissions for bedrock:InvokeModel")
    
    # Load test events
    if args.event_file:
        with open(args.event_file, 'r') as f:
            events_data = json.load(f)
            if isinstance(events_data, list):
                test_events = events_data
            else:
                test_events = [events_data]
        print(f"\nLoaded {len(test_events)} test event(s) from {args.event_file}")
    else:
        # Create test events
        test_events = []
        for i in range(args.num_tests):
            is_fraud = (i % 3 == 0)  # 33% fraud, 67% legitimate
            ml_score = 0.6 if is_fraud else 0.4  # Borderline scores
            test_events.append(create_test_event(is_fraud=is_fraud, ml_score=ml_score))
        
        print(f"\nCreated {len(test_events)} test events")
        fraud_count = sum(1 for e in test_events if e.get('ip_click_count_24h', 0) > 100)
        legit_count = len(test_events) - fraud_count
        print(f"  Fraud events: {fraud_count}")
        print(f"  Legitimate events: {legit_count}")
    
    # Test AI analyzer
    print("\n" + "-" * 60)
    print("Running tests...")
    print("-" * 60)
    results = test_ai_analyzer_local(test_events)
    
    # Print results
    print_test_results(results)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to: {args.output}")


if __name__ == '__main__':
    main()

