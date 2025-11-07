"""
Fraud Orchestrator Lambda Function
Routes events to ML or ML+AI analysis path based on ML score
"""
import json
import os
import boto3
import csv
import io
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

# Import feature extraction
try:
    from feature_extractor import extract_features
except ImportError:
    # Fallback for Lambda deployment
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from feature_extractor import extract_features

# Initialize AWS clients
sagemaker = boto3.client('sagemaker-runtime')
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

# Environment variables
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT', 'fraudguard-xgboost-endpoint')
AI_ANALYZER_FUNCTION = os.environ.get('AI_ANALYZER_FUNCTION', 'fraudguard-ai-analyzer')
DECISION_COMBINER_FUNCTION = os.environ.get('DECISION_COMBINER_FUNCTION', '')  # Optional: use dedicated combiner
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')

# Decision thresholds
FRAUD_THRESHOLD = 0.8  # Block immediately if ML score > 0.8
LEGITIMATE_THRESHOLD = 0.3  # Allow immediately if ML score < 0.3
BORDERLINE_MIN = 0.3  # Route to AI if score between 0.3 and 0.8
BORDERLINE_MAX = 0.8

# In-memory cache for fraud rate lookups (5 minute TTL)
_fraud_rate_cache = {}
CACHE_TTL = 300  # 5 minutes in seconds


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Orchestrate fraud detection workflow
    
    Args:
        event: Event from ingestion handler or API Gateway
        context: Lambda context object
        
    Returns:
        Fraud detection result
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # Extract event data
        if 'body' in event:
            body = json.loads(event.get('body', '{}'))
        else:
            body = event
        
        event_id = body.get('event_id')
        if not event_id:
            return create_error_response(400, "Missing event_id")
        
        # Get context data from DynamoDB
        # Check if this is a Google Ads event (limited signals)
        is_google_ads = body.get('source') == 'google_ads'
        
        if is_google_ads:
            context_data = get_google_ads_context_data(
                body.get('keyword'),
                body.get('target_id'),
                body.get('gclid')
            )
        else:
            context_data = get_context_data(
                event_id,
                body.get('device_id'),
                body.get('ip_address')
            )
        
        # Extract features for ML model
        feature_vector = extract_features(body, context_data)
        
        # Call SageMaker endpoint for ML score
        ml_score = get_ml_score(feature_vector)
        
        # Decision logic
        if ml_score > FRAUD_THRESHOLD:
            # Clear fraud - block immediately
            result = create_ml_only_response(
                event_id, ml_score, True, 'block', start_time
            )
        elif ml_score < LEGITIMATE_THRESHOLD:
            # Clear legitimate - allow immediately
            result = create_ml_only_response(
                event_id, ml_score, False, 'allow', start_time
            )
        else:
            # Borderline case - route to AI analysis
            result = route_to_ai_analysis(body, ml_score, feature_vector, start_time)
        
        # Store result in DynamoDB
        store_result(event_id, result)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        return create_error_response(500, f"Orchestration error: {str(e)}")


def get_cached_fraud_rate(cache_key: str, fetch_func) -> float:
    """
    Get cached fraud rate or fetch and cache if expired
    
    Args:
        cache_key: Cache key (e.g., 'keyword:buy-shoes' or 'target:placement-123')
        fetch_func: Function to call if cache miss or expired
        
    Returns:
        Fraud rate (0.0-1.0)
    """
    now = time.time()
    
    # Check cache
    if cache_key in _fraud_rate_cache:
        value, timestamp = _fraud_rate_cache[cache_key]
        if now - timestamp < CACHE_TTL:
            return value
    
    # Cache miss or expired - fetch and cache
    value = fetch_func()
    _fraud_rate_cache[cache_key] = (value, now)
    return value


def get_google_ads_context_data(keyword: str, target_id: str, gclid: str) -> Dict[str, Any]:
    """
    Get context data for Google Ads events (limited signals)
    
    Args:
        keyword: Keyword from Google Ads
        target_id: Target/placement ID
        gclid: Google Click ID
        
    Returns:
        Context data dictionary with Google-specific features
    """
    if not TABLE_NAME:
        return {}
    
    try:
        # Import storage utilities
        try:
            from storage.dynamodb_utils import (
                get_keyword_fraud_rate,
                get_target_fraud_rate
            )
        except ImportError:
            # Fallback - define simple functions
            def get_keyword_fraud_rate(table_name, keyword, days=30):
                return 0.0
            def get_target_fraud_rate(table_name, target_id, days=30):
                return 0.0
        
        # Get historical fraud rates with caching
        keyword_fraud_rate = 0.0
        if keyword:
            cache_key = f'keyword:{keyword}'
            keyword_fraud_rate = get_cached_fraud_rate(
                cache_key,
                lambda: get_keyword_fraud_rate(TABLE_NAME, keyword, days=30)
            )
        
        target_fraud_rate = 0.0
        if target_id:
            cache_key = f'target:{target_id}'
            target_fraud_rate = get_cached_fraud_rate(
                cache_key,
                lambda: get_target_fraud_rate(TABLE_NAME, target_id, days=30)
            )
        
        # Analyze GCLID pattern (simplified - would use more sophisticated analysis)
        gclid_pattern_score = analyze_gclid_pattern(gclid) if gclid else 0.5
        
        return {
            'keyword_fraud_rate': keyword_fraud_rate,
            'target_fraud_rate': target_fraud_rate,
            'gclid_pattern_score': gclid_pattern_score,
            # Set missing signals to defaults
            'ip_click_count_24h': 0,
            'device_click_count_1h': 0,
            'time_since_last_click': None
        }
    except Exception as e:
        print(f"Error getting Google Ads context data: {str(e)}")
        return {}


def analyze_gclid_pattern(gclid: str) -> float:
    """
    Analyze GCLID for bot-like patterns
    
    Args:
        gclid: Google Click ID
        
    Returns:
        Pattern score (0.0-1.0, higher = more suspicious)
    """
    if not gclid:
        return 0.5
    
    # Simple pattern analysis
    # In production, would use more sophisticated analysis
    # Check for suspicious patterns like:
    # - Low entropy (repetitive characters)
    # - Sequential patterns
    # - Unusual character distributions
    
    from feature_extractor import calculate_entropy
    
    entropy = calculate_entropy(gclid)
    
    # Lower entropy = more suspicious (bot-like patterns)
    # Normalize to 0-1 (inverse: low entropy = high suspicion)
    pattern_score = 1.0 - entropy
    
    return pattern_score


def get_context_data(event_id: str, device_id: str, ip_address: str) -> Dict[str, Any]:
    """
    Get context data from DynamoDB for feature enrichment
    
    Args:
        event_id: Event ID
        device_id: Device ID
        ip_address: IP address
        
    Returns:
        Context data dictionary
    """
    if not TABLE_NAME:
        return {}
    
    try:
        # Import storage utilities
        try:
            from storage.dynamodb_utils import (
                get_device_click_count_1h,
                get_time_since_last_click,
                query_events_by_device
            )
        except ImportError:
            # Fallback - define simple query function
            def query_events_by_device(table_name, device_id, start_ts, end_ts):
                table = dynamodb.Table(table_name)
                try:
                    response = table.query(
                        IndexName='device-timestamp-index',
                        KeyConditionExpression='device_id = :device_id AND timestamp BETWEEN :start AND :end',
                        ExpressionAttributeValues={
                            ':device_id': device_id,
                            ':start': start_ts,
                            ':end': end_ts
                        }
                    )
                    return response.get('Items', [])
                except:
                    return []
            
            def get_time_since_last_click(table_name, device_id):
                # Simplified implementation
                return None
        
        # Get device history
        now = datetime.now(timezone.utc)
        one_hour_ago = int((now - timedelta(hours=1)).timestamp())
        now_timestamp = int(now.timestamp())
        
        device_events = query_events_by_device(TABLE_NAME, device_id, one_hour_ago, now_timestamp)
        device_click_count_1h = len(device_events)
        
        # Get time since last click
        time_since_last_click = get_time_since_last_click(TABLE_NAME, device_id)
        
        # Get IP click count (simplified - would need GSI in production)
        # For now, use placeholder
        ip_click_count_24h = 0
        
        return {
            'ip_click_count_24h': ip_click_count_24h,
            'device_click_count_1h': device_click_count_1h,
            'time_since_last_click': time_since_last_click
        }
    except Exception as e:
        print(f"Error getting context data: {str(e)}")
        return {}


def get_ml_score(feature_vector: List[float]) -> float:
    """
    Get ML fraud score from SageMaker endpoint
    
    Args:
        feature_vector: List of feature values in CSV format
        
    Returns:
        ML fraud score (0.0-1.0)
    """
    if not SAGEMAKER_ENDPOINT:
        # Fallback: return placeholder score for development
        print("Warning: SAGEMAKER_ENDPOINT not set, using fallback score")
        return 0.5
    
    try:
        # Convert feature vector to CSV format (SageMaker XGBoost expects CSV)
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(feature_vector)
        csv_data = csv_buffer.getvalue()
        
        # Invoke SageMaker endpoint
        response = sagemaker.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='text/csv',
            Body=csv_data.encode('utf-8')
        )
        
        # Parse response (XGBoost returns predictions as CSV)
        result = response['Body'].read().decode('utf-8')
        prediction = float(result.strip())
        
        # XGBoost returns probability, which is already 0-1
        return prediction
        
    except Exception as e:
        # Fallback on error
        print(f"Error calling SageMaker endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0.5


def route_to_ai_analysis(
    body: Dict[str, Any],
    ml_score: float,
    feature_vector: List[float],
    start_time: datetime
) -> Dict[str, Any]:
    """
    Route borderline cases to AI analysis
    
    Args:
        body: Original event body
        ml_score: ML fraud score
        features: Extracted features
        start_time: Request start time
        
    Returns:
        Combined ML+AI result
    """
    try:
        # Invoke AI analyzer Lambda
        ai_response = lambda_client.invoke(
            FunctionName=AI_ANALYZER_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'body': json.dumps({
                    **body,
                    'ml_score': ml_score,
                    'feature_vector': feature_vector
                })
            })
        )
        
        ai_result = json.loads(ai_response['Payload'].read())
        ai_data = json.loads(ai_result.get('body', '{}'))
        
        # Use dedicated decision combiner if available, otherwise combine inline
        if DECISION_COMBINER_FUNCTION:
            return use_decision_combiner_lambda(body, ml_score, ai_data, start_time)
        else:
            return combine_scores_inline(body, ml_score, ai_data, start_time)
        
    except Exception as e:
        # Fallback to ML-only result if AI analysis fails
        print(f"Error in AI analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_ml_only_response(
            body.get('event_id'),
            ml_score,
            ml_score > 0.65,
            'review',
            start_time
        )


def use_decision_combiner_lambda(
    body: Dict[str, Any],
    ml_score: float,
    ai_data: Dict[str, Any],
    start_time: datetime
) -> Dict[str, Any]:
    """
    Use dedicated decision combiner Lambda function
    
    Args:
        body: Original event body
        ml_score: ML fraud score
        ai_data: AI analysis result
        start_time: Request start time
        
    Returns:
        Combined result from decision combiner
    """
    try:
        # Invoke decision combiner Lambda
        combiner_response = lambda_client.invoke(
            FunctionName=DECISION_COMBINER_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'body': json.dumps({
                    'event_id': body.get('event_id'),
                    'ml_score': ml_score,
                    'ai_result': ai_data
                })
            })
        )
        
        combiner_result = json.loads(combiner_response['Payload'].read())
        result = json.loads(combiner_result.get('body', '{}'))
        
        # Add latency
        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        result['latency_ms'] = latency_ms
        
        return result
        
    except Exception as e:
        # Fallback to inline combination
        print(f"Error calling decision combiner: {str(e)}")
        return combine_scores_inline(body, ml_score, ai_data, start_time)


def combine_scores_inline(
    body: Dict[str, Any],
    ml_score: float,
    ai_data: Dict[str, Any],
    start_time: datetime
) -> Dict[str, Any]:
    """
    Combine ML and AI scores inline (fallback method)
    
    Args:
        body: Original event body
        ml_score: ML fraud score
        ai_data: AI analysis result
        start_time: Request start time
        
    Returns:
        Combined result
    """
    # Combine ML and AI scores
    ai_score = ai_data.get('ai_score', ml_score)
    ai_confidence = ai_data.get('confidence', 0.5)
    
    # Ensemble scoring: 40% ML, 60% AI (when AI confidence > 0.8)
    if ai_confidence > 0.8:
        final_score = (ml_score * 0.4) + (ai_score * 0.6)
    else:
        final_score = (ml_score * 0.6) + (ai_score * 0.4)
    
    # Final decision
    is_fraud = final_score > 0.65
    action = 'block' if is_fraud else ('review' if final_score > 0.5 else 'allow')
    
    latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    return {
        'event_id': body.get('event_id'),
        'is_fraud': is_fraud,
        'fraud_score': final_score,
        'ml_score': ml_score,
        'ai_score': ai_score,
        'confidence': ai_confidence,
        'detection_method': 'ml_ai_ensemble',
        'fraud_signals': ai_data.get('fraud_signals', []),
        'reasoning': ai_data.get('reasoning', ''),
        'recommended_action': action,
        'latency_ms': latency_ms
    }


def create_ml_only_response(
    event_id: str,
    ml_score: float,
    is_fraud: bool,
    action: str,
    start_time: datetime
) -> Dict[str, Any]:
    """
    Create ML-only response
    
    Args:
        event_id: Event ID
        ml_score: ML fraud score
        is_fraud: Fraud verdict
        action: Recommended action
        start_time: Request start time
        
    Returns:
        ML-only response dictionary
    """
    latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    return {
        'event_id': event_id,
        'is_fraud': is_fraud,
        'fraud_score': ml_score,
        'confidence': 0.8 if ml_score > FRAUD_THRESHOLD or ml_score < LEGITIMATE_THRESHOLD else 0.5,
        'detection_method': 'ml_only',
        'latency_ms': latency_ms,
        'action': action
    }


def store_result(event_id: str, result: Dict[str, Any]) -> None:
    """
    Store fraud detection result in DynamoDB
    
    Args:
        event_id: Event ID
        result: Detection result
    """
    if not TABLE_NAME:
        return
    
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.update_item(
            Key={'event_id': event_id},
            UpdateExpression='SET fraud_result = :result, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':result': result,
                ':timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
    except Exception as e:
        print(f"Error storing result: {str(e)}")


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
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': message,
            'status': 'error'
        })
    }

