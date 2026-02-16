# Firebase Timeout Fix - Testing Guide

## Problem Fixed
Backend was getting stuck for **300 seconds** when Firebase quota was exceeded, causing terrible user experience.

## Solution Summary
1. **Socket-level timeout**: Set 5s default timeout on all socket operations during Firebase init
2. **Thread timeout**: Spawn Firebase init in worker thread, timeout after 5s
3. **Quota backoff**: On timeout, activate 1-hour backoff to prevent repeated attempts
4. **Early exit**: Check quota status FIRST before any network calls

## Expected Behavior

### First Request (Quota Exceeded)
```
Request starts
→ TCP probe succeeds (2s)
→ Worker thread spawned
→ Socket timeout after 5s
→ Quota backoff activated for 1 hour
→ Returns fallback dataset
Total time: ~7 seconds ✅
```

### Subsequent Requests (During Backoff)
```
Request starts
→ Quota check: still in backoff
→ Immediately returns fallback dataset
Total time: <0.1 seconds ✅
```

### After Backoff Expires
```
Request starts
→ Quota check: backoff expired
→ Attempts Firebase connection
→ Either succeeds or triggers new backoff
```

## Configuration

Environment variables (optional):

```bash
# Maximum time to wait for Firebase init (default: 5s)
export FIREBASE_INIT_DEADLINE=5

# How long to back off after timeout/quota error (default: 3600s = 1 hour)
export FIREBASE_QUOTA_BACKOFF=3600

# Skip Firebase entirely for local testing (default: off)
export FIREBASE_FAILFAST=1
```

## Testing

### Automated Test
```bash
python test_firebase_timeout.py
```

### Manual Test (When Quota Exceeded)
1. Wait for Firebase quota to be exceeded
2. Make API request: `GET /api/predict/transactions`
3. **Expected**: Response in ~7 seconds with fallback data
4. **Before fix**: Would hang for 300 seconds

### Verify Logs
When quota exceeded, you should see:
```
ERROR: Firebase initialization timed out after 5.0s - likely quota exceeded
WARNING: Quota backoff activated until 2025-12-08T18:43:10+00:00
INFO: Serving fallback dataset transactions for uid=...
```

### Check Quota Status
```python
from db import firebase_client
status = firebase_client.get_quota_status()
print(status)
# {'quota_exceeded': True, 
#  'quota_exceeded_until': '2025-12-08T18:43:10+00:00',
#  'last_init_attempt': '2025-12-08T17:43:10+00:00',
#  'init_error': 'Firebase initialization timed out after 5.0s...'}
```

## Fallback Data

Dataset location: `datasets/Dataset.csv`
- Contains 2099+ sample transactions
- Normalized with required fields: `amount`, `date`, `user_id`, `internal_transfer`
- Tagged with `data_source="dataset"` for tracking

## Key Code Changes

1. **db/firebase_client.py**:
   - Socket timeout in `_firebase_init_worker()`: 5s
   - Thread timeout in `_init_firebase()`: 5s (configurable)
   - Quota check at function start (before any network calls)
   - Fallback dataset loader with CSV caching

2. **src/Generation/fallbacks.py**:
   - Normalized CSV reader
   - Thread-safe caching
   - Handles Hungarian number formats

3. **src/Generation/data_loader.py**:
   - Ensures required columns exist
   - Falls back to dataset when Firebase unavailable

## Troubleshooting

### Still Hangs for 300s?
Check if another part of code is calling Firebase directly:
```bash
grep -r "firebase_admin.initialize_app" .
grep -r "firestore.client()" .
```

### Fallback Data Not Loading?
Check dataset file exists:
```bash
ls -la datasets/Dataset.csv
# Should show ~2099 rows
```

### Quota Never Expires?
Manually clear quota status:
```python
from db import firebase_client
firebase_client._quota_exceeded_until = None
firebase_client._db_init_error = None
```

## Performance Impact

- **First timeout**: ~7s (vs 300s before) = **97.7% faster**
- **During backoff**: <0.1s (instant)
- **Fallback data**: 2099 transactions loaded in <100ms
- **Worker thread**: Abandoned (will be GC'd), no memory leak

## Future Improvements

1. Add retry with exponential backoff after quota expires
2. Cache Firebase credentials to avoid re-auth
3. Pre-warm fallback data on startup
4. Add health check endpoint for quota status

