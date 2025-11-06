"""
Test Dashboard Functionality
Validates that the dashboard can be imported and basic functions work
"""
import sys
import os

# Add dashboard directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        import streamlit as st
        print("✅ streamlit imported")
    except ImportError as e:
        print(f"❌ streamlit import failed: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ pandas imported")
    except ImportError as e:
        print(f"❌ pandas import failed: {e}")
        return False
    
    try:
        import plotly.express as px
        print("✅ plotly imported")
    except ImportError as e:
        print(f"❌ plotly import failed: {e}")
        return False
    
    try:
        import boto3
        print("✅ boto3 imported")
    except ImportError as e:
        print(f"❌ boto3 import failed: {e}")
        return False
    
    return True

def test_dashboard_functions():
    """Test dashboard functions"""
    print("\nTesting dashboard functions...")
    try:
        # Import dashboard functions
        from app import get_mock_events, calculate_metrics
        
        # Test mock events generation
        print("Testing mock events generation...")
        events = get_mock_events(hours=24)
        print(f"✅ Generated {len(events)} mock events")
        
        # Test metrics calculation
        print("Testing metrics calculation...")
        metrics = calculate_metrics(events)
        print(f"✅ Calculated metrics:")
        print(f"   Total events: {metrics['total_events']}")
        print(f"   Fraud count: {metrics['fraud_count']}")
        print(f"   Fraud rate: {metrics['fraud_rate']:.2f}%")
        print(f"   Fraud types: {len(metrics['fraud_by_type'])}")
        print(f"   Top signals: {len(metrics['top_signals'])}")
        
        return True
    except Exception as e:
        print(f"❌ Dashboard function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_structures():
    """Test data structure handling"""
    print("\nTesting data structures...")
    try:
        import pandas as pd
        from app import calculate_metrics
        
        # Test with empty data
        metrics = calculate_metrics([])
        assert metrics['total_events'] == 0
        print("✅ Empty data handling works")
        
        # Test with sample data
        sample_events = [
            {
                'event_id': 'test-1',
                'timestamp': 1704067200,
                'is_fraud': True,
                'fraud_score': 0.85,
                'campaign_id': 'campaign-1',
                'ip_country': 'US',
                'primary_fraud_type': 'bot_traffic',
                'fraud_signals': ['bot_user_agent', 'high_click_velocity']
            },
            {
                'event_id': 'test-2',
                'timestamp': 1704067300,
                'is_fraud': False,
                'fraud_score': 0.25,
                'campaign_id': 'campaign-1',
                'ip_country': 'US',
                'primary_fraud_type': 'legitimate',
                'fraud_signals': []
            }
        ]
        
        metrics = calculate_metrics(sample_events)
        assert metrics['total_events'] == 2
        assert metrics['fraud_count'] == 1
        assert metrics['fraud_rate'] == 50.0
        print("✅ Sample data handling works")
        
        return True
    except Exception as e:
        print(f"❌ Data structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Dashboard Functionality Test")
    print("=" * 60)
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    # Test dashboard functions
    if results[-1][1]:
        results.append(("Dashboard Functions", test_dashboard_functions()))
        results.append(("Data Structures", test_data_structures()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✅ All tests passed! Dashboard is ready to run.")
        print("\nTo start the dashboard, run:")
        print("  cd dashboard")
        print("  streamlit run app.py")
        print("\nThen open http://localhost:8501 in your browser")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

