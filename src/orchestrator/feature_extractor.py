"""
Feature Extraction for ML Model
Extracts and prepares features from ad events for XGBoost model
"""
import math
from typing import Dict, Any, List
from datetime import datetime, timezone


def calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of a string
    
    Args:
        text: Input string
        
    Returns:
        Entropy value normalized to 0-1
    """
    if not text or len(text) == 0:
        return 0.0
    
    entropy = 0
    for char in set(text):
        p = text.count(char) / len(text)
        if p > 0:
            entropy -= p * math.log2(p)
    
    # Normalize to 0-1 (assuming max entropy is 8 bits for typical strings)
    return min(entropy / 8.0, 1.0)


def is_bot_user_agent(user_agent: str) -> bool:
    """
    Check if user agent indicates a bot
    
    Args:
        user_agent: User agent string
        
    Returns:
        True if bot, False otherwise
    """
    if not user_agent:
        return False
    
    bot_keywords = [
        'bot', 'crawler', 'spider', 'scraper', 'headless',
        'phantom', 'selenium', 'webdriver', 'curl', 'wget',
        'python-requests', 'go-http-client', 'java/'
    ]
    
    user_agent_lower = user_agent.lower()
    return any(keyword in user_agent_lower for keyword in bot_keywords)


def is_datacenter_ip(ip_address: str) -> bool:
    """
    Check if IP address is from a datacenter
    
    Args:
        ip_address: IP address string
        
    Returns:
        True if datacenter IP, False otherwise
    """
    if not ip_address:
        return False
    
    # Simplified check - in production, use IP reputation service
    # Check for private IP ranges
    parts = ip_address.split('.')
    if len(parts) != 4:
        return False
    
    try:
        first_octet = int(parts[0])
        second_octet = int(parts[1])
        
        # Private IP ranges
        if first_octet == 10:
            return True
        if first_octet == 172 and 16 <= second_octet <= 31:
            return True
        if first_octet == 192 and second_octet == 168:
            return True
        
        # Common datacenter ranges (simplified)
        if first_octet == 203 and second_octet == 0:
            return True
        
    except ValueError:
        return False
    
    return False


def is_vpn_ip(ip_address: str) -> bool:
    """
    Check if IP address is from a known VPN
    
    Args:
        ip_address: IP address string
        
    Returns:
        True if VPN IP, False otherwise
    """
    if not ip_address:
        return False
    
    # Simplified check - in production, use VPN detection service
    # Common VPN ranges (simplified)
    parts = ip_address.split('.')
    if len(parts) != 4:
        return False
    
    try:
        first_octet = int(parts[0])
        second_octet = int(parts[1])
        
        # Common VPN ranges
        if first_octet == 198 and second_octet == 51:
            return True
        
    except ValueError:
        return False
    
    return False


def extract_features(event: Dict[str, Any], context_data: Dict[str, Any] = None) -> List[float]:
    """
    Extract features from event for ML model
    
    Args:
        event: Event dictionary with enriched data
        context_data: Additional context data from DynamoDB
        
    Returns:
        List of feature values in the order expected by the model
    """
    if context_data is None:
        context_data = {}
    
    # Get values from event or context
    ip_click_count_24h = event.get('ip_click_count_24h', context_data.get('ip_click_count_24h', 0))
    device_click_count_1h = event.get('device_click_count_1h', context_data.get('device_click_count_1h', 0))
    time_since_last_click = event.get('time_since_last_click', context_data.get('time_since_last_click', 0))
    
    # Temporal features
    timestamp = event.get('timestamp', int(datetime.now(timezone.utc).timestamp()))
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    hour_of_day = dt.hour
    day_of_week = dt.weekday()
    
    # User agent features
    user_agent = event.get('user_agent', '')
    ua_is_bot = is_bot_user_agent(user_agent)
    ua_entropy = calculate_entropy(user_agent)
    
    # IP features
    ip_address = event.get('ip_address', '')
    ip_is_datacenter = is_datacenter_ip(ip_address)
    ip_is_vpn = is_vpn_ip(ip_address)
    
    # Geographic features (simplified - would use geo IP service in production)
    geo_distance_km = event.get('geo_distance_km', 0.0)
    
    # Referrer features
    referrer = event.get('referrer', '')
    referrer_is_valid = bool(referrer and referrer.startswith('http'))
    
    # Behavioral features
    click_to_view_time_ms = event.get('click_to_view_time_ms', 0)
    
    # Historical features
    campaign_fraud_rate = event.get('campaign_fraud_rate', 0.0)
    publisher_quality = event.get('publisher_quality', 0.5)
    
    # Device features
    device_fingerprint_entropy = event.get('device_fingerprint_entropy', 0.5)
    is_mobile = event.get('is_mobile', False)
    is_repeated_click = event.get('is_repeated_click', False)
    
    # Conversion features
    time_to_conversion_sec = event.get('time_to_conversion_sec', 0.0)
    
    # Categorical features (encoded)
    ip_country = event.get('ip_country', 'US')
    device_os = event.get('device_os', 'Windows')
    
    # Simple encoding for categorical features
    country_codes = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE']
    os_types = ['Windows', 'macOS', 'Linux', 'iOS', 'Android']
    
    ip_country_encoded = country_codes.index(ip_country) if ip_country in country_codes else 0
    device_os_encoded = os_types.index(device_os) if device_os in os_types else 0
    
    # Return features in the order expected by the model
    # This must match the training data feature order
    features = [
        float(ip_click_count_24h),
        float(device_click_count_1h),
        float(time_since_last_click) if time_since_last_click else 0.0,
        float(hour_of_day),
        float(day_of_week),
        float(1 if ua_is_bot else 0),
        float(ua_entropy),
        float(1 if ip_is_datacenter else 0),
        float(1 if ip_is_vpn else 0),
        float(geo_distance_km),
        float(1 if referrer_is_valid else 0),
        float(click_to_view_time_ms),
        float(campaign_fraud_rate),
        float(publisher_quality),
        float(device_fingerprint_entropy),
        float(1 if is_mobile else 0),
        float(1 if is_repeated_click else 0),
        float(time_to_conversion_sec) if time_to_conversion_sec else 0.0,
        float(ip_country_encoded),
        float(device_os_encoded),
    ]
    
    return features

