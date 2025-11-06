"""
Test Decision Combiner Logic
Tests the decision combiner Lambda function with various ML and AI score combinations
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'decision_combiner'))


def create_test_event(
    ml_score: float,
    ai_score: float,
    ai_confidence: float = 0.8,
    ai_is_fraud: bool = False
) -> Dict[str, Any]:
    """
    Create a test event for decision combiner
    
    Args:
        ml_score: ML fraud score
        ai_score: AI fraud score
        ai_confidence: AI confidence level
        ai_is_fraud: AI's fraud verdict
        
    Returns:
        Test event dictionary
    """
    return {
        'event_id': f'test-{ml_score:.2f}-{ai_score:.2f}',
        'ml_score': ml_score,
        'ai_result': {
            'ai_score': ai_score,
            'confidence': ai_confidence,
            'is_fraud': ai_is_fraud,
            'fraud_signals': ['test_signal_1', 'test_signal_2'],
            'reasoning': 'Test reasoning for fraud detection',
            'primary_fraud_type': 'bot_traffic' if ai_is_fraud else 'legitimate'
        }
    }


def test_decision_combiner_local(test_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Test decision combiner Lambda function locally
    
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
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = 'fraudguard-decision-combiner'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:fraudguard-decision-combiner'
            self.memory_limit_in_mb = 512
            self.aws_request_id = 'test-request-id'
    
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
            print(f"  AI Score: {event.get('ai_result', {}).get('ai_score', 0.5):.2f}")
            print(f"  AI Confidence: {event.get('ai_result', {}).get('confidence', 0.5):.2f}")
            
            # Invoke Lambda handler
            response = lambda_handler(event, context)
            
            # Parse response
            if response.get('statusCode') == 200:
                result = json.loads(response.get('body', '{}'))
                
                results['successful'] += 1
                results['responses'].append({
                    'event_id': event.get('event_id'),
                    'ml_score': event.get('ml_score'),
                    'ai_score': event.get('ai_result', {}).get('ai_score'),
                    'final_score': result.get('fraud_score'),
                    'is_fraud': result.get('is_fraud'),
                    'action': result.get('recommended_action'),
                    'method': result.get('detection_method'),
                    'ensemble_details': result.get('ensemble_details', {})
                })
                
                print(f"  ✅ Success")
                print(f"    Final Score: {result.get('fraud_score', 0):.4f}")
                print(f"    Fraud: {result.get('is_fraud')}")
                print(f"    Action: {result.get('recommended_action')}")
                print(f"    Method: {result.get('detection_method')}")
                ensemble = result.get('ensemble_details', {})
                if 'ml_weight' in ensemble:
                    print(f"    Weights: ML={ensemble.get('ml_weight', 0):.2f}, AI={ensemble.get('ai_weight', 0):.2f}")
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
    
    return results


def print_test_results(results: Dict[str, Any]) -> None:
    """Print test results"""
    print("\n" + "=" * 60)
    print("Decision Combiner Test Results")
    print("=" * 60)
    
    print(f"\nTest Statistics:")
    print(f"  Total tests: {results['total_tests']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    if results['total_tests'] > 0:
        print(f"  Success rate: {results['successful']/results['total_tests']*100:.2f}%")
    
    if results['responses']:
        print(f"\nDecision Results:")
        
        fraud_detected = sum(1 for r in results['responses'] if r.get('is_fraud', False))
        print(f"  Fraud detected: {fraud_detected}/{len(results['responses'])}")
        
        actions = {}
        methods = {}
        for r in results['responses']:
            action = r.get('action', 'unknown')
            method = r.get('method', 'unknown')
            actions[action] = actions.get(action, 0) + 1
            methods[method] = methods.get(method, 0) + 1
        
        print(f"\n  Actions:")
        for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
            print(f"    {action}: {count}")
        
        print(f"\n  Detection Methods:")
        for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
            print(f"    {method}: {count}")
        
        print(f"\n  Detailed Results:")
        for r in results['responses']:
            print(f"\n    Event: {r.get('event_id')}")
            print(f"      ML: {r.get('ml_score', 0):.4f} | AI: {r.get('ai_score', 0):.4f} | Final: {r.get('final_score', 0):.4f}")
            print(f"      Fraud: {r.get('is_fraud')} | Action: {r.get('action')} | Method: {r.get('method')}")
    
    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:5]:
            print(f"  {error.get('event_id')}: {error.get('error')}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test decision combiner logic')
    parser.add_argument('--output', type=str, help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Decision Combiner Testing")
    print("=" * 60)
    
    # Create test scenarios
    test_events = [
        # Scenario 1: Both agree on fraud
        create_test_event(ml_score=0.75, ai_score=0.85, ai_confidence=0.9, ai_is_fraud=True),
        
        # Scenario 2: Both agree on legitimate
        create_test_event(ml_score=0.25, ai_score=0.15, ai_confidence=0.9, ai_is_fraud=False),
        
        # Scenario 3: ML says fraud, AI says legitimate (high confidence)
        create_test_event(ml_score=0.70, ai_score=0.30, ai_confidence=0.95, ai_is_fraud=False),
        
        # Scenario 4: ML says legitimate, AI says fraud (high confidence)
        create_test_event(ml_score=0.30, ai_score=0.80, ai_confidence=0.95, ai_is_fraud=True),
        
        # Scenario 5: Borderline case - both moderate
        create_test_event(ml_score=0.55, ai_score=0.60, ai_confidence=0.7, ai_is_fraud=True),
        
        # Scenario 6: ML high, AI low confidence
        create_test_event(ml_score=0.80, ai_score=0.50, ai_confidence=0.5, ai_is_fraud=False),
        
        # Scenario 7: ML low, AI high confidence
        create_test_event(ml_score=0.20, ai_score=0.70, ai_confidence=0.9, ai_is_fraud=True),
    ]
    
    print(f"\nCreated {len(test_events)} test scenarios")
    
    # Test decision combiner
    print("\n" + "-" * 60)
    print("Running tests...")
    print("-" * 60)
    results = test_decision_combiner_local(test_events)
    
    # Print results
    print_test_results(results)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to: {args.output}")


if __name__ == '__main__':
    main()

