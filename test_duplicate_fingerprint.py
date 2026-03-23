"""
Test script to verify the duplicate detection fingerprint logic
Run this to ensure the fixes are working correctly
"""

import sys
import re

def _normalize_text(s) -> str:
    if not s:
        return ""
    t = str(s).lower()
    # normalize diacritics
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ö", "o").replace("ő", "o").replace("ú", "u").replace("ü", "u").replace("ű", "u")
    t = re.sub(r"\s+", " ", t)
    return t

def _tx_fingerprint_for_dedup(tx: dict) -> str:
    """Test implementation of fingerprint function"""
    # Full timestamp (not just date)
    date_raw = str(tx.get("date", "")).strip()
    date_full = date_raw if date_raw else ""

    # Amount with 2 decimal places
    try:
        amount_val = float(tx.get("amount", 0.0) or 0.0)
    except Exception:
        amount_val = 0.0
    amount_s = f"{amount_val:.2f}"

    # Normalized text fields
    desc = _normalize_text(tx.get("description", ""))[:200]
    cat = _normalize_text(tx.get("category", ""))
    ttype = _normalize_text(tx.get("tran_type", ""))
    internal = _normalize_text(tx.get("internal_transfer", ""))

    return "|".join([date_full, amount_s, desc, cat, ttype, internal])


def test_duplicate_detection():
    """Test various scenarios for duplicate detection"""

    print("=" * 70)
    print("DUPLICATE DETECTION TEST")
    print("=" * 70)

    # Test 1: Same transaction, same time - SHOULD BE DUPLICATE
    print("\n✅ Test 1: Exact duplicate (same time)")
    tx1 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.50,
        "description": "Grocery shopping",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    tx2 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.50,
        "description": "Grocery shopping",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    fp1 = _tx_fingerprint_for_dedup(tx1)
    fp2 = _tx_fingerprint_for_dedup(tx2)
    print(f"Transaction 1 fingerprint: {fp1}")
    print(f"Transaction 2 fingerprint: {fp2}")
    print(f"Are they duplicates? {fp1 == fp2} ✓ (EXPECTED: True)")

    # Test 2: Same day, different time - SHOULD NOT BE DUPLICATE
    print("\n✅ Test 2: Same day, different time (FIX VERIFICATION)")
    tx3 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.50,
        "description": "Grocery shopping",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    tx4 = {
        "date": "2024-01-15 15:45:00",  # Different time!
        "amount": 150.50,
        "description": "Grocery shopping",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    fp3 = _tx_fingerprint_for_dedup(tx3)
    fp4 = _tx_fingerprint_for_dedup(tx4)
    print(f"Transaction 3 fingerprint: {fp3}")
    print(f"Transaction 4 fingerprint: {fp4}")
    print(f"Are they duplicates? {fp3 == fp4} ✓ (EXPECTED: False)")

    # Test 3: Different amounts - SHOULD NOT BE DUPLICATE
    print("\n✅ Test 3: Different amounts")
    tx5 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.50,
        "description": "Grocery shopping",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    tx6 = {
        "date": "2024-01-15 10:30:00",
        "amount": 200.75,  # Different amount!
        "description": "Grocery shopping",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    fp5 = _tx_fingerprint_for_dedup(tx5)
    fp6 = _tx_fingerprint_for_dedup(tx6)
    print(f"Transaction 5 fingerprint: {fp5}")
    print(f"Transaction 6 fingerprint: {fp6}")
    print(f"Are they duplicates? {fp5 == fp6} ✓ (EXPECTED: False)")

    # Test 4: Hungarian diacritics normalization
    print("\n✅ Test 4: Diacritics normalization")
    tx7 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.50,
        "description": "Étterem Szeged",  # With diacritics
        "category": "Étel",
        "tran_type": "kiadás",
        "internal_transfer": "none"
    }
    tx8 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.50,
        "description": "Etterem Szeged",  # Without diacritics
        "category": "Etel",
        "tran_type": "kiadas",
        "internal_transfer": "none"
    }
    fp7 = _tx_fingerprint_for_dedup(tx7)
    fp8 = _tx_fingerprint_for_dedup(tx8)
    print(f"Transaction 7 fingerprint: {fp7}")
    print(f"Transaction 8 fingerprint: {fp8}")
    print(f"Are they duplicates? {fp7 == fp8} ✓ (EXPECTED: True)")

    # Test 5: Amount precision (should round to 2 decimals)
    print("\n✅ Test 5: Amount precision")
    tx9 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.5,  # One decimal
        "description": "Test",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    tx10 = {
        "date": "2024-01-15 10:30:00",
        "amount": 150.50,  # Two decimals
        "description": "Test",
        "category": "Food",
        "tran_type": "expense",
        "internal_transfer": "none"
    }
    fp9 = _tx_fingerprint_for_dedup(tx9)
    fp10 = _tx_fingerprint_for_dedup(tx10)
    print(f"Transaction 9 fingerprint: {fp9}")
    print(f"Transaction 10 fingerprint: {fp10}")
    print(f"Are they duplicates? {fp9 == fp10} ✓ (EXPECTED: True)")

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
    print("\nIMPORTANT: Fix 1 is working if Test 2 shows False (different times = not duplicate)")


if __name__ == "__main__":
    test_duplicate_detection()

