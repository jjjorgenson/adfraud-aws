"""
Decision Combiner Lambda Function
Combines ML and AI analysis results for final fraud decisions using ensemble methods
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

# Configuration
FRAUD_THRESHOLD = float(os.environ.get("FRAUD_THRESHOLD", "0.65"))
REVIEW_THRESHOLD = float(os.environ.get("REVIEW_THRESHOLD", "0.5"))
ML_WEIGHT = float(os.environ.get("ML_WEIGHT", "0.4"))
AI_WEIGHT = float(os.environ.get("AI_WEIGHT", "0.6"))
ENSEMBLE_METHOD = os.environ.get("ENSEMBLE_METHOD", "confidence_weighted")  # confidence_weighted, fixed_weight, max, min


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Combine ML and AI scores for final fraud decision

    Args:
        event: Event with ML and AI analysis results
        context: Lambda context object

    Returns:
        Final fraud decision with combined scores
    """
    try:
        # Parse event data
        if "body" in event:
            body = json.loads(event.get("body", "{}"))
        else:
            body = event

        # Extract ML and AI scores
        ml_score = body.get("ml_score", 0.5)
        ai_result = body.get("ai_result", {})

        # If ai_result is a string, parse it
        if isinstance(ai_result, str):
            ai_result = json.loads(ai_result)

        ai_score = ai_result.get("ai_score", ml_score)
        ai_confidence = ai_result.get("confidence", 0.5)
        ai_is_fraud = ai_result.get("is_fraud", False)
        fraud_signals = ai_result.get("fraud_signals", [])
        reasoning = ai_result.get("reasoning", "")
        primary_fraud_type = ai_result.get("primary_fraud_type", "unknown")

        # Combine scores using ensemble method
        final_score, ensemble_details = combine_scores(
            ml_score=ml_score, ai_score=ai_score, ai_confidence=ai_confidence, method=ENSEMBLE_METHOD
        )

        # Make final decision
        decision = make_decision(
            final_score=final_score, ml_score=ml_score, ai_score=ai_score, ai_is_fraud=ai_is_fraud, ai_confidence=ai_confidence
        )

        # Build response
        result = {
            "event_id": body.get("event_id", "unknown"),
            "is_fraud": decision["is_fraud"],
            "fraud_score": round(final_score, 4),
            "ml_score": round(ml_score, 4),
            "ai_score": round(ai_score, 4),
            "ai_confidence": round(ai_confidence, 4),
            "detection_method": decision["method"],
            "recommended_action": decision["action"],
            "fraud_signals": fraud_signals,
            "primary_fraud_type": primary_fraud_type,
            "reasoning": reasoning,
            "ensemble_details": ensemble_details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps(result),
        }

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {"error": str(e), "message": "Failed to combine ML and AI scores", "is_fraud": False, "fraud_score": 0.0}
            ),
        }


def combine_scores(
    ml_score: float, ai_score: float, ai_confidence: float, method: str = "confidence_weighted"
) -> Tuple[float, Dict[str, Any]]:
    """
    Combine ML and AI scores using ensemble method

    Args:
        ml_score: ML fraud score (0.0-1.0)
        ai_score: AI fraud score (0.0-1.0)
        ai_confidence: AI confidence level (0.0-1.0)
        method: Ensemble method to use

    Returns:
        Tuple of (final_score, ensemble_details)
    """
    ensemble_details = {"method": method, "ml_score": ml_score, "ai_score": ai_score, "ai_confidence": ai_confidence}

    if method == "confidence_weighted":
        # Weight AI more when confidence is high
        if ai_confidence > 0.8:
            ml_weight = 0.3
            ai_weight = 0.7
        elif ai_confidence > 0.6:
            ml_weight = 0.4
            ai_weight = 0.6
        else:
            ml_weight = 0.6
            ai_weight = 0.4

        final_score = (ml_score * ml_weight) + (ai_score * ai_weight)
        ensemble_details["ml_weight"] = ml_weight
        ensemble_details["ai_weight"] = ai_weight

    elif method == "fixed_weight":
        # Use fixed weights from environment
        final_score = (ml_score * ML_WEIGHT) + (ai_score * AI_WEIGHT)
        ensemble_details["ml_weight"] = ML_WEIGHT
        ensemble_details["ai_weight"] = AI_WEIGHT

    elif method == "max":
        # Take maximum of both scores (conservative - more fraud detections)
        final_score = max(ml_score, ai_score)
        ensemble_details["operation"] = "max"

    elif method == "min":
        # Take minimum of both scores (lenient - fewer false positives)
        final_score = min(ml_score, ai_score)
        ensemble_details["operation"] = "min"

    elif method == "average":
        # Simple average
        final_score = (ml_score + ai_score) / 2.0
        ensemble_details["operation"] = "average"

    else:
        # Default to confidence-weighted
        ml_weight = 0.4 if ai_confidence > 0.6 else 0.6
        ai_weight = 1.0 - ml_weight
        final_score = (ml_score * ml_weight) + (ai_score * ai_weight)
        ensemble_details["method"] = "confidence_weighted"
        ensemble_details["ml_weight"] = ml_weight
        ensemble_details["ai_weight"] = ai_weight

    # Ensure score is in valid range
    final_score = max(0.0, min(1.0, final_score))

    return final_score, ensemble_details


def make_decision(
    final_score: float, ml_score: float, ai_score: float, ai_is_fraud: bool, ai_confidence: float
) -> Dict[str, Any]:
    """
    Make final fraud decision based on combined score

    Args:
        final_score: Combined ensemble score
        ml_score: ML fraud score
        ai_score: AI fraud score
        ai_is_fraud: AI's fraud verdict
        ai_confidence: AI confidence level

    Returns:
        Decision dictionary with is_fraud, action, and method
    """
    # Determine if fraud
    is_fraud = final_score > FRAUD_THRESHOLD

    # Determine action
    if is_fraud:
        action = "block"
    elif final_score > REVIEW_THRESHOLD:
        action = "review"
    else:
        action = "allow"

    # Determine detection method
    if ml_score > 0.8 or ml_score < 0.3:
        method = "ml_only"
    elif ai_confidence > 0.7:
        method = "ml_ai_ensemble"
    else:
        method = "ml_primary"

    # Special cases: Override with AI verdict if high confidence
    if ai_confidence > 0.9 and ai_is_fraud != is_fraud:
        # AI is very confident and disagrees with ensemble
        is_fraud = ai_is_fraud
        action = "block" if ai_is_fraud else "allow"
        method = "ai_override"

    return {"is_fraud": is_fraud, "action": action, "method": method}
