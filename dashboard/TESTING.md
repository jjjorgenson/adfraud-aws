# Dashboard Testing Guide

This guide explains how to test the Fraud Analytics Dashboard locally and verify its functionality.

## Quick Start

### 1. Install Dependencies

```bash
cd dashboard
pip install -r requirements.txt
```

### 2. Run Dashboard

```bash
streamlit run app.py
```

The dashboard will start on http://localhost:8501

### 3. Access Dashboard

Open your browser and navigate to:
```
http://localhost:8501
```

## Testing Checklist

### ✅ Functionality Tests

Run the automated test script:

```bash
python test_dashboard.py
```

This validates:
- All dependencies are installed
- Mock events generation works
- Metrics calculation is correct
- Data structure handling works

### ✅ Manual Testing

1. **Real-Time Overview**
   - [ ] Total events metric displays correctly
   - [ ] Fraud rate percentage is accurate
   - [ ] Fraud type pie chart renders
   - [ ] Top fraud signals bar chart displays
   - [ ] Geographic heatmap shows countries
   - [ ] Time range selector works (1h, 24h, 7d)

2. **Campaign Analysis**
   - [ ] Campaign fraud rates table displays
   - [ ] Campaign fraud rate bar chart renders
   - [ ] Hourly click pattern line chart shows
   - [ ] Campaign summary table is accurate

3. **Event Detail View**
   - [ ] Event selector dropdown works
   - [ ] Event information displays correctly
   - [ ] Fraud analysis metrics show
   - [ ] Fraud signals badges display
   - [ ] AI explanation text appears

4. **Navigation**
   - [ ] Sidebar navigation works
   - [ ] Page switching is smooth
   - [ ] Refresh button updates data
   - [ ] Time range changes update metrics

## Test Scenarios

### Scenario 1: Mock Data (Default)

When DynamoDB is not available, the dashboard uses mock data:
- 100 mock events generated
- 30% fraud rate
- Various fraud types (bot_traffic, click_farm, device_farm)
- Multiple campaigns and countries

**Expected Behavior:**
- All charts render correctly
- Metrics are calculated accurately
- No errors in console

### Scenario 2: Real DynamoDB Data

When DynamoDB is configured:
- Events are fetched from DynamoDB
- Real-time data is displayed
- Metrics reflect actual fraud patterns

**Setup:**
```bash
export DYNAMODB_TABLE_NAME=fraudguard-events-dev
export AWS_REGION=us-east-1
```

**Expected Behavior:**
- Data loads from DynamoDB
- Metrics reflect real events
- Charts update with actual data

### Scenario 3: Empty Data

When no events are available:
- Dashboard shows zero metrics
- Charts display "No data available" messages
- No errors occur

**Expected Behavior:**
- Graceful handling of empty data
- Informative messages displayed
- Dashboard remains functional

## Performance Testing

### Load Time

The dashboard should load in <3 seconds:
- Initial page load
- Data fetching
- Chart rendering

### Refresh Performance

- Refresh button should update data quickly
- Caching should improve subsequent loads
- No noticeable lag when switching pages

## Browser Compatibility

Test in multiple browsers:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari

## Troubleshooting

### Dashboard won't start

**Error:** `ModuleNotFoundError: No module named 'streamlit'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Charts not displaying

**Error:** Charts show "No data available"

**Solution:**
- Check if mock data is being generated
- Verify DynamoDB connection if using real data
- Check browser console for errors

### Port already in use

**Error:** `Port 8501 is already in use`

**Solution:**
```bash
# Use a different port
streamlit run app.py --server.port=8502
```

### AWS credentials not found

**Error:** `Unable to locate credentials`

**Solution:**
- Configure AWS credentials: `aws configure`
- Or use mock data mode (default)

## Test Results

After running `test_dashboard.py`, you should see:

```
✅ PASS: Imports
✅ PASS: Dashboard Functions
✅ PASS: Data Structures

✅ All tests passed! Dashboard is ready to run.
```

## Next Steps

1. ✅ Run automated tests: `python test_dashboard.py`
2. ✅ Start dashboard: `streamlit run app.py`
3. ✅ Test all views manually
4. ✅ Verify charts render correctly
5. ✅ Test with real DynamoDB data (optional)
6. ✅ Deploy to AWS App Runner (Task 42)

## Known Issues

- Streamlit warnings about ScriptRunContext when running tests (can be ignored)
- Mock data uses random values (different each run)
- Geographic heatmap requires country codes in ISO-3 format

