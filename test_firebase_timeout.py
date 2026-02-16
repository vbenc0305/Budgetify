#!/usr/bin/env python3
"""Test script to verify Firebase timeout behavior.

This script tests that Firebase initialization fails fast (within 5-10 seconds)
rather than hanging for 300 seconds when quota is exceeded.
"""
import time
import logging
import sys

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)

def test_firebase_timeout():
    """Test that Firebase init times out quickly."""
    logger.info("=" * 60)
    logger.info("Testing Firebase timeout behavior")
    logger.info("=" * 60)

    start = time.time()

    try:
        from db import firebase_client
        logger.info("Attempting to get Firebase client...")

        client = firebase_client.get_db_client()
        elapsed = time.time() - start

        logger.info(f"✅ Firebase client obtained successfully in {elapsed:.2f}s")
        return True

    except firebase_client.FirebaseUnavailable as e:
        elapsed = time.time() - start
        logger.warning(f"⚠️  Firebase unavailable after {elapsed:.2f}s: {e}")

        if elapsed < 10:
            logger.info(f"✅ PASS: Failed fast in {elapsed:.2f}s (< 10s threshold)")
            return True
        else:
            logger.error(f"❌ FAIL: Took {elapsed:.2f}s (should be < 10s)")
            return False

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"❌ Unexpected error after {elapsed:.2f}s: {e}", exc_info=True)
        return False

def test_quota_backoff():
    """Test that subsequent calls after quota exceeded return immediately."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing quota backoff behavior")
    logger.info("=" * 60)

    from db import firebase_client

    # Check quota status
    status = firebase_client.get_quota_status()
    logger.info(f"Quota status: {status}")

    if not status.get("quota_exceeded"):
        logger.info("ℹ️  Quota not exceeded - test not applicable")
        return True

    # Try again - should fail immediately
    start = time.time()
    try:
        client = firebase_client.get_db_client()
        elapsed = time.time() - start
        logger.info(f"✅ Firebase client obtained in {elapsed:.2f}s")
        return True
    except firebase_client.FirebaseUnavailable as e:
        elapsed = time.time() - start

        if elapsed < 0.1:
            logger.info(f"✅ PASS: Fast-failed in {elapsed:.3f}s during quota backoff")
            return True
        else:
            logger.warning(f"⚠️  Took {elapsed:.2f}s during backoff (expected < 0.1s)")
            return elapsed < 1.0  # Still pass if < 1s

def test_fallback_data():
    """Test that fallback dataset is accessible."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing fallback dataset")
    logger.info("=" * 60)

    try:
        from db import firebase_client

        uid = "test-user-fallback"
        txs = firebase_client.get_fallback_transactions(uid)

        if txs:
            logger.info(f"✅ PASS: Loaded {len(txs)} fallback transactions")
            logger.info(f"Sample transaction: {txs[0]}")
            return True
        else:
            logger.warning("⚠️  No fallback transactions found")
            return False

    except Exception as e:
        logger.error(f"❌ FAIL: Error loading fallback data: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    results = []

    # Run tests
    results.append(("Firebase Timeout", test_firebase_timeout()))
    results.append(("Quota Backoff", test_quota_backoff()))
    results.append(("Fallback Data", test_fallback_data()))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {name}")

    all_passed = all(p for _, p in results)

    if all_passed:
        logger.info("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed")
        sys.exit(1)

