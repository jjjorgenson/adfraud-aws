"""
Deploy SageMaker Endpoint
Deploys trained XGBoost model as a real-time endpoint with auto-scaling and monitoring
"""
import boto3
import sagemaker
from sagemaker import get_execution_role
from sagemaker.predictor import Predictor
from sagemaker.model import Model
from sagemaker.model_monitor import ModelMonitor, DefaultModelMonitor
from sagemaker.model_monitor import DataCaptureConfig
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize SageMaker session
sagemaker_session = sagemaker.Session()
role = get_execution_role()
region = sagemaker_session.boto_region_name

# Configuration
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME', 'fraudguard-xgboost-endpoint')
INSTANCE_TYPE = os.environ.get('INSTANCE_TYPE', 'ml.t2.medium')  # Use ml.m5.large for production
INITIAL_INSTANCE_COUNT = int(os.environ.get('INITIAL_INSTANCE_COUNT', '1'))
MIN_CAPACITY = int(os.environ.get('MIN_CAPACITY', '1'))
MAX_CAPACITY = int(os.environ.get('MAX_CAPACITY', '5'))
TARGET_UTILIZATION = int(os.environ.get('TARGET_UTILIZATION', '70'))


def deploy_endpoint(
    model_artifact: str,
    endpoint_name: str,
    instance_type: str,
    initial_instance_count: int = 1
) -> Predictor:
    """
    Deploy model to SageMaker endpoint
    
    Args:
        model_artifact: S3 path to model artifact
        endpoint_name: Name for the endpoint
        instance_type: SageMaker instance type
        initial_instance_count: Initial number of instances
        
    Returns:
        SageMaker predictor
    """
    print(f"Deploying model to endpoint: {endpoint_name}")
    print(f"Model artifact: {model_artifact}")
    print(f"Instance type: {instance_type}")
    print(f"Initial instance count: {initial_instance_count}")
    
    # Get XGBoost container image
    from sagemaker.amazon.amazon_estimator import get_image_uri
    container = get_image_uri(region, 'xgboost', '1.5-1')
    
    # Create model
    model = Model(
        image_uri=container,
        model_data=model_artifact,
        role=role,
        sagemaker_session=sagemaker_session
    )
    
    # Deploy model
    predictor = model.deploy(
        initial_instance_count=initial_instance_count,
        instance_type=instance_type,
        endpoint_name=endpoint_name,
        wait=True
    )
    
    print(f"Endpoint deployed: {endpoint_name}")
    print(f"Endpoint ARN: {predictor.endpoint_name}")
    
    return predictor


def configure_auto_scaling(
    endpoint_name: str,
    min_capacity: int,
    max_capacity: int,
    target_utilization: int = 70
) -> None:
    """
    Configure auto-scaling for SageMaker endpoint
    
    Args:
        endpoint_name: Endpoint name
        min_capacity: Minimum number of instances
        max_capacity: Maximum number of instances
        target_utilization: Target CPU utilization percentage
    """
    print(f"Configuring auto-scaling for endpoint: {endpoint_name}")
    print(f"Min capacity: {min_capacity}")
    print(f"Max capacity: {max_capacity}")
    print(f"Target utilization: {target_utilization}%")
    
    application_autoscaling = boto3.client('application-autoscaling', region_name=region)
    sagemaker_client = boto3.client('sagemaker', region_name=region)
    
    # Get endpoint variant name
    endpoint_config = sagemaker_client.describe_endpoint_config(
        EndpointConfigName=sagemaker_client.describe_endpoint(EndpointName=endpoint_name)['EndpointConfigName']
    )
    variant_name = endpoint_config['ProductionVariants'][0]['VariantName']
    
    # Register scalable target
    resource_id = f"endpoint/{endpoint_name}/variant/{variant_name}"
    
    try:
        application_autoscaling.register_scalable_target(
            ServiceNamespace='sagemaker',
            ResourceId=resource_id,
            ScalableDimension='sagemaker:variant:DesiredInstanceCount',
            MinCapacity=min_capacity,
            MaxCapacity=max_capacity
        )
        print(f"Scalable target registered: {resource_id}")
    except application_autoscaling.exceptions.ResourceInUseException:
        print(f"Scalable target already exists: {resource_id}")
    
    # Create scaling policy
    policy_name = f"{endpoint_name}-scaling-policy"
    
    try:
        application_autoscaling.put_scaling_policy(
            ServiceNamespace='sagemaker',
            ResourceId=resource_id,
            ScalableDimension='sagemaker:variant:DesiredInstanceCount',
            PolicyName=policy_name,
            PolicyType='TargetTrackingScaling',
            TargetTrackingScalingPolicyConfiguration={
                'TargetValue': target_utilization,
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
                },
                'ScaleInCooldown': 300,  # 5 minutes
                'ScaleOutCooldown': 60,  # 1 minute
            }
        )
        print(f"Scaling policy created: {policy_name}")
    except Exception as e:
        print(f"Error creating scaling policy: {str(e)}")
        print("You may need to create the scaling policy manually in the AWS Console")


def setup_data_capture(
    endpoint_name: str,
    s3_capture_path: str,
    capture_percentage: int = 100
) -> None:
    """
    Set up data capture for model monitoring
    
    Args:
        endpoint_name: Endpoint name
        s3_capture_path: S3 path for captured data
        capture_percentage: Percentage of requests to capture
    """
    print(f"Setting up data capture for endpoint: {endpoint_name}")
    print(f"Capture path: {s3_capture_path}")
    print(f"Capture percentage: {capture_percentage}%")
    
    data_capture_config = DataCaptureConfig(
        enable_capture=True,
        sampling_percentage=capture_percentage,
        destination_s3_uri=s3_capture_path,
        capture_options=['REQUEST', 'RESPONSE']
    )
    
    # Note: Data capture needs to be configured when creating the endpoint
    # This is a placeholder for documentation
    print("Note: Data capture should be configured during endpoint creation")
    print("For existing endpoints, update the endpoint configuration")


def setup_monitoring(
    endpoint_name: str,
    baseline_data_path: str,
    output_s3_uri: str
) -> None:
    """
    Set up model monitoring
    
    Args:
        endpoint_name: Endpoint name
        baseline_data_path: S3 path to baseline data
        output_s3_uri: S3 path for monitoring output
    """
    print(f"Setting up model monitoring for endpoint: {endpoint_name}")
    
    # Create model monitor
    model_monitor = DefaultModelMonitor(
        role=role,
        instance_count=1,
        instance_type='ml.t3.medium',
        volume_size_in_gb=20,
        max_runtime_in_seconds=3600,
        sagemaker_session=sagemaker_session
    )
    
    # Schedule monitoring
    monitoring_schedule_name = f"{endpoint_name}-monitoring"
    
    try:
        model_monitor.create_monitoring_schedule(
            monitoring_schedule_name=monitoring_schedule_name,
            endpoint_input=endpoint_name,
            output_s3_uri=output_s3_uri,
            statistics=model_monitor.baseline_statistics(),
            constraints=model_monitor.suggested_constraints(),
            schedule_cron_expression='cron(0 * * * ? *)'  # Every hour
        )
        print(f"Monitoring schedule created: {monitoring_schedule_name}")
    except Exception as e:
        print(f"Error creating monitoring schedule: {str(e)}")
        print("You may need to create the monitoring schedule manually")


def test_endpoint(
    predictor: Predictor,
    test_features: list
) -> Dict[str, Any]:
    """
    Test endpoint with sample features
    
    Args:
        predictor: SageMaker predictor
        test_features: List of feature vectors
        
    Returns:
        Test results dictionary
    """
    print(f"Testing endpoint: {predictor.endpoint_name}")
    
    import time
    
    results = {
        'predictions': [],
        'latencies': [],
        'errors': []
    }
    
    for i, features in enumerate(test_features):
        try:
            start_time = time.time()
            prediction = predictor.predict(features)
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            results['predictions'].append(prediction)
            results['latencies'].append(latency)
            
            print(f"Sample {i+1}: Prediction={prediction[0]:.4f}, Latency={latency:.2f}ms")
        except Exception as e:
            results['errors'].append(str(e))
            print(f"Error on sample {i+1}: {str(e)}")
    
    if results['latencies']:
        avg_latency = sum(results['latencies']) / len(results['latencies'])
        p95_latency = sorted(results['latencies'])[int(len(results['latencies']) * 0.95)]
        
        print(f"\nTest Results:")
        print(f"Total requests: {len(test_features)}")
        print(f"Successful: {len(results['predictions'])}")
        print(f"Errors: {len(results['errors'])}")
        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"P95 latency: {p95_latency:.2f}ms")
        
        results['avg_latency'] = avg_latency
        results['p95_latency'] = p95_latency
    
    return results


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy SageMaker endpoint')
    parser.add_argument('--model-artifact', type=str, required=True, help='S3 path to model artifact')
    parser.add_argument('--endpoint-name', type=str, default=ENDPOINT_NAME, help='Endpoint name')
    parser.add_argument('--instance-type', type=str, default=INSTANCE_TYPE, help='Instance type')
    parser.add_argument('--initial-instance-count', type=int, default=INITIAL_INSTANCE_COUNT, help='Initial instance count')
    parser.add_argument('--min-capacity', type=int, default=MIN_CAPACITY, help='Min capacity for auto-scaling')
    parser.add_argument('--max-capacity', type=int, default=MAX_CAPACITY, help='Max capacity for auto-scaling')
    parser.add_argument('--target-utilization', type=int, default=TARGET_UTILIZATION, help='Target CPU utilization')
    parser.add_argument('--no-auto-scaling', action='store_true', help='Skip auto-scaling configuration')
    parser.add_argument('--test', action='store_true', help='Test endpoint after deployment')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SageMaker Endpoint Deployment")
    print("=" * 60)
    
    # Deploy endpoint
    predictor = deploy_endpoint(
        args.model_artifact,
        args.endpoint_name,
        args.instance_type,
        args.initial_instance_count
    )
    
    # Configure auto-scaling
    if not args.no_auto_scaling:
        configure_auto_scaling(
            args.endpoint_name,
            args.min_capacity,
            args.max_capacity,
            args.target_utilization
        )
    
    # Test endpoint
    if args.test:
        # Create sample test features (20 features as per PRD)
        sample_features = [[0.0] * 20]  # Placeholder - replace with actual features
        test_endpoint(predictor, sample_features)
    
    print("\n" + "=" * 60)
    print("Deployment Complete!")
    print("=" * 60)
    print(f"Endpoint name: {args.endpoint_name}")
    print(f"Endpoint ARN: {predictor.endpoint_name}")
    print(f"\nTo test the endpoint:")
    print(f"  predictor = Predictor(endpoint_name='{args.endpoint_name}')")
    print(f"  prediction = predictor.predict(features)")


if __name__ == '__main__':
    main()

