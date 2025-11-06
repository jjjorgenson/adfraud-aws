"""
Generate Synthetic Fraud Dataset
Creates a labeled dataset of 100k ad events for ML model training
"""
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Tuple
import math

# Initialize Faker
fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# Configuration
TOTAL_SAMPLES = 100000
FRAUD_RATIO = 0.3  # 30% fraud, 70% legitimate
TRAIN_RATIO = 0.7
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Fraud types
FRAUD_TYPES = ['bot_traffic', 'click_farm', 'device_farm', 'impersonation']
LEGITIMATE_TYPE = 'legitimate'

# Bot user agents
BOT_USER_AGENTS = [
    'HeadlessChrome/91.0.4472.124',
    'Mozilla/5.0 (compatible; Googlebot/2.1)',
    'python-requests/2.28.0',
    'curl/7.68.0',
    'PostmanRuntime/7.29.0',
    'Scrapy/2.6.1',
]

# Datacenter IP ranges (simplified)
DATACENTER_IPS = [
    '10.0.0.0/8',
    '172.16.0.0/12',
    '192.168.0.0/16',
]

# Known VPN IPs (simplified - using sample ranges)
VPN_IPS = [
    '203.0.113.0/24',
    '198.51.100.0/24',
]

# Countries
COUNTRIES = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE']

# Operating systems
OS_TYPES = ['Windows', 'macOS', 'Linux', 'iOS', 'Android']


def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string"""
    if not text:
        return 0.0
    entropy = 0
    for char in set(text):
        p = text.count(char) / len(text)
        entropy -= p * math.log2(p)
    return entropy / 8.0  # Normalize to 0-1


def generate_ip_address(is_datacenter: bool = False, is_vpn: bool = False) -> str:
    """Generate IP address"""
    if is_datacenter:
        return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
    elif is_vpn:
        return f"203.0.113.{random.randint(1, 254)}"
    else:
        return fake.ipv4()


def generate_user_agent(is_bot: bool = False, is_mobile: bool = False) -> str:
    """Generate user agent string"""
    if is_bot:
        return random.choice(BOT_USER_AGENTS)
    elif is_mobile:
        return fake.user_agent()
    else:
        return fake.user_agent()


def generate_legitimate_event(event_id: str, timestamp: datetime) -> Dict:
    """Generate a legitimate ad event"""
    device_id = fake.uuid4()
    campaign_id = f"campaign-{random.randint(1, 100)}"
    publisher_id = f"publisher-{random.randint(1, 50)}"
    
    # Legitimate patterns
    ip_click_count_24h = random.randint(1, 5)  # Normal: 1-5 clicks per day
    device_click_count_1h = random.randint(0, 2)  # Normal: 0-2 clicks per hour
    time_since_last_click = random.uniform(30, 300) if device_click_count_1h > 0 else None
    
    user_agent = generate_user_agent(is_bot=False, is_mobile=random.choice([True, False]))
    ua_entropy = calculate_entropy(user_agent)
    
    return {
        'event_id': event_id,
        'timestamp': int(timestamp.timestamp()),
        'event_type': random.choice(['click', 'impression', 'install', 'conversion']),
        'ip_address': generate_ip_address(is_datacenter=False, is_vpn=False),
        'user_agent': user_agent,
        'device_id': device_id,
        'campaign_id': campaign_id,
        'publisher_id': publisher_id,
        'referrer': fake.url() if random.random() > 0.2 else '',
        'click_id': fake.uuid4(),
        'hour_of_day': timestamp.hour,
        'day_of_week': timestamp.weekday(),
        'ip_click_count_24h': ip_click_count_24h,
        'device_click_count_1h': device_click_count_1h,
        'time_since_last_click': time_since_last_click if time_since_last_click else 0,
        'ua_is_bot': False,
        'ua_entropy': ua_entropy,
        'ip_is_datacenter': False,
        'ip_is_vpn': random.random() < 0.1,  # 10% VPN usage is normal
        'geo_distance_km': random.uniform(0, 50),  # Small distance
        'referrer_is_valid': random.random() > 0.1,  # 90% valid referrers
        'click_to_view_time_ms': random.randint(1000, 10000),  # Normal viewing time
        'campaign_fraud_rate': random.uniform(0.0, 0.1),  # Low fraud rate
        'publisher_quality': random.uniform(0.7, 1.0),  # High quality
        'device_fingerprint_entropy': random.uniform(0.6, 1.0),  # Unique devices
        'is_mobile': random.random() > 0.5,
        'is_repeated_click': False,
        'time_to_conversion_sec': random.uniform(60, 3600) if random.random() > 0.7 else None,
        'ip_country': random.choice(COUNTRIES),
        'device_os': random.choice(OS_TYPES),
        'is_fraud': False,
        'fraud_type': LEGITIMATE_TYPE,
    }


def generate_fraud_event(event_id: str, timestamp: datetime, fraud_type: str) -> Dict:
    """Generate a fraudulent ad event"""
    device_id = fake.uuid4()
    campaign_id = f"campaign-{random.randint(1, 100)}"
    publisher_id = f"publisher-{random.randint(1, 50)}"
    
    if fraud_type == 'bot_traffic':
        # Bot patterns
        ip_click_count_24h = random.randint(100, 1000)  # High click volume
        device_click_count_1h = random.randint(50, 200)  # Very high hourly clicks
        time_since_last_click = random.uniform(0.1, 2.0)  # Very fast clicks
        user_agent = generate_user_agent(is_bot=True, is_mobile=False)
        ua_entropy = calculate_entropy(user_agent)
        ip_is_datacenter = random.random() < 0.7
        ip_is_vpn = random.random() < 0.3
        geo_distance_km = random.uniform(100, 10000)  # Large distance
        click_to_view_time_ms = random.randint(10, 100)  # Very fast clicks
        campaign_fraud_rate = random.uniform(0.5, 0.9)  # High fraud rate
        publisher_quality = random.uniform(0.1, 0.4)  # Low quality
        device_fingerprint_entropy = random.uniform(0.1, 0.3)  # Similar devices
        is_repeated_click = random.random() < 0.3
        
    elif fraud_type == 'click_farm':
        # Click farm patterns
        ip_click_count_24h = random.randint(50, 500)
        device_click_count_1h = random.randint(20, 100)
        time_since_last_click = random.uniform(1, 10)  # Fast but not instant
        user_agent = generate_user_agent(is_bot=False, is_mobile=random.choice([True, False]))
        ua_entropy = calculate_entropy(user_agent)
        ip_is_datacenter = True  # Always datacenter
        ip_is_vpn = random.random() < 0.2
        geo_distance_km = random.uniform(50, 5000)
        click_to_view_time_ms = random.randint(50, 500)
        campaign_fraud_rate = random.uniform(0.4, 0.8)
        publisher_quality = random.uniform(0.2, 0.5)
        device_fingerprint_entropy = random.uniform(0.2, 0.5)
        is_repeated_click = random.random() < 0.5
        
    elif fraud_type == 'device_farm':
        # Device farm patterns
        ip_click_count_24h = random.randint(20, 200)
        device_click_count_1h = random.randint(10, 50)
        time_since_last_click = random.uniform(5, 30)
        user_agent = generate_user_agent(is_bot=False, is_mobile=True)
        ua_entropy = calculate_entropy(user_agent)
        ip_is_datacenter = random.random() < 0.6
        ip_is_vpn = random.random() < 0.4
        geo_distance_km = random.uniform(0, 1000)
        click_to_view_time_ms = random.randint(200, 2000)
        campaign_fraud_rate = random.uniform(0.3, 0.7)
        publisher_quality = random.uniform(0.3, 0.6)
        device_fingerprint_entropy = random.uniform(0.1, 0.4)  # Similar devices
        is_repeated_click = random.random() < 0.4
        
    else:  # impersonation
        # Impersonation patterns
        ip_click_count_24h = random.randint(10, 100)
        device_click_count_1h = random.randint(5, 20)
        time_since_last_click = random.uniform(10, 60)
        user_agent = generate_user_agent(is_bot=False, is_mobile=random.choice([True, False]))
        ua_entropy = calculate_entropy(user_agent)
        ip_is_datacenter = random.random() < 0.4
        ip_is_vpn = True  # Often uses VPN
        geo_distance_km = random.uniform(500, 5000)
        click_to_view_time_ms = random.randint(500, 5000)
        campaign_fraud_rate = random.uniform(0.2, 0.6)
        publisher_quality = random.uniform(0.4, 0.7)
        device_fingerprint_entropy = random.uniform(0.3, 0.6)
        is_repeated_click = random.random() < 0.2
    
    return {
        'event_id': event_id,
        'timestamp': int(timestamp.timestamp()),
        'event_type': random.choice(['click', 'impression', 'install', 'conversion']),
        'ip_address': generate_ip_address(is_datacenter=ip_is_datacenter, is_vpn=ip_is_vpn),
        'user_agent': user_agent,
        'device_id': device_id,
        'campaign_id': campaign_id,
        'publisher_id': publisher_id,
        'referrer': fake.url() if random.random() > 0.5 else '',
        'click_id': fake.uuid4(),
        'hour_of_day': timestamp.hour,
        'day_of_week': timestamp.weekday(),
        'ip_click_count_24h': ip_click_count_24h,
        'device_click_count_1h': device_click_count_1h,
        'time_since_last_click': time_since_last_click,
        'ua_is_bot': fraud_type == 'bot_traffic',
        'ua_entropy': ua_entropy,
        'ip_is_datacenter': ip_is_datacenter,
        'ip_is_vpn': ip_is_vpn,
        'geo_distance_km': geo_distance_km,
        'referrer_is_valid': random.random() > 0.4,  # More invalid referrers
        'click_to_view_time_ms': click_to_view_time_ms,
        'campaign_fraud_rate': campaign_fraud_rate,
        'publisher_quality': publisher_quality,
        'device_fingerprint_entropy': device_fingerprint_entropy,
        'is_mobile': random.random() > 0.3,
        'is_repeated_click': is_repeated_click,
        'time_to_conversion_sec': random.uniform(10, 300) if random.random() > 0.5 else None,
        'ip_country': random.choice(COUNTRIES),
        'device_os': random.choice(OS_TYPES),
        'is_fraud': True,
        'fraud_type': fraud_type,
    }


def generate_dataset() -> pd.DataFrame:
    """Generate the complete dataset"""
    print(f"Generating {TOTAL_SAMPLES} samples...")
    
    events = []
    start_date = datetime.now() - timedelta(days=30)
    
    num_fraud = int(TOTAL_SAMPLES * FRAUD_RATIO)
    num_legitimate = TOTAL_SAMPLES - num_fraud
    
    print(f"Generating {num_legitimate} legitimate events...")
    for i in range(num_legitimate):
        event_id = f"event-{i:06d}"
        timestamp = start_date + timedelta(seconds=random.randint(0, 30 * 24 * 60 * 60))
        event = generate_legitimate_event(event_id, timestamp)
        events.append(event)
    
    print(f"Generating {num_fraud} fraud events...")
    for i in range(num_fraud):
        event_id = f"event-{num_legitimate + i:06d}"
        timestamp = start_date + timedelta(seconds=random.randint(0, 30 * 24 * 60 * 60))
        fraud_type = random.choice(FRAUD_TYPES)
        event = generate_fraud_event(event_id, timestamp, fraud_type)
        events.append(event)
    
    # Shuffle events
    random.shuffle(events)
    
    df = pd.DataFrame(events)
    print(f"Dataset generated: {len(df)} samples")
    print(f"Fraud ratio: {df['is_fraud'].sum() / len(df):.2%}")
    print(f"Fraud type distribution:")
    print(df[df['is_fraud']]['fraud_type'].value_counts())
    
    return df


def split_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split dataset into train/val/test"""
    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    train_size = int(len(df) * TRAIN_RATIO)
    val_size = int(len(df) * VAL_RATIO)
    
    train_df = df[:train_size]
    val_df = df[train_size:train_size + val_size]
    test_df = df[train_size + val_size:]
    
    print(f"\nDataset split:")
    print(f"Train: {len(train_df)} samples ({len(train_df)/len(df):.1%})")
    print(f"Val: {len(val_df)} samples ({len(val_df)/len(df):.1%})")
    print(f"Test: {len(test_df)} samples ({len(test_df)/len(df):.1%})")
    
    return train_df, val_df, test_df


def save_dataset(df: pd.DataFrame, train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, output_dir: str = 'data'):
    """Save dataset to files"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save full dataset
    df.to_csv(f'{output_dir}/full_dataset.csv', index=False)
    df.to_parquet(f'{output_dir}/full_dataset.parquet', index=False)
    
    # Save splits
    train_df.to_csv(f'{output_dir}/train.csv', index=False)
    train_df.to_parquet(f'{output_dir}/train.parquet', index=False)
    
    val_df.to_csv(f'{output_dir}/val.csv', index=False)
    val_df.to_parquet(f'{output_dir}/val.parquet', index=False)
    
    test_df.to_csv(f'{output_dir}/test.csv', index=False)
    test_df.to_parquet(f'{output_dir}/test.parquet', index=False)
    
    # Save features and labels separately for training
    feature_columns = [col for col in df.columns if col not in ['is_fraud', 'fraud_type', 'event_id', 'timestamp']]
    
    train_features = train_df[feature_columns]
    train_labels = train_df['is_fraud'].astype(int)
    
    val_features = val_df[feature_columns]
    val_labels = val_df['is_fraud'].astype(int)
    
    test_features = test_df[feature_columns]
    test_labels = test_df['is_fraud'].astype(int)
    
    train_features.to_parquet(f'{output_dir}/train_features.parquet', index=False)
    train_labels.to_parquet(f'{output_dir}/train_labels.parquet', index=False)
    
    val_features.to_parquet(f'{output_dir}/val_features.parquet', index=False)
    val_labels.to_parquet(f'{output_dir}/val_labels.parquet', index=False)
    
    test_features.to_parquet(f'{output_dir}/test_features.parquet', index=False)
    test_labels.to_parquet(f'{output_dir}/test_labels.parquet', index=False)
    
    # Save dataset info
    info = {
        'total_samples': len(df),
        'train_samples': len(train_df),
        'val_samples': len(val_df),
        'test_samples': len(test_df),
        'fraud_ratio': float(df['is_fraud'].sum() / len(df)),
        'fraud_type_distribution': df[df['is_fraud']]['fraud_type'].value_counts().to_dict(),
        'features': feature_columns,
        'num_features': len(feature_columns),
    }
    
    with open(f'{output_dir}/dataset_info.json', 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"\nDataset saved to {output_dir}/")
    print(f"Files created:")
    print(f"  - full_dataset.csv/parquet")
    print(f"  - train.csv/parquet")
    print(f"  - val.csv/parquet")
    print(f"  - test.csv/parquet")
    print(f"  - train_features.parquet")
    print(f"  - train_labels.parquet")
    print(f"  - val_features.parquet")
    print(f"  - val_labels.parquet")
    print(f"  - test_features.parquet")
    print(f"  - test_labels.parquet")
    print(f"  - dataset_info.json")


def main():
    """Main function"""
    print("=" * 60)
    print("Synthetic Fraud Dataset Generator")
    print("=" * 60)
    
    # Generate dataset
    df = generate_dataset()
    
    # Split dataset
    train_df, val_df, test_df = split_dataset(df)
    
    # Save dataset
    save_dataset(df, train_df, val_df, test_df)
    
    # Print statistics
    print("\n" + "=" * 60)
    print("Dataset Statistics")
    print("=" * 60)
    print(f"\nTotal samples: {len(df)}")
    print(f"Fraud samples: {df['is_fraud'].sum()} ({df['is_fraud'].sum()/len(df):.1%})")
    print(f"Legitimate samples: {(~df['is_fraud']).sum()} ({(~df['is_fraud']).sum()/len(df):.1%})")
    print(f"\nFraud type distribution:")
    for fraud_type, count in df[df['is_fraud']]['fraud_type'].value_counts().items():
        print(f"  {fraud_type}: {count}")
    
    print("\nDataset generation complete!")


if __name__ == '__main__':
    main()

