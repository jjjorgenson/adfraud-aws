"""
Train XGBoost Model on SageMaker
Prepares dataset and trains XGBoost model using SageMaker's built-in algorithm
"""
import boto3
import sagemaker
from sagemaker import get_execution_role
from sagemaker.amazon.amazon_estimator import get_image_uri
from sagemaker.inputs import TrainingInput
from sagemaker.session import Session
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from typing import Dict, Any

# Initialize SageMaker session
sagemaker_session = sagemaker.Session()
role = get_execution_role()
region = sagemaker_session.boto_region_name

# Configuration
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'fraudguard-data')
PREFIX = 'training-data'
MODEL_NAME = 'fraudguard-xgboost'
INSTANCE_TYPE = 'ml.m5.xlarge'  # Use ml.t2.medium for dev, ml.m5.xlarge for production
INSTANCE_COUNT = 1

# Hyperparameters (from PRD)
HYPERPARAMETERS = {
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
    'scale_pos_weight': '1',  # Adjust if class imbalance
}


def prepare_data_for_sagemaker(
    train_path: str,
    val_path: str,
    test_path: str,
    s3_bucket: str,
    s3_prefix: str
) -> Dict[str, str]:
    """
    Prepare dataset for SageMaker training
    
    Args:
        train_path: Path to training CSV file
        val_path: Path to validation CSV file
        test_path: Path to test CSV file
        s3_bucket: S3 bucket name
        s3_prefix: S3 prefix for training data
        
    Returns:
        Dictionary with S3 paths for train, val, and test data
    """
    print("Preparing data for SageMaker...")
    
    # Load datasets
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)
    
    # Separate features and labels
    feature_columns = [col for col in train_df.columns 
                      if col not in ['is_fraud', 'fraud_type', 'event_id', 'timestamp']]
    
    # Prepare training data (features + label)
    train_data = train_df[feature_columns + ['is_fraud']]
    val_data = val_df[feature_columns + ['is_fraud']]
    test_data = test_df[feature_columns + ['is_fraud']]
    
    # Convert boolean columns to int
    bool_columns = train_data.select_dtypes(include=['bool']).columns
    for col in bool_columns:
        train_data[col] = train_data[col].astype(int)
        val_data[col] = val_data[col].astype(int)
        test_data[col] = test_data[col].astype(int)
    
    # Save to local files
    train_file = 'train.csv'
    val_file = 'val.csv'
    test_file = 'test.csv'
    
    train_data.to_csv(train_file, index=False, header=False)
    val_data.to_csv(val_file, index=False, header=False)
    test_data.to_csv(test_file, index=False, header=False)
    
    # Upload to S3
    s3 = boto3.client('s3')
    
    train_s3_path = f"s3://{s3_bucket}/{s3_prefix}/train/train.csv"
    val_s3_path = f"s3://{s3_bucket}/{s3_prefix}/val/val.csv"
    test_s3_path = f"s3://{s3_bucket}/{s3_prefix}/test/test.csv"
    
    print(f"Uploading training data to {train_s3_path}...")
    s3.upload_file(train_file, s3_bucket, f"{s3_prefix}/train/train.csv")
    
    print(f"Uploading validation data to {val_s3_path}...")
    s3.upload_file(val_file, s3_bucket, f"{s3_prefix}/val/val.csv")
    
    print(f"Uploading test data to {test_s3_path}...")
    s3.upload_file(test_file, s3_bucket, f"{s3_prefix}/test/test.csv")
    
    # Clean up local files
    os.remove(train_file)
    os.remove(val_file)
    os.remove(test_file)
    
    print("Data preparation complete!")
    
    return {
        'train': train_s3_path,
        'val': val_s3_path,
        'test': test_s3_path,
        'feature_columns': feature_columns
    }


def train_xgboost_model(
    train_data_path: str,
    val_data_path: str,
    s3_bucket: str,
    s3_prefix: str,
    hyperparameters: Dict[str, str],
    instance_type: str = 'ml.m5.xlarge',
    instance_count: int = 1
) -> sagemaker.estimator.Estimator:
    """
    Train XGBoost model on SageMaker
    
    Args:
        train_data_path: S3 path to training data
        val_data_path: S3 path to validation data
        s3_bucket: S3 bucket name
        s3_prefix: S3 prefix for model output
        hyperparameters: Model hyperparameters
        instance_type: SageMaker instance type
        instance_count: Number of instances
        
    Returns:
        Trained SageMaker estimator
    """
    print("Starting XGBoost training on SageMaker...")
    
    # Get XGBoost container image
    container = get_image_uri(region, 'xgboost', '1.5-1')
    
    # Create estimator
    estimator = sagemaker.estimator.Estimator(
        image_uri=container,
        role=role,
        instance_count=instance_count,
        instance_type=instance_type,
        hyperparameters=hyperparameters,
        output_path=f's3://{s3_bucket}/{s3_prefix}/models',
        sagemaker_session=sagemaker_session,
        base_job_name=MODEL_NAME
    )
    
    # Prepare training inputs
    train_input = TrainingInput(
        s3_data=train_data_path,
        content_type='text/csv'
    )
    
    val_input = TrainingInput(
        s3_data=val_data_path,
        content_type='text/csv'
    )
    
    # Start training job
    print(f"Training job: {estimator.base_job_name}")
    print(f"Instance type: {instance_type}")
    print(f"Hyperparameters: {hyperparameters}")
    
    estimator.fit(
        inputs={'train': train_input, 'validation': val_input},
        wait=True,
        logs=True
    )
    
    print("Training complete!")
    
    return estimator


def evaluate_model(
    estimator: sagemaker.estimator.Estimator,
    test_data_path: str,
    feature_columns: list
) -> Dict[str, Any]:
    """
    Evaluate trained model on test set
    
    Args:
        estimator: Trained SageMaker estimator
        test_data_path: S3 path to test data
        feature_columns: List of feature column names
        
    Returns:
        Evaluation metrics dictionary
    """
    print("Evaluating model on test set...")
    
    # Deploy model to endpoint for evaluation
    predictor = estimator.deploy(
        initial_instance_count=1,
        instance_type='ml.t2.medium',  # Use smaller instance for evaluation
        endpoint_name=f"{MODEL_NAME}-eval"
    )
    
    # Load test data
    s3 = boto3.client('s3')
    bucket, key = test_data_path.replace('s3://', '').split('/', 1)
    
    # Download test data
    test_file = 'test_eval.csv'
    s3.download_file(bucket, key, test_file)
    
    test_df = pd.read_csv(test_file, header=None)
    test_features = test_df.iloc[:, :-1].values
    test_labels = test_df.iloc[:, -1].values
    
    # Make predictions
    predictions = []
    batch_size = 100
    
    for i in range(0, len(test_features), batch_size):
        batch = test_features[i:i+batch_size]
        batch_predictions = predictor.predict(batch)
        predictions.extend(batch_predictions)
    
    predictions = np.array(predictions)
    
    # Calculate metrics
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score,
        f1_score, roc_auc_score, confusion_matrix
    )
    
    # Convert probabilities to binary predictions
    binary_predictions = (predictions > 0.5).astype(int)
    
    metrics = {
        'accuracy': float(accuracy_score(test_labels, binary_predictions)),
        'precision': float(precision_score(test_labels, binary_predictions)),
        'recall': float(recall_score(test_labels, binary_predictions)),
        'f1_score': float(f1_score(test_labels, binary_predictions)),
        'roc_auc': float(roc_auc_score(test_labels, predictions)),
        'confusion_matrix': confusion_matrix(test_labels, binary_predictions).tolist()
    }
    
    print("\nModel Evaluation Metrics:")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 Score: {metrics['f1_score']:.4f}")
    print(f"ROC AUC: {metrics['roc_auc']:.4f}")
    print(f"\nConfusion Matrix:")
    print(metrics['confusion_matrix'])
    
    # Clean up
    os.remove(test_file)
    predictor.delete_endpoint()
    
    return metrics


def save_model_info(
    estimator: sagemaker.estimator.Estimator,
    metrics: Dict[str, Any],
    feature_columns: list,
    output_path: str
):
    """
    Save model information to JSON file
    
    Args:
        estimator: Trained SageMaker estimator
        metrics: Evaluation metrics
        feature_columns: List of feature column names
        output_path: Path to save model info
    """
    model_info = {
        'model_name': MODEL_NAME,
        'training_job_name': estimator.latest_training_job.name,
        'model_artifact': estimator.model_data,
        'hyperparameters': HYPERPARAMETERS,
        'features': feature_columns,
        'num_features': len(feature_columns),
        'evaluation_metrics': metrics,
        'created_at': datetime.now().isoformat(),
        'instance_type': INSTANCE_TYPE,
    }
    
    with open(output_path, 'w') as f:
        json.dump(model_info, f, indent=2)
    
    print(f"\nModel info saved to {output_path}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train XGBoost model on SageMaker')
    parser.add_argument('--train-data', type=str, required=True, help='Path to training CSV file')
    parser.add_argument('--val-data', type=str, required=True, help='Path to validation CSV file')
    parser.add_argument('--test-data', type=str, required=True, help='Path to test CSV file')
    parser.add_argument('--s3-bucket', type=str, default=BUCKET_NAME, help='S3 bucket name')
    parser.add_argument('--s3-prefix', type=str, default=PREFIX, help='S3 prefix for training data')
    parser.add_argument('--instance-type', type=str, default=INSTANCE_TYPE, help='SageMaker instance type')
    parser.add_argument('--no-eval', action='store_true', help='Skip model evaluation')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("XGBoost Model Training on SageMaker")
    print("=" * 60)
    
    # Prepare data
    data_paths = prepare_data_for_sagemaker(
        args.train_data,
        args.val_data,
        args.test_data,
        args.s3_bucket,
        args.s3_prefix
    )
    
    # Train model
    estimator = train_xgboost_model(
        data_paths['train'],
        data_paths['val'],
        args.s3_bucket,
        args.s3_prefix,
        HYPERPARAMETERS,
        args.instance_type,
        INSTANCE_COUNT
    )
    
    # Evaluate model
    if not args.no_eval:
        metrics = evaluate_model(
            estimator,
            data_paths['test'],
            data_paths['feature_columns']
        )
        
        # Save model info
        save_model_info(
            estimator,
            metrics,
            data_paths['feature_columns'],
            'model_info.json'
        )
    
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print(f"Model artifact: {estimator.model_data}")
    print(f"Training job: {estimator.latest_training_job.name}")
    print("\nTo deploy the model, use:")
    print(f"  predictor = estimator.deploy(instance_type='ml.t2.medium', initial_instance_count=1)")


if __name__ == '__main__':
    main()

