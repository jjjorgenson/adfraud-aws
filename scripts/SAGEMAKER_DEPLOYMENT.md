# SageMaker Endpoint Deployment Guide

This guide explains how to deploy the trained XGBoost model as a real-time SageMaker endpoint with auto-scaling and monitoring.

## Prerequisites

1. **Trained Model**: Model artifact from SageMaker training job
2. **AWS Account** with SageMaker access
3. **SageMaker Execution Role** with permissions to:
   - Deploy SageMaker endpoints
   - Configure auto-scaling
   - Set up monitoring

## Deployment Options

### Option 1: Python Script (Recommended)

Use the Python script for automated deployment:

```bash
# Install dependencies
pip install -r sagemaker_training_requirements.txt

# Deploy endpoint
python deploy_sagemaker_endpoint.py \
  --model-artifact s3://fraudguard-data/training-data/models/fraudguard-xgboost-*/output/model.tar.gz \
  --endpoint-name fraudguard-xgboost-endpoint \
  --instance-type ml.t2.medium \
  --initial-instance-count 1 \
  --min-capacity 1 \
  --max-capacity 5 \
  --target-utilization 70 \
  --test
```

### Option 2: SageMaker SDK (Python)

Deploy using SageMaker SDK:

```python
import sagemaker
from sagemaker.model import Model
from sagemaker.amazon.amazon_estimator import get_image_uri

# Initialize
sagemaker_session = sagemaker.Session()
role = sagemaker.get_execution_role()
region = sagemaker_session.boto_region_name

# Get container
container = get_image_uri(region, 'xgboost', '1.5-1')

# Create model
model = Model(
    image_uri=container,
    model_data='s3://fraudguard-data/training-data/models/model.tar.gz',
    role=role,
    sagemaker_session=sagemaker_session
)

# Deploy
predictor = model.deploy(
    initial_instance_count=1,
    instance_type='ml.t2.medium',
    endpoint_name='fraudguard-xgboost-endpoint'
)
```

### Option 3: AWS CLI

Deploy using AWS CLI:

```bash
# Create model
aws sagemaker create-model \
  --model-name fraudguard-xgboost-model \
  --execution-role-arn arn:aws:iam::ACCOUNT_ID:role/SageMakerExecutionRole \
  --primary-container Image=811284229777.dkr.ecr.us-east-1.amazonaws.com/xgboost:latest,ModelDataUrl=s3://fraudguard-data/models/model.tar.gz

# Create endpoint configuration
aws sagemaker create-endpoint-config \
  --endpoint-config-name fraudguard-xgboost-config \
  --production-variants VariantName=AllTraffic,ModelName=fraudguard-xgboost-model,InitialInstanceCount=1,InstanceType=ml.t2.medium

# Create endpoint
aws sagemaker create-endpoint \
  --endpoint-name fraudguard-xgboost-endpoint \
  --endpoint-config-name fraudguard-xgboost-config
```

## Auto-Scaling Configuration

Configure auto-scaling to handle variable traffic:

```python
import boto3

application_autoscaling = boto3.client('application-autoscaling', region_name='us-east-1')

# Register scalable target
resource_id = "endpoint/fraudguard-xgboost-endpoint/variant/AllTraffic"

application_autoscaling.register_scalable_target(
    ServiceNamespace='sagemaker',
    ResourceId=resource_id,
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    MinCapacity=1,
    MaxCapacity=5
)

# Create scaling policy
application_autoscaling.put_scaling_policy(
    ServiceNamespace='sagemaker',
    ResourceId=resource_id,
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    PolicyName='fraudguard-scaling-policy',
    PolicyType='TargetTrackingScaling',
    TargetTrackingScalingPolicyConfiguration={
        'TargetValue': 70.0,  # Target 70% CPU utilization
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
        },
        'ScaleInCooldown': 300,  # 5 minutes
        'ScaleOutCooldown': 60,  # 1 minute
    }
)
```

## Monitoring Setup

### Data Capture

Enable data capture for model monitoring:

```python
from sagemaker.model_monitor import DataCaptureConfig

data_capture_config = DataCaptureConfig(
    enable_capture=True,
    sampling_percentage=100,
    destination_s3_uri='s3://fraudguard-data/monitoring/data-capture/',
    capture_options=['REQUEST', 'RESPONSE']
)
```

### Model Monitor

Set up model monitoring:

```python
from sagemaker.model_monitor import DefaultModelMonitor

model_monitor = DefaultModelMonitor(
    role=role,
    instance_count=1,
    instance_type='ml.t3.medium',
    volume_size_in_gb=20,
    max_runtime_in_seconds=3600
)

# Create monitoring schedule
model_monitor.create_monitoring_schedule(
    monitoring_schedule_name='fraudguard-monitoring',
    endpoint_input='fraudguard-xgboost-endpoint',
    output_s3_uri='s3://fraudguard-data/monitoring/output/',
    schedule_cron_expression='cron(0 * * * ? *)'  # Every hour
)
```

## Testing Endpoint

Test the deployed endpoint:

```bash
# Test endpoint
python test_sagemaker_endpoint.py \
  --endpoint-name fraudguard-xgboost-endpoint \
  --num-samples 100 \
  --num-iterations 1 \
  --output test_results.json
```

Or test programmatically:

```python
from sagemaker.predictor import Predictor
import numpy as np

predictor = Predictor(endpoint_name='fraudguard-xgboost-endpoint')

# Create sample features (20 features)
features = [[0.0] * 20]  # Replace with actual features

# Make prediction
prediction = predictor.predict(features)
print(f"Fraud score: {prediction[0]:.4f}")
```

## Instance Types

- **Development**: `ml.t2.medium` (~$0.05/hour)
- **Production**: `ml.m5.large` (~$0.13/hour)
- **High Performance**: `ml.m5.xlarge` (~$0.23/hour)

## Performance Requirements

From PRD:
- **Latency**: <100ms @ p95 (ML path)
- **Availability**: 99%
- **Throughput**: 1000 req/sec sustained

## Cost Estimation

Endpoint costs (approximate):
- `ml.t2.medium`: ~$0.05/hour = ~$36/month
- `ml.m5.large`: ~$0.13/hour = ~$94/month
- `ml.m5.xlarge`: ~$0.23/hour = ~$166/month

With auto-scaling (1-5 instances):
- Average: 2 instances
- Monthly cost: ~$72 - $332 (depending on instance type)

## Troubleshooting

### Common Issues

1. **Endpoint Creation Fails**: Check IAM permissions and model artifact path
2. **High Latency**: Use larger instance type or optimize model
3. **Auto-Scaling Not Working**: Verify IAM permissions for Application Auto Scaling
4. **Monitoring Not Working**: Check S3 bucket permissions and IAM role

### Monitoring

Monitor endpoint:
- SageMaker Console → Endpoints
- CloudWatch Metrics → `/aws/sagemaker/Endpoints`
- CloudWatch Logs → `/aws/sagemaker/Endpoints`

Key metrics:
- `Invocations`: Number of requests
- `ModelLatency`: Prediction latency
- `Invocation4XXErrors`: Client errors
- `Invocation5XXErrors`: Server errors

## Next Steps

After deployment:
1. Test endpoint with sample requests
2. Update Lambda functions to use endpoint
3. Set up CloudWatch alarms
4. Monitor endpoint performance
5. Configure auto-scaling based on traffic patterns

