"""
Test SageMaker Endpoint
Tests the deployed SageMaker endpoint with sample requests
"""
import boto3
import json
import time
import numpy as np
from typing import List, Dict, Any
from sagemaker.predictor import Predictor

# Configuration
ENDPOINT_NAME = 'fraudguard-xgboost-endpoint'
REGION = 'us-east-1'


def create_sample_features(num_samples: int = 10) -> List[List[float]]:
    """
    Create sample feature vectors for testing
    
    Args:
        num_samples: Number of samples to create
        
    Returns:
        List of feature vectors
    """
    # 20 features as per PRD
    features = []
    
    for i in range(num_samples):
        # Create realistic feature values
        sample = [
            float(np.random.randint(0, 100)),  # ip_click_count_24h
            float(np.random.randint(0, 10)),   # device_click_count_1h
            float(np.random.uniform(0, 3600)), # time_since_last_click
            float(np.random.randint(0, 24)),   # hour_of_day
            float(np.random.randint(0, 7)),    # day_of_week
            float(np.random.choice([0, 1])),   # ua_is_bot
            float(np.random.uniform(0, 1)),    # ua_entropy
            float(np.random.choice([0, 1])),   # ip_is_datacenter
            float(np.random.choice([0, 1])),   # ip_is_vpn
            float(np.random.uniform(0, 1000)), # geo_distance_km
            float(np.random.choice([0, 1])),   # referrer_is_valid
            float(np.random.randint(100, 10000)), # click_to_view_time_ms
            float(np.random.uniform(0, 1)),    # campaign_fraud_rate
            float(np.random.uniform(0, 1)),    # publisher_quality
            float(np.random.uniform(0, 1)),    # device_fingerprint_entropy
            float(np.random.choice([0, 1])),   # is_mobile
            float(np.random.choice([0, 1])),   # is_repeated_click
            float(np.random.uniform(0, 3600)) if np.random.random() > 0.5 else 0.0,  # time_to_conversion_sec
            float(np.random.randint(0, 10)),   # ip_country (encoded)
            float(np.random.randint(0, 5)),    # device_os (encoded)
        ]
        features.append(sample)
    
    return features


def test_endpoint(
    endpoint_name: str,
    test_features: List[List[float]],
    num_iterations: int = 1
) -> Dict[str, Any]:
    """
    Test SageMaker endpoint
    
    Args:
        endpoint_name: Endpoint name
        test_features: List of feature vectors
        num_iterations: Number of test iterations
        
    Returns:
        Test results dictionary
    """
    print(f"Testing endpoint: {endpoint_name}")
    print(f"Number of samples: {len(test_features)}")
    print(f"Number of iterations: {num_iterations}")
    
    predictor = Predictor(endpoint_name=endpoint_name)
    
    results = {
        'predictions': [],
        'latencies': [],
        'errors': [],
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0
    }
    
    for iteration in range(num_iterations):
        print(f"\nIteration {iteration + 1}/{num_iterations}")
        
        for i, features in enumerate(test_features):
            try:
                start_time = time.time()
                
                # Make prediction
                prediction = predictor.predict(features)
                
                latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                results['predictions'].append(float(prediction[0]))
                results['latencies'].append(latency)
                results['total_requests'] += 1
                results['successful_requests'] += 1
                
                if (i + 1) % 10 == 0:
                    print(f"  Processed {i + 1}/{len(test_features)} samples")
                    
            except Exception as e:
                results['errors'].append({
                    'sample': i,
                    'error': str(e)
                })
                results['total_requests'] += 1
                results['failed_requests'] += 1
                print(f"  Error on sample {i + 1}: {str(e)}")
    
    # Calculate statistics
    if results['latencies']:
        results['avg_latency'] = sum(results['latencies']) / len(results['latencies'])
        results['min_latency'] = min(results['latencies'])
        results['max_latency'] = max(results['latencies'])
        results['p50_latency'] = np.percentile(results['latencies'], 50)
        results['p95_latency'] = np.percentile(results['latencies'], 95)
        results['p99_latency'] = np.percentile(results['latencies'], 99)
        
        results['avg_prediction'] = sum(results['predictions']) / len(results['predictions'])
        results['min_prediction'] = min(results['predictions'])
        results['max_prediction'] = max(results['predictions'])
    
    return results


def print_results(results: Dict[str, Any]) -> None:
    """Print test results"""
    print("\n" + "=" * 60)
    print("Test Results")
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
        print(f"  P50: {results['p50_latency']:.2f}")
        print(f"  P95: {results['p95_latency']:.2f}")
        print(f"  P99: {results['p99_latency']:.2f}")
        
        print(f"\nPrediction Statistics:")
        print(f"  Average: {results['avg_prediction']:.4f}")
        print(f"  Min: {results['min_prediction']:.4f}")
        print(f"  Max: {results['max_prediction']:.4f}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:5]:  # Show first 5 errors
            print(f"  Sample {error['sample']}: {error['error']}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test SageMaker endpoint')
    parser.add_argument('--endpoint-name', type=str, default=ENDPOINT_NAME, help='Endpoint name')
    parser.add_argument('--num-samples', type=int, default=100, help='Number of test samples')
    parser.add_argument('--num-iterations', type=int, default=1, help='Number of test iterations')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SageMaker Endpoint Testing")
    print("=" * 60)
    
    # Create sample features
    test_features = create_sample_features(args.num_samples)
    
    # Test endpoint
    results = test_endpoint(
        args.endpoint_name,
        test_features,
        args.num_iterations
    )
    
    # Print results
    print_results(results)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Check if latency meets requirements
    if results.get('p95_latency'):
        target_latency = 100  # ms (from PRD)
        if results['p95_latency'] <= target_latency:
            print(f"\n✅ P95 latency ({results['p95_latency']:.2f}ms) meets requirement ({target_latency}ms)")
        else:
            print(f"\n⚠️  P95 latency ({results['p95_latency']:.2f}ms) exceeds requirement ({target_latency}ms)")


if __name__ == '__main__':
    main()

