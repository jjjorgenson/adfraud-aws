# Storage Utilities

This module provides utilities for DynamoDB and S3 storage operations.

## DynamoDB Utilities (`dynamodb_utils.py`)

### Functions

- `store_event(table_name, event)` - Store event in DynamoDB
- `get_event(table_name, event_id)` - Get event by event_id
- `query_events_by_campaign(table_name, campaign_id, start_timestamp, end_timestamp)` - Query events by campaign using GSI
- `query_events_by_device(table_name, device_id, start_timestamp, end_timestamp)` - Query events by device using GSI
- `get_ip_click_count_24h(table_name, ip_address)` - Get click count for IP in last 24 hours
- `get_device_click_count_1h(table_name, device_id)` - Get click count for device in last hour
- `get_time_since_last_click(table_name, device_id)` - Get time since last click for device
- `update_event_result(table_name, event_id, fraud_result)` - Update event with fraud detection result
- `convert_floats_to_decimal(obj)` - Convert floats to Decimal for DynamoDB compatibility

## S3 Utilities (`s3_utils.py`)

### Functions

- `store_raw_event(bucket_name, event, event_id, timestamp)` - Store raw event in S3 with date partitioning
- `get_raw_event(bucket_name, s3_key)` - Retrieve raw event from S3
- `store_training_data(bucket_name, features, labels, version)` - Store training data in S3
- `list_events_by_date_range(bucket_name, start_date, end_date)` - List all event S3 keys in a date range
- `store_model_artifact(bucket_name, model_data, model_version)` - Store model artifact in S3

## Usage Example

```python
from src.storage import dynamodb_utils, s3_utils

# Store event in DynamoDB
event = {
    'event_id': '123',
    'timestamp': 1234567890,
    'event_type': 'click',
    # ... other fields
}
dynamodb_utils.store_event('fraudguard-events', event)

# Store raw event in S3
s3_key = s3_utils.store_raw_event(
    'fraudguard-data',
    event,
    '123',
    datetime.now(timezone.utc)
)

# Query events by campaign
events = dynamodb_utils.query_events_by_campaign(
    'fraudguard-events',
    'campaign-456',
    start_timestamp=1234567890,
    end_timestamp=1234567890 + 86400
)
```

