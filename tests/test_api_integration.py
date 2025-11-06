"""
Integration Tests for API and ML Model
Tests end-to-end fraud detection flow
"""
import json
import requests
import time
from typing import Dict, Any


def create_test_event(is_fraud: bool = False) -> Dict[str, Any]:
    """
    Create a test ad event
    
    Args:
        is_fraud: Whether to create a fraudulent event
        
    Returns:
        Event dictionary
    """
    if is_fraud:
        # Fraudulent event characteristics
        return {
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
            'device_os': 'Windows'
        }
    else:
        # Legitimate event characteristics
        return {
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
            'device_os': 'Windows'
        }


def test_api_endpoint(api_url: str, api_key: str, test_events: list) -> Dict[str, Any]:
    """
    Test API endpoint with multiple events
    
    Args:
        api_url: API Gateway endpoint URL
        api_key: API key for authentication
        test_events: List of test events
        
    Returns:
        Test results dictionary
    """
    results = {
        'total_requests': len(test_events),
        'successful_requests': 0,
        'failed_requests': 0,
        'latencies': [],
        'predictions': [],
        'errors': []
    }
    
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }
    
    for i, event in enumerate(test_events):
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{api_url}/v1/detect-fraud",
                headers=headers,
                json=event,
                timeout=10
            )
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                result = response.json()
                results['successful_requests'] += 1
                results['latencies'].append(latency)
                results['predictions'].append(result)
                
                print(f"Event {i+1}: Status={response.status_code}, "
                      f"Fraud={result.get('is_fraud')}, "
                      f"Score={result.get('fraud_score', 0):.4f}, "
                      f"Latency={latency:.2f}ms")
            else:
                results['failed_requests'] += 1
                results['errors'].append({
                    'event': i+1,
                    'status_code': response.status_code,
                    'error': response.text
                })
                print(f"Event {i+1}: Failed with status {response.status_code}")
                
        except Exception as e:
            results['failed_requests'] += 1
            results['errors'].append({
                'event': i+1,
                'error': str(e)
            })
            print(f"Event {i+1}: Error - {str(e)}")
    
    # Calculate statistics
    if results['latencies']:
        results['avg_latency'] = sum(results['latencies']) / len(results['latencies'])
        results['min_latency'] = min(results['latencies'])
        results['max_latency'] = max(results['latencies'])
        results['p95_latency'] = sorted(results['latencies'])[int(len(results['latencies']) * 0.95)]
    
    return results


def print_test_results(results: Dict[str, Any]) -> None:
    """Print test results"""
    print("\n" + "=" * 60)
    print("API Integration Test Results")
    print("=" * 60)
    
    print(f"\nRequest Statistics:")
    print(f"  Total requests: {results['total_requests']}")
    print(f"  Successful: {results['successful_requests']}")
    print(f"  Failed: {results['failed_requests']}")
    print(f"  Success rate: {results['successful_requests']/results['total_requests']*100:.2f}%")
    
    if results['latencies']:
        print(f"\nLatency Statistics (ms):")
        print(f"  Average: {results['avg_latency']:.2f}")
        print(f"  Min: {results['min_latency']:.2f}")
        print(f"  Max: {results['max_latency']:.2f}")
        print(f"  P95: {results['p95_latency']:.2f}")
        
        # Check latency requirements
        target_latency = 100  # ms (from PRD)
        if results['p95_latency'] <= target_latency:
            print(f"\n✅ P95 latency ({results['p95_latency']:.2f}ms) meets requirement ({target_latency}ms)")
        else:
            print(f"\n⚠️  P95 latency ({results['p95_latency']:.2f}ms) exceeds requirement ({target_latency}ms)")
    
    # Analyze predictions
    if results['predictions']:
        fraud_count = sum(1 for p in results['predictions'] if p.get('is_fraud', False))
        print(f"\nPrediction Statistics:")
        print(f"  Fraud detected: {fraud_count}/{len(results['predictions'])}")
        print(f"  Detection methods:")
        methods = {}
        for p in results['predictions']:
            method = p.get('detection_method', 'unknown')
            methods[method] = methods.get(method, 0) + 1
        for method, count in methods.items():
            print(f"    {method}: {count}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test API integration with ML model')
    parser.add_argument('--api-url', type=str, required=True, help='API Gateway endpoint URL')
    parser.add_argument('--api-key', type=str, required=True, help='API key for authentication')
    parser.add_argument('--num-tests', type=int, default=10, help='Number of test events')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("API Integration Testing")
    print("=" * 60)
    
    # Create test events (mix of fraud and legitimate)
    test_events = []
    for i in range(args.num_tests):
        is_fraud = (i % 3 == 0)  # 33% fraud, 67% legitimate
        test_events.append(create_test_event(is_fraud=is_fraud))
    
    print(f"\nCreated {len(test_events)} test events")
    print(f"Fraud events: {sum(1 for e in test_events if e.get('ip_click_count_24h', 0) > 100)}")
    print(f"Legitimate events: {sum(1 for e in test_events if e.get('ip_click_count_24h', 0) <= 100)}")
    
    # Test API endpoint
    results = test_api_endpoint(args.api_url, args.api_key, test_events)
    
    # Print results
    print_test_results(results)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()

