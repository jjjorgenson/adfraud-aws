"""
DynamoDB utility functions for event storage and retrieval
"""
import boto3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')


def get_table(table_name: str):
    """
    Get DynamoDB table resource
    
    Args:
        table_name: Name of the DynamoDB table
        
    Returns:
        DynamoDB table resource
    """
    return dynamodb.Table(table_name)


def store_event(table_name: str, event: Dict[str, Any]) -> None:
    """
    Store event in DynamoDB
    
    Args:
        table_name: Name of the DynamoDB table
        event: Event dictionary to store
    """
    table = get_table(table_name)
    
    # Convert floats to Decimal for DynamoDB
    event = convert_floats_to_decimal(event)
    
    table.put_item(Item=event)


def get_event(table_name: str, event_id: str) -> Optional[Dict[str, Any]]:
    """
    Get event by event_id
    
    Args:
        table_name: Name of the DynamoDB table
        event_id: Event ID to retrieve
        
    Returns:
        Event dictionary or None if not found
    """
    table = get_table(table_name)
    
    try:
        response = table.get_item(
            Key={
                'event_id': event_id
            }
        )
        return response.get('Item')
    except Exception as e:
        print(f"Error getting event: {str(e)}")
        return None


def query_events_by_campaign(
    table_name: str,
    campaign_id: str,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Query events by campaign_id using GSI
    
    Args:
        table_name: Name of the DynamoDB table
        campaign_id: Campaign ID to query
        start_timestamp: Start timestamp (Unix epoch)
        end_timestamp: End timestamp (Unix epoch)
        
    Returns:
        List of event dictionaries
    """
    table = get_table(table_name)
    
    key_condition = 'campaign_id = :campaign_id'
    expression_values = {':campaign_id': campaign_id}
    
    if start_timestamp and end_timestamp:
        key_condition += ' AND timestamp BETWEEN :start AND :end'
        expression_values[':start'] = start_timestamp
        expression_values[':end'] = end_timestamp
    
    try:
        response = table.query(
            IndexName='campaign-timestamp-index',
            KeyConditionExpression=key_condition,
            ExpressionAttributeValues=expression_values
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error querying events by campaign: {str(e)}")
        return []


def query_events_by_device(
    table_name: str,
    device_id: str,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Query events by device_id using GSI
    
    Args:
        table_name: Name of the DynamoDB table
        device_id: Device ID to query
        start_timestamp: Start timestamp (Unix epoch)
        end_timestamp: End timestamp (Unix epoch)
        
    Returns:
        List of event dictionaries
    """
    table = get_table(table_name)
    
    key_condition = 'device_id = :device_id'
    expression_values = {':device_id': device_id}
    
    if start_timestamp and end_timestamp:
        key_condition += ' AND timestamp BETWEEN :start AND :end'
        expression_values[':start'] = start_timestamp
        expression_values[':end'] = end_timestamp
    
    try:
        response = table.query(
            IndexName='device-timestamp-index',
            KeyConditionExpression=key_condition,
            ExpressionAttributeValues=expression_values
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error querying events by device: {str(e)}")
        return []


def get_ip_click_count_24h(table_name: str, ip_address: str) -> int:
    """
    Get click count for IP address in last 24 hours
    
    Args:
        table_name: Name of the DynamoDB table
        ip_address: IP address to query
        
    Returns:
        Click count in last 24 hours
    """
    # TODO: Implement efficient query for IP click count
    # This would require a GSI on ip_address + timestamp
    # For now, return placeholder
    return 0


def get_device_click_count_1h(table_name: str, device_id: str) -> int:
    """
    Get click count for device in last 1 hour
    
    Args:
        table_name: Name of the DynamoDB table
        device_id: Device ID to query
        
    Returns:
        Click count in last 1 hour
    """
    now = datetime.now(timezone.utc)
    one_hour_ago = int((now - timedelta(hours=1)).timestamp())
    now_timestamp = int(now.timestamp())
    
    events = query_events_by_device(table_name, device_id, one_hour_ago, now_timestamp)
    return len(events)


def get_time_since_last_click(table_name: str, device_id: str) -> Optional[int]:
    """
    Get time since last click for device
    
    Args:
        table_name: Name of the DynamoDB table
        device_id: Device ID to query
        
    Returns:
        Seconds since last click, or None if no previous clicks
    """
    now = datetime.now(timezone.utc)
    one_day_ago = int((now - timedelta(days=1)).timestamp())
    now_timestamp = int(now.timestamp())
    
    events = query_events_by_device(table_name, device_id, one_day_ago, now_timestamp)
    
    if not events:
        return None
    
    # Sort by timestamp descending
    events.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    last_click_timestamp = events[0].get('timestamp', 0)
    
    return now_timestamp - last_click_timestamp


def update_event_result(
    table_name: str,
    event_id: str,
    fraud_result: Dict[str, Any]
) -> None:
    """
    Update event with fraud detection result
    
    Args:
        table_name: Name of the DynamoDB table
        event_id: Event ID to update
        fraud_result: Fraud detection result dictionary
    """
    table = get_table(table_name)
    
    # Convert floats to Decimal
    fraud_result = convert_floats_to_decimal(fraud_result)
    
    update_expression = 'SET fraud_result = :result, updated_at = :timestamp'
    expression_values = {
        ':result': fraud_result,
        ':timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Add individual fields for easier querying
    if 'is_fraud' in fraud_result:
        update_expression += ', is_fraud = :is_fraud'
        expression_values[':is_fraud'] = fraud_result['is_fraud']
    
    if 'fraud_score' in fraud_result:
        update_expression += ', fraud_score = :fraud_score'
        expression_values[':fraud_score'] = fraud_result['fraud_score']
    
    if 'ml_score' in fraud_result:
        update_expression += ', ml_score = :ml_score'
        expression_values[':ml_score'] = fraud_result['ml_score']
    
    if 'ai_score' in fraud_result:
        update_expression += ', ai_score = :ai_score'
        expression_values[':ai_score'] = fraud_result['ai_score']
    
    if 'detection_method' in fraud_result:
        update_expression += ', detection_method = :detection_method'
        expression_values[':detection_method'] = fraud_result['detection_method']
    
    try:
        table.update_item(
            Key={'event_id': event_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
    except Exception as e:
        print(f"Error updating event result: {str(e)}")


def convert_floats_to_decimal(obj: Any) -> Any:
    """
    Convert float values to Decimal for DynamoDB compatibility
    
    Args:
        obj: Object to convert
        
    Returns:
        Object with floats converted to Decimal
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj

