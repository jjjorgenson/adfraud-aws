"""
S3 utility functions for event storage and retrieval
"""
import json
import boto3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

s3_client = boto3.client('s3')


def store_raw_event(
    bucket_name: str,
    event: Dict[str, Any],
    event_id: str,
    timestamp: datetime
) -> str:
    """
    Store raw event in S3 with date partitioning
    
    Args:
        bucket_name: Name of the S3 bucket
        event: Event dictionary to store
        event_id: Event ID
        timestamp: Event timestamp
        
    Returns:
        S3 key where event was stored
    """
    # Create S3 key with date partitioning
    date_str = timestamp.strftime('%Y/%m/%d/%H')
    s3_key = f"raw-events/date={timestamp.strftime('%Y-%m-%d')}/hour={timestamp.strftime('%H')}/{event_id}.json"
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json.dumps(event),
        ContentType='application/json',
        Metadata={
            'event_id': event_id,
            'event_type': event.get('event_type', 'unknown'),
            'timestamp': timestamp.isoformat()
        }
    )
    
    return s3_key


def get_raw_event(bucket_name: str, s3_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve raw event from S3
    
    Args:
        bucket_name: Name of the S3 bucket
        s3_key: S3 key of the event
        
    Returns:
        Event dictionary or None if not found
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        content = response['Body'].read()
        return json.loads(content)
    except Exception as e:
        print(f"Error getting event from S3: {str(e)}")
        return None


def store_training_data(
    bucket_name: str,
    features: Any,
    labels: Any,
    version: str = "v1.0"
) -> Dict[str, str]:
    """
    Store training data in S3 in Parquet format
    
    Args:
        bucket_name: Name of the S3 bucket
        features: Feature data (pandas DataFrame or similar)
        labels: Label data (pandas Series or similar)
        version: Model version
        
    Returns:
        Dictionary with S3 keys for features and labels
    """
    # TODO: Implement Parquet storage
    # For now, store as JSON
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    
    features_key = f"training-data/{version}/features_{timestamp}.json"
    labels_key = f"training-data/{version}/labels_{timestamp}.json"
    
    # Convert to JSON (replace with Parquet conversion later)
    s3_client.put_object(
        Bucket=bucket_name,
        Key=features_key,
        Body=json.dumps(features),
        ContentType='application/json'
    )
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=labels_key,
        Body=json.dumps(labels),
        ContentType='application/json'
    )
    
    return {
        'features_key': features_key,
        'labels_key': labels_key
    }


def list_events_by_date_range(
    bucket_name: str,
    start_date: datetime,
    end_date: datetime
) -> List[str]:
    """
    List all event S3 keys in a date range
    
    Args:
        bucket_name: Name of the S3 bucket
        start_date: Start date
        end_date: End date
        
    Returns:
        List of S3 keys
    """
    keys = []
    current_date = start_date
    
    while current_date <= end_date:
        prefix = f"raw-events/date={current_date.strftime('%Y-%m-%d')}/"
        
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                keys.extend([obj['Key'] for obj in response['Contents']])
        except Exception as e:
            print(f"Error listing events: {str(e)}")
        
        current_date += timedelta(days=1)
    
    return keys


def store_model_artifact(
    bucket_name: str,
    model_data: bytes,
    model_version: str
) -> str:
    """
    Store model artifact in S3
    
    Args:
        bucket_name: Name of the S3 bucket
        model_data: Model data as bytes
        model_version: Model version string
        
    Returns:
        S3 key where model was stored
    """
    s3_key = f"models/{model_version}/model.tar.gz"
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=model_data,
        ContentType='application/gzip'
    )
    
    return s3_key

