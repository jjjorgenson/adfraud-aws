# SageMaker XGBoost Training Guide

This guide explains how to train the XGBoost fraud detection model on AWS SageMaker.

## Prerequisites

1. **AWS Account** with SageMaker access
2. **AWS CLI** configured with appropriate credentials
3. **SageMaker Execution Role** with permissions to:
   - Access S3 buckets
   - Create SageMaker training jobs
   - Deploy SageMaker endpoints
4. **Dataset** generated using `generate_dataset.py`

## Training Options

### Option 1: Python Script (Recommended)

Use the Python script for automated training:

```bash
# Install dependencies
pip install -r sagemaker_training_requirements.txt

# Generate dataset first
python generate_dataset.py

# Train model
python train_xgboost_sagemaker.py \
  --train-data data/train.csv \
  --val-data data/val.csv \
  --test-data data/test.csv \
  --s3-bucket fraudguard-data \
  --s3-prefix training-data \
  --instance-type ml.m5.xlarge
```

### Option 2: SageMaker Notebook

Use the Jupyter notebook for interactive training:

1. Open SageMaker Studio or create a SageMaker notebook instance
2. Upload `train_xgboost_notebook.ipynb`
3. Update configuration (bucket name, instance type, etc.)
4. Run cells sequentially

### Option 3: SageMaker Training Job (CLI)

Create a training job directly:

```bash
# Upload data to S3 first
aws s3 cp data/train.csv s3://fraudguard-data/training-data/train/train.csv
aws s3 cp data/val.csv s3://fraudguard-data/training-data/val/val.csv

# Create training job
aws sagemaker create-training-job \
  --training-job-name fraudguard-xgboost-$(date +%s) \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/SageMakerExecutionRole \
  --algorithm-specification TrainingImage=811284229777.dkr.ecr.us-east-1.amazonaws.com/xgboost:latest \
  --input-data-config '[{
    "ChannelName": "train",
    "DataSource": {
      "S3DataSource": {
        "S3Uri": "s3://fraudguard-data/training-data/train/",
        "S3DataType": "S3Prefix"
      }
    }
  }]' \
  --output-data-config S3OutputPath=s3://fraudguard-data/training-data/models/ \
  --resource-config InstanceType=ml.m5.xlarge,InstanceCount=1 \
  --hyper-parameters '{
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "max_depth": "6",
    "eta": "0.1",
    "subsample": "0.8",
    "colsample_bytree": "0.8",
    "num_round": "200"
  }'
```

## Hyperparameters

Default hyperparameters (from PRD):

```python
{
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'max_depth': '6',
    'eta': '0.1',
    'subsample': '0.8',
    'colsample_bytree': '0.8',
    'num_round': '200',
    'min_child_weight': '1',
    'gamma': '0',
    'alpha': '0',
    'lambda': '1',
}
```

### Hyperparameter Tuning

For production, consider using SageMaker Automatic Model Tuning:

```python
from sagemaker.tuner import HyperparameterTuner, IntegerParameter, ContinuousParameter

hyperparameter_ranges = {
    'max_depth': IntegerParameter(3, 10),
    'eta': ContinuousParameter(0.01, 0.3),
    'subsample': ContinuousParameter(0.5, 1.0),
    'colsample_bytree': ContinuousParameter(0.5, 1.0),
    'num_round': IntegerParameter(100, 500),
}

tuner = HyperparameterTuner(
    estimator=estimator,
    objective_metric_name='validation:auc',
    hyperparameter_ranges=hyperparameter_ranges,
    max_jobs=20,
    max_parallel_jobs=5
)

tuner.fit({'train': train_input, 'validation': val_input})
```

## Instance Types

- **Development**: `ml.t2.medium` (cheaper, slower)
- **Production Training**: `ml.m5.xlarge` (balanced)
- **Production Inference**: `ml.m5.large` (optimized for inference)

## Model Evaluation

The training script automatically evaluates the model on the test set:

- **Accuracy**: Overall prediction accuracy
- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **F1 Score**: Harmonic mean of precision and recall
- **ROC AUC**: Area under ROC curve

Target metrics (from PRD):
- Accuracy: > 90%
- Precision: > 85%
- Recall: > 80%
- ROC AUC: > 0.95

## Model Deployment

After training, deploy the model:

```python
# Deploy to endpoint
predictor = estimator.deploy(
    initial_instance_count=1,
    instance_type='ml.t2.medium',  # Use ml.m5.large for production
    endpoint_name='fraudguard-xgboost-endpoint'
)

# Test prediction
sample_features = [[...]]  # Feature vector
prediction = predictor.predict(sample_features)
```

## Cost Estimation

Training costs (approximate):
- `ml.t2.medium`: ~$0.05/hour
- `ml.m5.xlarge`: ~$0.23/hour

For 100k samples:
- Training time: ~10-30 minutes
- Estimated cost: $0.04 - $0.12

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure SageMaker execution role has S3 access
2. **Out of Memory**: Use larger instance type or reduce batch size
3. **Training Job Fails**: Check CloudWatch logs for error details
4. **Slow Training**: Use GPU instances (ml.g4dn.xlarge) for faster training

### Monitoring

Monitor training progress:
- SageMaker Console → Training Jobs
- CloudWatch Logs → `/aws/sagemaker/TrainingJobs`
- Training metrics: validation:auc, validation:error

## Next Steps

After training:
1. Evaluate model performance
2. Deploy model to endpoint
3. Update Lambda functions to use endpoint
4. Test end-to-end fraud detection flow

