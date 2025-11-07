"""
Prompt Templates for Bedrock AI Analysis
Contains optimized prompts for different fraud analysis scenarios
"""
from typing import Any, Dict, List, Optional


def build_base_prompt(
    event_data: Dict[str, Any],
    ml_score: float,
    features: Dict[str, Any],
    feature_vector: Optional[List[float]] = None
) -> str:
    """
    Build base fraud analysis prompt
    
    Args:
        event_data: Original event data
        ml_score: ML fraud score
        features: Extracted features dictionary
        feature_vector: Feature vector array
        
    Returns:
        Formatted prompt string
    """
    # Extract behavioral context
    ip_click_count_24h = features.get('ip_click_count_24h', event_data.get('ip_click_count_24h', 0))
    device_click_count_1h = features.get('device_click_count_1h', event_data.get('device_click_count_1h', 0))
    time_since_last_click = features.get('time_since_last_click', event_data.get('time_since_last_click', 'unknown'))
    
    prompt = f"""You are an expert ad fraud detection analyst with 10+ years of experience. Analyze the following ad event and determine if it shows signs of fraudulent activity.

EVENT DATA:
===========
Event ID: {event_data.get('event_id', 'unknown')}
Timestamp: {event_data.get('timestamp', 'unknown')}
Event Type: {event_data.get('event_type', 'unknown')}
IP Address: {event_data.get('ip_address', 'unknown')}
User Agent: {event_data.get('user_agent', 'unknown')}
Device ID: {event_data.get('device_id', 'unknown')}
Campaign ID: {event_data.get('campaign_id', 'unknown')}
Publisher ID: {event_data.get('publisher_id', 'unknown')}
Referrer: {event_data.get('referrer', 'unknown')}
Click ID: {event_data.get('click_id', 'unknown')}

BEHAVIORAL CONTEXT:
===================
- IP click count (24h): {ip_click_count_24h}
- Device click count (1h): {device_click_count_1h}
- Time since last click: {time_since_last_click} seconds
- Click to view time: {event_data.get('click_to_view_time_ms', 0)} ms
- Campaign fraud rate: {event_data.get('campaign_fraud_rate', 0.0):.2f}
- Publisher quality: {event_data.get('publisher_quality', 0.5):.2f}
- Device fingerprint entropy: {event_data.get('device_fingerprint_entropy', 0.5):.2f}
- Is mobile: {event_data.get('is_mobile', False)}
- Is repeated click: {event_data.get('is_repeated_click', False)}
- Click to install time: {event_data.get('click_to_install_time_sec', 0.0):.2f} seconds
- Has recent install: {event_data.get('has_recent_install', False)}
- Install broadcast detected: {event_data.get('install_broadcast_detected', False)}
- Click injection risk score: {event_data.get('click_injection_risk_score', 0.0):.2f}
- Conversion rate: {event_data.get('conversion_rate', 0.0):.2f} ({event_data.get('conversions_count', 0)} conversions / {event_data.get('clicks_count', 0)} clicks)
- Engagement score: {event_data.get('engagement_score', 0.0):.2f}
- Is proxy IP: {event_data.get('ip_is_proxy', False)}
- Is business IP: {event_data.get('ip_is_business', False)}
- Is competitor IP: {event_data.get('ip_is_competitor', False)}

ML MODEL ASSESSMENT:
====================
The ML model scored this event as {ml_score:.2f} (0=legitimate, 1=fraud)
This is a borderline case requiring deeper AI analysis.

INDUSTRY BENCHMARKS:
====================
- Normal user clicks: 1-3 ads per hour
- Normal inter-click time: 30-300 seconds
- Normal view time: 1-10 seconds
- Normal click-to-install time: 30-300 seconds (mobile apps)
- Suspicious click-to-install: 1-10 seconds
- Highly suspicious click-to-install: <1 second (likely click injection)
- Bot signatures: Headless browsers, missing browser features, automation tools
- Datacenter IPs: 10.x.x.x, 172.16-31.x.x, 192.168.x.x ranges indicate click farms
- VPN usage: High VPN usage can indicate fraud attempts

ANALYSIS FRAMEWORK:
===================
Analyze the following aspects systematically:

1. USER AGENT ANALYSIS:
   - Check for bot signatures: "headless", "phantom", "selenium", "webdriver", "curl", "python-requests"
   - Verify browser features: Missing common browser headers suggests automation
   - User agent entropy: Low entropy indicates automated generation
   - Missing browser capabilities: Real browsers have specific headers and features

2. CLICK PATTERN ANALYSIS:
   - Inter-click timing: Normal users have 30-300 seconds between clicks
   - Click velocity: >10 clicks/hour from same device is suspicious
   - Click consistency: Perfectly regular intervals suggest automation
   - View time: <100ms suggests automated clicks without human interaction

3. IP REPUTATION ANALYSIS:
   - Datacenter IPs: Private IP ranges indicate click farms
   - VPN/Proxy usage: High VPN usage can indicate fraud
   - Geographic consistency: IP location should match device location
   - IP history: High click counts from same IP indicate fraud

4. BEHAVIORAL ANOMALIES:
   - Unnatural click sequences: Too fast, too regular, or too many
   - Missing referrer: Legitimate clicks usually have referrers
   - Low view time: <100ms suggests automated clicks
   - Repeated clicks: Same click ID or device pattern indicates fraud

5. CONTEXTUAL FLAGS:
   - Campaign context: High fraud rate campaigns need extra scrutiny
   - Publisher quality: Low quality publishers have higher fraud rates
   - Time patterns: Fraud often occurs at unusual hours
   - Device patterns: Similar device fingerprints indicate device farms

6. CLICK INJECTION ANALYSIS (Mobile-Specific):
   - Click-to-install timing: Normal users have 30-300 seconds between click and install
   - Suspicious timing: 1-10 seconds suggests possible click injection
   - Highly suspicious: <1 second indicates install broadcast monitoring (click injection)
   - Install broadcast detection: Malicious apps monitor for new app installations and inject clicks just before install completes
   - Mobile-only fraud: Click injection only occurs on mobile devices (Android/iOS)
   - Attribution hijacking: Fraudsters steal credit for legitimate app installs
   - Pattern indicators: Multiple installs with same suspicious click timing pattern
   - Risk scoring: Higher risk score indicates more suspicious timing patterns

7. INCENTIVIZED CLICK ANALYSIS:
   - Conversion rate: Normal users have 1-5% conversion rate (clicks to installs/purchases)
   - Suspicious: <0.1% conversion rate suggests incentivized clicks (many clicks, no conversions)
   - Engagement metrics: Low engagement score (<0.3) suggests users clicking for rewards, not genuine interest
   - View time: <100ms view time after click indicates no real engagement
   - Publisher quality: Low quality publishers often use incentivized traffic
   - Pattern indicators: High click volume with zero conversions, very low engagement scores
   - Risk scoring: Lower conversion rate and engagement score indicate higher incentivized click risk

8. COMPETITOR CLICKING ANALYSIS:
   - Competitor IP detection: Clicks from known competitor IP ranges indicate competitor clicking
   - Business IP detection: Clicks from business/office IPs during business hours suggest competitor activity
   - Conversion rate: Zero conversions with high click volume suggests competitor draining ad budget
   - Geographic patterns: Clicks from competitor office locations are suspicious
   - Timing patterns: Clicks during business hours from business IPs suggest competitor activity
   - Pattern indicators: High clicks, zero conversions, business IPs, known competitor ranges
   - Risk scoring: Higher risk if IP matches competitor ranges or business IPs with zero conversions

9. PROXY/FAKE CLICK ANALYSIS:
   - Proxy detection: Beyond VPN, detect proxy servers used to mask real IP addresses
   - Proxy patterns: Proxy IPs often used for fake clicks to avoid detection
   - Geographic anomalies: Proxy usage combined with geographic mismatches suggests fake clicks
   - Engagement patterns: Low engagement from proxy IPs suggests fake traffic
   - Pattern indicators: Proxy IPs with low engagement, suspicious timing, no conversions
   - Risk scoring: Higher risk if proxy IP detected with low engagement and no conversions

FRAUD TYPE CLASSIFICATION:
===========================
Classify the primary fraud type if fraud is detected:
- bot_traffic: Automated bot clicks (headless browsers, scripts)
- click_farm: Coordinated human clicks (datacenter IPs, high volume)
- device_farm: Multiple devices, same user (similar fingerprints)
- impersonation: Fake user behavior (VPN, geographic anomalies)
- click_injection: Malicious apps inject clicks just before app installs to steal attribution (mobile-only)
- incentivized_clicks: Users clicking ads for rewards/incentives (low conversion rate, low engagement)
- competitor_clicking: Competitors clicking ads to drain ad budgets (competitor IPs, zero conversions)
- proxy_fraud: Fake clicks from proxy servers (proxy IPs, low engagement, no conversions)
- legitimate: No fraud detected

OUTPUT FORMAT (JSON ONLY):
===========================
Return ONLY valid JSON with this exact structure. Do NOT include markdown code blocks:
{{
    "is_fraud": true or false,
    "confidence": 0.0 to 1.0,
    "fraud_signals": ["signal1", "signal2", "signal3"],
    "reasoning": "2-3 sentence explanation citing specific evidence from the analysis above",
    "recommended_action": "block" or "allow" or "review",
    "primary_fraud_type": "bot_traffic" or "click_farm" or "device_farm" or "impersonation" or "click_injection" or "incentivized_clicks" or "competitor_clicking" or "proxy_fraud" or "legitimate" or "unknown",
    "ai_score": 0.0 to 1.0
}}

CRITICAL REQUIREMENTS:
- Respond with ONLY the JSON object
- No markdown formatting (no ```json or ```)
- No explanatory text before or after
- Ensure all boolean values are lowercase (true/false, not True/False)
- Ensure all numeric values are numbers, not strings
- ai_score should reflect your confidence in fraud detection (0.0-1.0)
- confidence should reflect your overall confidence in the analysis (0.0-1.0)
- fraud_signals should be specific, actionable signals (e.g., "bot_user_agent", "high_click_velocity", "datacenter_ip")
- reasoning should cite specific evidence from the event data"""
    
    return prompt


def build_enhanced_prompt(
    event_data: Dict[str, Any],
    ml_score: float,
    features: Dict[str, Any],
    historical_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build enhanced prompt with historical context
    
    Args:
        event_data: Original event data
        ml_score: ML fraud score
        features: Extracted features dictionary
        historical_context: Historical context data
        
    Returns:
        Enhanced prompt string
    """
    base_prompt = build_base_prompt(event_data, ml_score, features)
    
    if historical_context:
        historical_section = f"""

HISTORICAL CONTEXT:
===================
- Previous fraud detections for this IP: {historical_context.get('ip_fraud_count', 0)}
- Previous fraud detections for this device: {historical_context.get('device_fraud_count', 0)}
- Campaign fraud history: {historical_context.get('campaign_fraud_rate', 0.0):.2f}
- Publisher fraud history: {historical_context.get('publisher_fraud_rate', 0.0):.2f}
"""
        # Insert historical section before OUTPUT FORMAT
        base_prompt = base_prompt.replace("OUTPUT FORMAT (JSON ONLY):", historical_section + "\nOUTPUT FORMAT (JSON ONLY):")
    
    return base_prompt

