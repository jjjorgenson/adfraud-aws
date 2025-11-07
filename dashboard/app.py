"""
Fraud Analytics Dashboard
Streamlit-based web dashboard for monitoring real-time fraud metrics
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import boto3
from typing import Dict, Any, List, Optional
import json
import os

# Page configuration
st.set_page_config(
    page_title="FraudGuard AI Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize AWS clients
@st.cache_resource
def get_dynamodb_client():
    """Get DynamoDB client"""
    return boto3.resource('dynamodb', region_name='us-east-1')

@st.cache_resource
def get_s3_client():
    """Get S3 client"""
    return boto3.client('s3', region_name='us-east-1')

# Configuration
# Default table name matches SAM template output
# Can be overridden via environment variable DYNAMODB_TABLE_NAME
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'fraudguard-events-dev')
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', '')

# Initialize clients
dynamodb = get_dynamodb_client()
s3 = get_s3_client()
table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None


def get_recent_events(hours: int = 24) -> List[Dict[str, Any]]:
    """
    Get recent events from DynamoDB
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        List of event dictionaries
    """
    if not table:
        # Return mock data for development
        return get_mock_events(hours)
    
    try:
        # Verify table exists by checking its status
        table.load()
    except Exception as e:
        # Table doesn't exist or can't be accessed
        st.warning(f"⚠️ DynamoDB table '{TABLE_NAME}' not found. Using mock data for demonstration.")
        st.info(f"💡 To use real data, ensure the table exists in AWS. Error: {str(e)}")
        return get_mock_events(hours)
    
    try:
        # Calculate timestamp threshold
        threshold = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
        
        # Scan table for recent events
        # Note: 'timestamp' is a reserved keyword in DynamoDB, so we use ExpressionAttributeNames
        response = table.scan(
            FilterExpression='#ts >= :threshold',
            ExpressionAttributeNames={'#ts': 'timestamp'},
            ExpressionAttributeValues={':threshold': threshold}
        )
        
        items = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression='#ts >= :threshold',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={':threshold': threshold},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
        
        if not items:
            st.info(f"ℹ️ No events found in the last {hours} hours. Using mock data for demonstration.")
            return get_mock_events(hours)
        
        return items
    except Exception as e:
        st.error(f"Error fetching events: {str(e)}")
        st.info("Using mock data for demonstration.")
        return get_mock_events(hours)


def generate_mock_reasoning(is_fraud: bool, campaign_id: str, ip_address: str, fraud_type: str = 'unknown') -> str:
    """Generate detailed mock AI reasoning"""
    if not is_fraud:
        return f"This event shows legitimate traffic patterns from IP {ip_address} in campaign {campaign_id}. Normal user behavior detected with consistent click patterns, valid user agent, and expected geographic location. No suspicious activity identified."

    fraud_types = {
        'bot_traffic': f"This event exhibits clear bot traffic patterns. The IP address {ip_address} shows automated behavior with non-human click patterns. The user agent string indicates a bot framework, and the click velocity exceeds normal human interaction rates. Campaign {campaign_id} has been flagged for review due to high bot activity.",
        'click_farm': f"Click farm activity detected from IP {ip_address} in campaign {campaign_id}. Multiple rapid clicks from the same source with identical patterns suggest coordinated fraudulent activity. The geographic location and timing patterns are consistent with known click farm operations. Immediate action recommended.",
        'device_farm': f"Device farm indicators present. IP {ip_address} shows multiple device IDs with identical behavioral patterns, suggesting device spoofing. Campaign {campaign_id} is experiencing coordinated fraud attempts. The device fingerprinting reveals anomalies consistent with farm operations.",
        'click_injection': f"Click injection fraud detected from IP {ip_address} in campaign {campaign_id}. A malicious app on the device monitored for new app installations and injected a fake click just before the install completed (<1 second timing). This pattern indicates install broadcast monitoring, where the fraudster steals attribution credit for legitimate app installs. The click-to-install time of less than 1 second is highly suspicious and characteristic of click injection attacks. Immediate blocking recommended.",
        'incentivized_clicks': f"Incentivized click fraud detected from IP {ip_address} in campaign {campaign_id}. This event shows a pattern of high click volume with extremely low or zero conversion rate, indicating users are clicking ads for rewards rather than genuine interest. The engagement score is very low, suggesting users are not actually engaging with the content after clicking. This is characteristic of incentivized traffic where users are paid or rewarded to click ads. Immediate review recommended.",
        'competitor_clicking': f"Competitor clicking fraud detected from IP {ip_address} in campaign {campaign_id}. The IP address matches known competitor ranges or business/office networks, and shows a pattern of high click volume with zero conversions. This suggests a competitor is clicking ads to drain the ad budget without generating any legitimate value. The timing patterns and geographic location further support this conclusion. Immediate blocking recommended.",
        'proxy_fraud': f"Proxy/fake click fraud detected from IP {ip_address} in campaign {campaign_id}. The IP address is from a proxy server (beyond VPN), and shows low engagement scores with no conversions. This pattern indicates fake clicks generated through proxy servers to mask the real source. The combination of proxy IP, low engagement, and zero conversions is highly suspicious. Immediate blocking recommended."
    }

    return fraud_types.get(fraud_type, f"Fraudulent activity detected from IP {ip_address} in campaign {campaign_id}. Multiple suspicious indicators suggest this is not legitimate traffic.")


def get_mock_events(hours: int = 24) -> List[Dict[str, Any]]:
    """Generate mock events for development"""
    import random
    try:
        from faker import Faker
        fake = Faker()
    except ImportError:
        # Fallback if faker not available
        fake = None
    events = []
    now = datetime.now(timezone.utc)
    
    fraud_types = ['bot_traffic', 'click_farm', 'device_farm', 'click_injection', 'incentivized_clicks', 'competitor_clicking', 'proxy_fraud']
    
    for i in range(100):
        is_fraud = random.random() < 0.3  # 30% fraud rate
        campaign_id = f'campaign-{random.randint(1, 10)}'
        ip_address = fake.ipv4() if fake else f'192.168.{random.randint(1, 255)}.{random.randint(1, 255)}'
        primary_fraud_type = random.choice(fraud_types) if is_fraud else 'legitimate'
        
        # Generate fraud-specific data
        click_to_install_time = None
        conversion_rate = None
        engagement_score = None
        ip_is_proxy = False
        ip_is_business = False
        ip_is_competitor = False
        
        if primary_fraud_type == 'click_injection':
            # Click injection: <1 second is highly suspicious
            click_to_install_time = random.uniform(0.1, 0.9)  # <1 second
        elif primary_fraud_type == 'incentivized_clicks':
            # Incentivized clicks: very low conversion rate, low engagement
            conversion_rate = random.uniform(0.0, 0.001)  # <0.1% conversion rate
            engagement_score = random.uniform(0.0, 0.3)  # Low engagement
        elif primary_fraud_type == 'competitor_clicking':
            # Competitor clicking: zero conversions, business IP
            conversion_rate = 0.0  # Zero conversions
            ip_is_business = True
            ip_is_competitor = random.random() < 0.5  # 50% chance of known competitor IP
        elif primary_fraud_type == 'proxy_fraud':
            # Proxy fraud: proxy IP, low engagement, no conversions
            ip_is_proxy = True
            engagement_score = random.uniform(0.0, 0.3)  # Low engagement
            conversion_rate = 0.0  # No conversions
        elif is_fraud and random.random() < 0.2:  # 20% chance of having install data for other fraud types
            click_to_install_time = random.uniform(30, 300)  # Normal range
        
        event = {
            'event_id': f'event-{i}',
            'timestamp': int((now - timedelta(minutes=random.randint(0, hours*60))).timestamp()),
            'is_fraud': is_fraud,
            'fraud_score': random.uniform(0.7, 0.95) if is_fraud else random.uniform(0.1, 0.4),
            'campaign_id': campaign_id,
            'publisher_id': f'publisher-{random.randint(1, 5)}',
            'ip_address': ip_address,
            'ip_country': fake.country_code() if fake else random.choice(['US', 'GB', 'CA', 'DE', 'FR']),
            'primary_fraud_type': primary_fraud_type,
            'fraud_signals': random.sample(['bot_user_agent', 'high_click_velocity', 'datacenter_ip', 'suspicious_timing'], k=random.randint(1, 3)) if is_fraud else [],
            'reasoning': generate_mock_reasoning(is_fraud, campaign_id, ip_address, primary_fraud_type)
        }
        
        # Add fraud-specific fields
        if click_to_install_time is not None:
            event['click_to_install_time_sec'] = click_to_install_time
            event['has_recent_install'] = True
            event['install_broadcast_detected'] = click_to_install_time < 1.0
            event['click_injection_risk_score'] = 0.95 if click_to_install_time < 1.0 else 0.3
            event['is_mobile'] = True  # Click injection is mobile-only
        
        if conversion_rate is not None:
            event['conversion_rate'] = conversion_rate
            event['clicks_count'] = random.randint(10, 100) if primary_fraud_type == 'incentivized_clicks' else random.randint(1, 10)
            event['conversions_count'] = int(event['clicks_count'] * conversion_rate)
        
        if engagement_score is not None:
            event['engagement_score'] = engagement_score
        
        if ip_is_proxy:
            event['ip_is_proxy'] = True
        
        if ip_is_business:
            event['ip_is_business'] = True
        
        if ip_is_competitor:
            event['ip_is_competitor'] = True
        
        events.append(event)
    
    return events


def calculate_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate dashboard metrics from events"""
    if not events:
        return {
            'total_events': 0,
            'fraud_count': 0,
            'fraud_rate': 0.0,
            'legitimate_count': 0,
            'fraud_by_type': {},
            'top_signals': {},
            'fraud_by_campaign': {},
            'fraud_by_country': {}
        }
    
    df = pd.DataFrame(events)
    
    # Parse honeypot field (convert to boolean)
    if 'honeypot' in df.columns:
        df['honeypot'] = df['honeypot'].apply(lambda x: True if x is True or x == True or str(x).lower() == 'true' else False)
    
    # Basic metrics
    total_events = len(df)
    fraud_count = df['is_fraud'].sum() if 'is_fraud' in df.columns else 0
    fraud_rate = (fraud_count / total_events * 100) if total_events > 0 else 0.0
    
    # Fraud by type
    fraud_by_type = {}
    if 'primary_fraud_type' in df.columns:
        fraud_df = df[df['is_fraud'] == True] if 'is_fraud' in df.columns else df
        fraud_by_type = fraud_df['primary_fraud_type'].value_counts().to_dict()
    
    # Top fraud signals
    top_signals = {}
    if 'fraud_signals' in df.columns:
        all_signals = []
        for signals in df['fraud_signals'].dropna():
            if isinstance(signals, list):
                all_signals.extend(signals)
        if all_signals:
            top_signals = pd.Series(all_signals).value_counts().head(10).to_dict()
    
    # Fraud by campaign
    fraud_by_campaign = {}
    if 'campaign_id' in df.columns and 'is_fraud' in df.columns:
        campaign_fraud = df.groupby('campaign_id').agg({
            'is_fraud': ['sum', 'count']
        }).reset_index()
        campaign_fraud.columns = ['campaign_id', 'fraud_count', 'total_count']
        campaign_fraud['fraud_rate'] = (campaign_fraud['fraud_count'] / campaign_fraud['total_count'] * 100).round(2)
        fraud_by_campaign = campaign_fraud.set_index('campaign_id')['fraud_rate'].to_dict()
    
    # Fraud by country
    fraud_by_country = {}
    if 'ip_country' in df.columns and 'is_fraud' in df.columns:
        country_fraud = df.groupby('ip_country').agg({
            'is_fraud': ['sum', 'count']
        }).reset_index()
        country_fraud.columns = ['country', 'fraud_count', 'total_count']
        country_fraud['fraud_rate'] = (country_fraud['fraud_count'] / country_fraud['total_count'] * 100).round(2)
        fraud_by_country = country_fraud.set_index('country')['fraud_rate'].to_dict()
    
    return {
        'total_events': total_events,
        'fraud_count': int(fraud_count),
        'fraud_rate': round(fraud_rate, 2),
        'legitimate_count': int(total_events - fraud_count),
        'fraud_by_type': fraud_by_type,
        'top_signals': top_signals,
        'fraud_by_campaign': fraud_by_campaign,
        'fraud_by_country': fraud_by_country
    }


def render_real_time_overview(events: List[Dict[str, Any]], metrics: Dict[str, Any]):
    """Render real-time overview dashboard"""
    st.header("📊 Real-Time Overview")
    
    # Filter honeypot events
    honeypot_events = [e for e in events if e.get('honeypot') == True]
    regular_events = [e for e in events if not e.get('honeypot')]
    
    # Show honeypot stats if available
    if honeypot_events:
        honeypot_metrics = calculate_metrics(honeypot_events)
        with st.expander("🍯 Honeypot Events", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Honeypot Events", len(honeypot_events))
            with col2:
                st.metric("Honeypot Fraud", honeypot_metrics['fraud_count'], delta=f"{honeypot_metrics['fraud_rate']:.1f}%")
            with col3:
                st.metric("Honeypot Legitimate", honeypot_metrics['legitimate_count'])
            with col4:
                st.metric("Honeypot Fraud Rate", f"{honeypot_metrics['fraud_rate']:.2f}%")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events (24h)", metrics['total_events'])
    
    with col2:
        st.metric("Fraud Detected", metrics['fraud_count'], delta=f"{metrics['fraud_rate']:.1f}%")
    
    with col3:
        st.metric("Legitimate", metrics['legitimate_count'])
    
    with col4:
        st.metric("Fraud Rate", f"{metrics['fraud_rate']:.2f}%")
    
    st.divider()
    
    # Charts row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Fraud by Type")
        if metrics['fraud_by_type']:
            fig = px.pie(
                values=list(metrics['fraud_by_type'].values()),
                names=list(metrics['fraud_by_type'].keys()),
                title="Fraud Type Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fraud data available")
    
    with col2:
        st.subheader("Top Fraud Signals")
        if metrics['top_signals']:
            signals_df = pd.DataFrame({
                'Signal': list(metrics['top_signals'].keys()),
                'Count': list(metrics['top_signals'].values())
            })
            fig = px.bar(
                signals_df,
                x='Count',
                y='Signal',
                orientation='h',
                title="Most Common Fraud Signals"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fraud signals available")
    
    # Geographic heatmap
    st.subheader("🌍 Geographic Fraud Distribution")
    if metrics['fraud_by_country']:
        country_df = pd.DataFrame({
            'Country': list(metrics['fraud_by_country'].keys()),
            'Fraud Rate (%)': list(metrics['fraud_by_country'].values())
        })
        
        # Create choropleth map
        fig = px.choropleth(
            country_df,
            locations='Country',
            locationmode='ISO-3',
            color='Fraud Rate (%)',
            title="Fraud Rate by Country",
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No geographic data available")
    
    # Honeypot events breakdown
    if honeypot_events:
        st.divider()
        st.subheader("🍯 Honeypot Events Breakdown")
        honeypot_df = pd.DataFrame(honeypot_events)
        
        col1, col2 = st.columns(2)
        with col1:
            if 'button_id' in honeypot_df.columns:
                button_counts = honeypot_df['button_id'].value_counts()
                if not button_counts.empty:
                    st.write("**Clicks by Button:**")
                    for button, count in button_counts.items():
                        st.write(f"  • {button}: {count}")
        
        with col2:
            if 'view_time_ms' in honeypot_df.columns:
                avg_view_time = honeypot_df['view_time_ms'].mean()
                st.metric("Average View Time", f"{avg_view_time:.0f} ms")
        
        # Show honeypot event types
        if 'event_type' in honeypot_df.columns:
            event_type_counts = honeypot_df['event_type'].value_counts()
            if not event_type_counts.empty:
                st.write("**Event Types:**")
                for event_type, count in event_type_counts.items():
                    st.write(f"  • {event_type}: {count}")


def render_campaign_analysis(events: List[Dict[str, Any]], metrics: Dict[str, Any]):
    """Render campaign analysis view"""
    st.header("📈 Campaign Analysis")
    
    if not metrics['fraud_by_campaign']:
        st.info("No campaign data available")
        return
    
    # Campaign fraud rates
    campaign_df = pd.DataFrame({
        'Campaign': list(metrics['fraud_by_campaign'].keys()),
        'Fraud Rate (%)': list(metrics['fraud_by_campaign'].values())
    }).sort_values('Fraud Rate (%)', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Fraud Rate by Campaign")
        fig = px.bar(
            campaign_df,
            x='Campaign',
            y='Fraud Rate (%)',
            title="Campaign Fraud Rates"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Campaign Summary")
        st.dataframe(campaign_df, use_container_width=True)
    
    # Time series for selected campaign
    st.subheader("📊 Click Pattern Analysis")
    if events:
        events_df = pd.DataFrame(events)
        if 'campaign_id' in events_df.columns and 'timestamp' in events_df.columns:
            # Convert timestamp to datetime
            events_df['datetime'] = pd.to_datetime(events_df['timestamp'], unit='s')
            events_df['hour'] = events_df['datetime'].dt.hour
            
            # Hourly click pattern
            hourly_clicks = events_df.groupby('hour').size().reset_index(name='clicks')
            fig = px.line(
                hourly_clicks,
                x='hour',
                y='clicks',
                title="Hourly Click Pattern (Last 24h)",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)


def render_event_detail(events: List[Dict[str, Any]]):
    """Render event detail view"""
    st.header("🔍 Event Detail View")
    
    if not events:
        st.info("No events available")
        return
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        show_honeypot = st.checkbox("Show Honeypot Events", value=True)
    with col2:
        show_regular = st.checkbox("Show Regular Events", value=True)
    
    # Filter events based on checkboxes
    filtered_events = []
    if show_honeypot:
        filtered_events.extend([e for e in events if e.get('honeypot') == True])
    if show_regular:
        filtered_events.extend([e for e in events if not e.get('honeypot')])
    
    if not filtered_events:
        st.info("No events match the selected filters")
        return
    
    events = filtered_events
    
    # Event selector
    event_ids = [e.get('event_id', 'unknown') for e in events]
    selected_event_id = st.selectbox("Select Event", event_ids)
    
    # Find selected event
    selected_event = next((e for e in events if e.get('event_id') == selected_event_id), None)
    
    if not selected_event:
        st.error("Event not found")
        return
    
    # Display event details
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Event Information")
        st.json({
            'Event ID': selected_event.get('event_id'),
            'Timestamp': datetime.fromtimestamp(selected_event.get('timestamp', 0), tz=timezone.utc).isoformat(),
            'Campaign ID': selected_event.get('campaign_id'),
            'Publisher ID': selected_event.get('publisher_id'),
            'IP Address': selected_event.get('ip_address'),
            'Country': selected_event.get('ip_country')
        })
    
    with col2:
        st.subheader("Fraud Analysis")
        is_fraud = selected_event.get('is_fraud', False)
        fraud_score = selected_event.get('fraud_score', 0.0)
        
        st.metric("Fraud Status", "🚨 Fraud Detected" if is_fraud else "✅ Legitimate")
        st.metric("Fraud Score", f"{fraud_score:.4f}")
        st.metric("Fraud Type", selected_event.get('primary_fraud_type', 'unknown'))
    
    # Fraud signals
    if selected_event.get('fraud_signals'):
        st.subheader("Fraud Signals")
        signals = selected_event['fraud_signals']
        if isinstance(signals, list):
            # Display badges in a row
            badge_cols = st.columns(min(len(signals), 5))  # Max 5 columns
            for idx, signal in enumerate(signals):
                with badge_cols[idx % len(badge_cols)]:
                    st.markdown(
                        f'<span style="background-color: #ff4444; color: white; padding: 4px 8px; '
                        f'border-radius: 4px; font-size: 0.9em; font-weight: bold;">🚨 {signal}</span>',
                        unsafe_allow_html=True
                    )
        else:
            st.text(signals)
    
    # AI Explanation
    if selected_event.get('reasoning'):
        st.subheader("🤖 AI Explanation")
        st.info(selected_event['reasoning'])


def main():
    """Main dashboard function"""
    # Sidebar
    with st.sidebar:
        st.title("🛡️ FraudGuard AI")
        st.markdown("---")
        
        # Time range selector
        time_range = st.selectbox(
            "Time Range",
            ["Last Hour", "Last 24 Hours", "Last 7 Days"],
            index=1
        )
        
        hours_map = {
            "Last Hour": 1,
            "Last 24 Hours": 24,
            "Last 7 Days": 168
        }
        hours = hours_map[time_range]
        
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Navigation")
        page = st.radio(
            "Select View",
            ["Real-Time Overview", "Campaign Analysis", "Event Detail"],
            index=0
        )
    
    # Load data
    with st.spinner("Loading events..."):
        events = get_recent_events(hours)
        metrics = calculate_metrics(events)
    
    # Render selected page
    if page == "Real-Time Overview":
        render_real_time_overview(events, metrics)
    elif page == "Campaign Analysis":
        render_campaign_analysis(events, metrics)
    elif page == "Event Detail":
        render_event_detail(events)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>FraudGuard AI Dashboard | "
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

# Test deployment trigger
