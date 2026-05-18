import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_current_user_uid
from api.routes import stats
from api.routes.transactions import transform_excel_row
from db.firebase_client import normalize_transaction_record_current_schema
from main import app as main_app


async def _fake_uid_dependency():
    return "test-user"


class TestTransactionTransferTypeApi(unittest.TestCase):
    def setUp(self):
        main_app.dependency_overrides[get_current_user_uid] = _fake_uid_dependency
        self.client = TestClient(main_app)

    def tearDown(self):
        main_app.dependency_overrides.clear()

    def test_get_transactions_returns_transaction_direction_and_for_who_separately(self):
        mocked_transactions = [
            {
                "amount": 499,
                "category": "Közlekedés",
                "date": "2024-04-29 07:29:29",
                "description": "2024.04.29 4159956198 BÉKÉSCSABA MÁV           -ÉRINTŐ",
                "for_who": "MÁV",
                "transaction_direction": "Kimenő",
                "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
                "transaction_id": "78c3a504-a8eb-4b93-ae4c-8dbe79b36ef1",
                "user_id": "test-user",
            }
        ]

        with patch("api.routes.transactions.get_user_transactions", return_value=mocked_transactions):
            response = self.client.get("/api/transactions", headers={"Authorization": "Bearer test-token"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload[0]["transaction_direction"], "Kimenő")
        self.assertEqual(payload[0]["for_who"], "MÁV")
        self.assertNotIn("Transfer type", payload[0])

    def test_put_transaction_requires_transaction_direction_and_keeps_for_who_as_partner(self):
        request_payload = {
            "amount": 499,
            "category": "Közlekedés",
            "date": "2024-04-29 07:29:29",
            "description": "2024.04.29 4159956198 BÉKÉSCSABA MÁV           -ÉRINTŐ",
            "for_who": "MÁV",
            "transaction_direction": "Kimenő",
            "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
        }

        with patch("api.routes.transactions.get_user_transactions", return_value=[]), patch(
            "api.routes.transactions.save_user_transaction", return_value="doc-1"
        ) as mocked_save:
            response = self.client.put(
                "/api/transactions",
                json=request_payload,
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        transaction = payload["transaction"]
        self.assertEqual(transaction["transaction_direction"], "Kimenő")
        self.assertEqual(transaction["for_who"], "MÁV")
        self.assertNotIn("Transfer type", transaction)

        saved_payload = mocked_save.call_args.args[1]
        self.assertEqual(saved_payload["for_who"], "MÁV")
        self.assertEqual(saved_payload["transaction_direction"], "Kimenő")

    def test_stats_route_returns_transaction_direction_instead_of_transfer_type_alias(self):
        stats_app = FastAPI()
        stats_app.include_router(stats.router, prefix="/api")
        stats_app.dependency_overrides[get_current_user_uid] = _fake_uid_dependency
        client = TestClient(stats_app)

        county_payload = {
            "matched_users": 1,
            "transactions": [
                {
                    "transaction_id": "tx-1",
                    "user_id": "test-user",
                    "for_who": "Teszt partner",
                    "transaction_direction": "Bejövő",
                    "tran_type": "ÁTUTALÁS",
                }
            ],
            "data_source": "firestore",
        }

        with patch("api.routes.stats.firebase_client.get_county_transactions", return_value=county_payload):
            response = client.get(
                "/api/stats/counties/Bekes/categories",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        transaction = payload["transactions"][0]
        self.assertEqual(transaction["transaction_direction"], "Bejövő")
        self.assertEqual(transaction["for_who"], "Teszt partner")
        self.assertNotIn("Transfer type", transaction)

        stats_app.dependency_overrides.clear()

    def test_main_app_registers_stats_route(self):
        county_payload = {
            "matched_users": 1,
            "transactions": [
                {
                    "transaction_id": "tx-1",
                    "user_id": "test-user",
                    "for_who": "Teszt partner",
                    "transaction_direction": "Bejövő",
                    "tran_type": "ÁTUTALÁS",
                }
            ],
            "data_source": "firestore",
        }

        with patch("api.routes.stats.firebase_client.get_county_transactions", return_value=county_payload):
            response = self.client.get(
                "/api/stats/counties/B%C3%A9k%C3%A9s/categories",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["county"], "Békés")
        self.assertEqual(payload["transactions"][0]["transaction_direction"], "Bejövő")

    def test_transform_excel_row_maps_partner_and_direction_to_separate_fields(self):
        row = {
            "Összeg": "499",
            "Tranzakció dátuma": "2024-04-29 07:29:29",
            "Közlemény": "2024.04.29 4159956198 BÉKÉSCSABA MÁV           -ÉRINTŐ",
            "Partner neve": "MÁV",
            "Bejövő/Kimenő": "Kimenő",
            "Típus": "VÁSÁRLÁS KÁRTYÁVAL",
            "Költési kategória": "Közlekedés",
        }

        transformed = transform_excel_row(row)

        self.assertEqual(transformed["for_who"], "MÁV")
        self.assertEqual(transformed["transaction_direction"], "Kimenő")

    def test_old_schema_transaction_is_rejected_instead_of_reused(self):
        stale_transaction = {
            "amount": 499,
            "for_who": "Kimenő",
            "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
        }

        self.assertIsNone(normalize_transaction_record_current_schema(stale_transaction))


if __name__ == "__main__":
    unittest.main()

