# Dataset Generation Scripts

This directory contains scripts for generating synthetic fraud detection datasets.

## Generate Synthetic Dataset

### Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Generate dataset
python generate_dataset.py
```

### Output

The script generates:
- `data/full_dataset.csv` - Full dataset (100k samples)
- `data/full_dataset.parquet` - Full dataset in Parquet format
- `data/train.csv/parquet` - Training set (70k samples)
- `data/val.csv/parquet` - Validation set (15k samples)
- `data/test.csv/parquet` - Test set (15k samples)
- `data/train_features.parquet` - Training features only
- `data/train_labels.parquet` - Training labels only
- `data/val_features.parquet` - Validation features only
- `data/val_labels.parquet` - Validation labels only
- `data/test_features.parquet` - Test features only
- `data/test_labels.parquet` - Test labels only
- `data/dataset_info.json` - Dataset metadata

### Dataset Characteristics

- **Total Samples**: 100,000
- **Class Distribution**: 70% legitimate, 30% fraud
- **Train/Val/Test Split**: 70/15/15
- **Fraud Types**:
  - Bot Traffic (automated clicks)
  - Click Farm (coordinated human clicks)
  - Device Farm (multiple devices, same user)
  - Impersonation (fake user behavior)

### Features

The dataset includes all features required for ML model training:

- `ip_click_count_24h` - Clicks from IP in last 24 hours
- `device_click_count_1h` - Clicks from device in last hour
- `time_since_last_click` - Seconds since last click
- `hour_of_day` - Hour of day (0-23)
- `day_of_week` - Day of week (0-6)
- `ua_is_bot` - User agent indicates bot
- `ua_entropy` - User agent string entropy
- `ip_is_datacenter` - IP is from datacenter
- `ip_is_vpn` - IP is known VPN
- `geo_distance_km` - Geographic distance
- `referrer_is_valid` - Referrer domain is legitimate
- `click_to_view_time_ms` - Time on page before click
- `campaign_fraud_rate` - Historical fraud rate for campaign
- `publisher_quality` - Publisher quality score
- `device_fingerprint_entropy` - Device uniqueness score
- `is_mobile` - Mobile device flag
- `is_repeated_click` - Duplicate click flag
- `time_to_conversion_sec` - Time to conversion
- `ip_country` - Country code
- `device_os` - Operating system

### Verification

After generation, verify dataset integrity:

```python
import pandas as pd

# Load dataset
df = pd.read_parquet('data/full_dataset.parquet')

# Check distribution
print(f"Fraud ratio: {df['is_fraud'].mean():.2%}")
print(f"Fraud types: {df[df['is_fraud']]['fraud_type'].value_counts()}")

# Check for missing values
print(f"Missing values: {df.isnull().sum().sum()}")

# Check feature ranges
print(df.describe())
```

