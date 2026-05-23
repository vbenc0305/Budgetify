import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db.firebase_client as firebase_client

TEST_UID = "3Dye4gBbAdPQSto3WbqgkBu6lrj2"


class TestCountyTransactionsFallback(unittest.TestCase):
    def test_fallback_uses_local_county_index_for_bekes_user(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            county_index_path = Path(tmp_dir) / "county_index.json"
            county_index_path.write_text(
                json.dumps({TEST_UID: "bekes"}, ensure_ascii=False),
                encoding="utf-8",
            )

            fake_txs = [
                {
                    "id": "tx-1",
                    "amount": 1000.0,
                    "category": "Etel",
                    "date": "2026-03-23 10:00:00",
                    "tran_type": "Kimenő",
                }
            ]

            with patch.object(firebase_client, "COUNTY_INDEX_PATH", county_index_path), \
                 patch.object(
                     firebase_client,
                     "_get_user_ids_for_county_firestore",
                     side_effect=firebase_client.FirebaseUnavailable("Quota exceeded."),
                 ), \
                 patch.object(firebase_client, "get_user_transactions", return_value=fake_txs):
                for query in ("Békés", "Bekes"):
                    with self.subTest(query=query):
                        result = firebase_client.get_county_transactions(query)
                        self.assertEqual(result["matched_users"], 1)
                        self.assertEqual(result["data_source"], "local_county_index")
                        self.assertEqual(len(result["transactions"]), 1)

                        tx = result["transactions"][0]
                        self.assertEqual(tx["user_id"], TEST_UID)
                        self.assertEqual(tx["transaction_id"], "tx-1")

    def test_fallback_returns_empty_when_county_missing_from_local_index(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            county_index_path = Path(tmp_dir) / "county_index.json"
            county_index_path.write_text(
                json.dumps({TEST_UID: "bekes"}, ensure_ascii=False),
                encoding="utf-8",
            )

            with patch.object(firebase_client, "COUNTY_INDEX_PATH", county_index_path), \
                 patch.object(
                     firebase_client,
                     "_get_user_ids_for_county_firestore",
                     side_effect=firebase_client.FirebaseUnavailable("Quota exceeded."),
                 ), \
                 patch.object(firebase_client, "get_user_transactions") as mocked_get_user_transactions:
                result = firebase_client.get_county_transactions("Baranya")

                self.assertEqual(result["matched_users"], 0)
                self.assertEqual(result["transactions"], [])
                self.assertEqual(result["data_source"], "local_county_index")
                mocked_get_user_transactions.assert_not_called()


if __name__ == "__main__":
    unittest.main()

