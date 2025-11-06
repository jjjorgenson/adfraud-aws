# Decision Combiner Lambda

The Decision Combiner Lambda function combines ML and AI analysis results to make final fraud decisions using ensemble methods.

## Overview

This Lambda function takes ML scores and AI analysis results and combines them using configurable ensemble methods to produce a final fraud decision.

## Features

- **Multiple Ensemble Methods**: Support for confidence-weighted, fixed-weight, max, min, and average methods
- **Configurable Thresholds**: Customizable fraud and review thresholds
- **AI Override Logic**: High-confidence AI verdicts can override ensemble decisions
- **Detailed Response**: Returns comprehensive decision details including ensemble weights and reasoning

## Environment Variables

- `FRAUD_THRESHOLD` (default: 0.65): Score above which fraud is detected
- `REVIEW_THRESHOLD` (default: 0.5): Score above which review is recommended
- `ML_WEIGHT` (default: 0.4): Weight for ML score in fixed-weight ensemble
- `AI_WEIGHT` (default: 0.6): Weight for AI score in fixed-weight ensemble
- `ENSEMBLE_METHOD` (default: confidence_weighted): Ensemble method to use

## Ensemble Methods

### 1. Confidence-Weighted (Default)

Dynamically adjusts weights based on AI confidence:

- AI confidence > 0.8: ML 30%, AI 70%
- AI confidence > 0.6: ML 40%, AI 60%
- AI confidence ≤ 0.6: ML 60%, AI 40%

**Best for**: Most scenarios, adapts to AI reliability

### 2. Fixed-Weight

Uses fixed weights from environment variables:

- ML weight: `ML_WEIGHT` (default: 0.4)
- AI weight: `AI_WEIGHT` (default: 0.6)

**Best for**: Consistent weighting regardless of confidence

### 3. Max

Takes the maximum of ML and AI scores (more conservative, detects more fraud).

**Best for**: High-security scenarios where false negatives are costly

### 4. Min

Takes the minimum of ML and AI scores (more lenient, fewer false positives).

**Best for**: Scenarios where false positives are costly

### 5. Average

Simple average of ML and AI scores.

**Best for**: Balanced approach

## Input Format

```json
{
  "event_id": "string",
  "ml_score": 0.75,
  "ai_result": {
    "ai_score": 0.85,
    "confidence": 0.9,
    "is_fraud": true,
    "fraud_signals": ["signal1", "signal2"],
    "reasoning": "Explanation...",
    "primary_fraud_type": "bot_traffic"
  }
}
```

## Output Format

```json
{
  "event_id": "string",
  "is_fraud": true,
  "fraud_score": 0.82,
  "ml_score": 0.75,
  "ai_score": 0.85,
  "ai_confidence": 0.9,
  "detection_method": "ml_ai_ensemble",
  "recommended_action": "block",
  "fraud_signals": ["signal1", "signal2"],
  "primary_fraud_type": "bot_traffic",
  "reasoning": "Explanation...",
  "ensemble_details": {
    "method": "confidence_weighted",
    "ml_weight": 0.3,
    "ai_weight": 0.7
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Decision Logic

1. **Calculate Final Score**: Using selected ensemble method
2. **Determine Fraud**: `final_score > FRAUD_THRESHOLD`
3. **Determine Action**:
   - `block`: If fraud detected
   - `review`: If score between thresholds
   - `allow`: If score below review threshold
4. **AI Override**: If AI confidence > 0.9 and disagrees with ensemble, use AI verdict

## Detection Methods

- `ml_only`: ML score was clear (outside borderline range)
- `ml_ai_ensemble`: Combined ML and AI scores
- `ml_primary`: AI confidence was low, ML weighted more
- `ai_override`: High-confidence AI verdict overrode ensemble

## Testing

Run the test script:

```bash
python scripts/test_decision_combiner.py --output results.json
```

## Integration

The Decision Combiner can be used:

1. **Standalone**: Called directly with ML and AI results
2. **Via Orchestrator**: Orchestrator can optionally use this Lambda for combining scores
3. **Inline**: Orchestrator can combine scores inline (fallback)

To enable in Orchestrator, set environment variable:
```
DECISION_COMBINER_FUNCTION=arn:aws:lambda:region:account:function:fraudguard-decision-combiner
```

