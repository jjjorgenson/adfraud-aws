"""
Ingestion Handler Lambda Function
Parses and enriches ad events, stores in DynamoDB and S3
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

import boto3

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")

# Environment variables
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
ORCHESTRATOR_FUNCTION = os.environ.get("ORCHESTRATOR_FUNCTION", "fraudguard-orchestrator")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle incoming ad event from API Gateway

    Args:
        event: API Gateway event containing request body
        context: Lambda context object

    Returns:
        API Gateway response with status code and body
    """
    start_time = datetime.now(timezone.utc)

    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))

        # Validate required fields
        validation_error = validate_event(body)
        if validation_error:
            return create_error_response(400, validation_error)

        # Generate event ID if not provided
        event_id = body.get("event_id", str(uuid4()))

        # Enrich event with context data
        enriched_event = enrich_event(body, event_id)

        # Store in DynamoDB
        store_in_dynamodb(enriched_event)

        # Store raw event in S3
        store_in_s3(body, event_id, start_time)

        # Trigger fraud orchestrator (async invocation)
        trigger_fraud_orchestrator(enriched_event)

        # Calculate latency
        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {"event_id": event_id, "status": "received", "message": "Event stored successfully", "latency_ms": latency_ms}
            ),
        }

    except json.JSONDecodeError as e:
        return create_error_response(400, f"Invalid JSON: {str(e)}")
    except Exception as e:
        return create_error_response(500, f"Internal server error: {str(e)}")


def validate_event(body: Dict[str, Any]) -> Optional[str]:
    """
    Validate required fields in the event

    Args:
        body: Event body dictionary

    Returns:
        Error message if validation fails, None otherwise
    """
    required_fields = ["event_type", "ip_address", "device_id", "campaign_id"]

    for field in required_fields:
        if field not in body or not body[field]:
            return f"Missing required field: {field}"

    # Validate event_type
    valid_event_types = ["click", "impression", "install", "conversion"]
    if body.get("event_type") not in valid_event_types:
        return f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}"

    return None


def enrich_event(body: Dict[str, Any], event_id: str) -> Dict[str, Any]:
    """
    Enrich event with metadata and context data

    Args:
        body: Original event body
        event_id: Generated event ID

    Returns:
        Enriched event dictionary
    """
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())

    # TODO: Lookup context data from DynamoDB
    # - ip_click_count_24h
    # - device_click_count_1h
    # - time_since_last_click

    enriched = {
        "event_id": event_id,
        "timestamp": timestamp,
        "event_type": body.get("event_type"),
        "ip_address": body.get("ip_address"),
        "user_agent": body.get("user_agent", ""),
        "device_id": body.get("device_id"),
        "campaign_id": body.get("campaign_id"),
        "publisher_id": body.get("publisher_id", ""),
        "referrer": body.get("referrer", ""),
        "click_id": body.get("click_id", ""),
        "raw_data": body,
        "ttl": timestamp + (7 * 24 * 60 * 60),  # 7 days TTL
        "created_at": now.isoformat(),
        # Placeholder for enriched context data
        "ip_click_count_24h": 0,  # TODO: Query DynamoDB
        "device_click_count_1h": 0,  # TODO: Query DynamoDB
        "time_since_last_click": None,  # TODO: Query DynamoDB
    }

    return enriched


def convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj


def store_in_dynamodb(event: Dict[str, Any]) -> None:
    """
    Store enriched event in DynamoDB

    Args:
        event: Enriched event dictionary
    """
    if not TABLE_NAME:
        raise ValueError("DYNAMODB_TABLE_NAME environment variable not set")

    # Convert floats to Decimal for DynamoDB compatibility
    event = convert_floats_to_decimal(event)

    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=event)


def store_in_s3(body: Dict[str, Any], event_id: str, timestamp: datetime) -> None:
    """
    Store raw event in S3

    Args:
        body: Original event body
        event_id: Event ID
        timestamp: Event timestamp
    """
    if not BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME environment variable not set")

    # Create S3 key with date partitioning
    date_str = timestamp.strftime("%Y/%m/%d/%H")
    s3_key = f"raw-events/{date_str}/{event_id}.json"

    s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=json.dumps(body), ContentType="application/json")


def trigger_fraud_orchestrator(event: Dict[str, Any]) -> None:
    """
    Trigger fraud orchestrator Lambda function asynchronously

    Args:
        event: Enriched event dictionary
    """
    if not ORCHESTRATOR_FUNCTION:
        return

    try:
        lambda_client.invoke(
            FunctionName=ORCHESTRATOR_FUNCTION, InvocationType="Event", Payload=json.dumps(event)  # Async invocation
        )
    except Exception as e:
        print(f"Error triggering orchestrator: {str(e)}")
        # Don't fail ingestion if orchestrator invocation fails


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create standardized error response

    Args:
        status_code: HTTP status code
        message: Error message

    Returns:
        API Gateway error response
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": message, "status": "error"}),
    }
