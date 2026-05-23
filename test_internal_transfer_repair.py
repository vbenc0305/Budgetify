import unittest

from api.routes.transactions import classify_internal_transfer
from src.Generation.data_preparation import prepare_transaction_data


class TestInternalTransferClassification(unittest.TestCase):
    def test_regular_outgoing_purchase_is_not_internal_transfer(self):
        result = classify_internal_transfer(
            description="2024.04.29 TESCO",
            tran_type="VÁSÁRLÁS KÁRTYÁVAL",
            transaction_direction="Kimenő",
            for_who="TESCO",
            amount=499.0,
        )
        self.assertEqual(result, "none")

    def test_persely_outgoing_transfer_is_classified_as_jar_in(self):
        result = classify_internal_transfer(
            description="Tanulmányok persely",
            tran_type="ESETI ÁTVEZETÉS PERSELYBE",
            transaction_direction="Kimenő",
            for_who="Tanulmányok",
            amount=5000.0,
        )
        self.assertEqual(result, "jar_in")

    def test_persely_incoming_transfer_is_classified_as_jar_out(self):
        result = classify_internal_transfer(
            description="Tanulmányok persely",
            tran_type="AZONNALI FIZETÉS BANKON BELÜL",
            transaction_direction="Bejövő",
            for_who="PERSELYSZÁMLA 8864",
            amount=5000.0,
        )
        self.assertEqual(result, "jar_out")


class TestPrepareTransactionDataRepair(unittest.TestCase):
    def test_prepare_transaction_data_repairs_stale_internal_transfer_labels(self):
        tx_list = [
            {
                "amount": 100.0,
                "category": "Food",
                "date": "2024-01-05 10:00:00",
                "description": "Tesco grocery",
                "for_who": "TESCO",
                "transaction_direction": "Kimenő",
                "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
                "user_id": "u1",
                "internal_transfer": "jar_out",
            },
            {
                "amount": 150.0,
                "category": "Travel",
                "date": "2024-02-05 10:00:00",
                "description": "MÁV ticket",
                "for_who": "MÁV",
                "transaction_direction": "Kimenő",
                "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
                "user_id": "u1",
                "internal_transfer": "jar_out",
            },
            {
                "amount": 120.0,
                "category": "Food",
                "date": "2024-03-05 10:00:00",
                "description": "Spar grocery",
                "for_who": "SPAR",
                "transaction_direction": "Kimenő",
                "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
                "user_id": "u1",
                "internal_transfer": "jar_out",
            },
            {
                "amount": 200.0,
                "category": "Bills",
                "date": "2024-04-05 10:00:00",
                "description": "Utility payment",
                "for_who": "Utility Co",
                "transaction_direction": "Kimenő",
                "tran_type": "ÁTUTALÁS",
                "user_id": "u1",
                "internal_transfer": "jar_out",
            },
        ]

        monthly_series, exog, exog_forecast, used_status = prepare_transaction_data(uid="u1", tx_list=tx_list)

        self.assertIsNotNone(monthly_series)
        self.assertEqual(used_status, "from_db")
        self.assertEqual(len(monthly_series), 4)
        self.assertAlmostEqual(float(monthly_series.sum()), 570.0)
        self.assertIsNotNone(exog)
        self.assertIsNotNone(exog_forecast)

    def test_prepare_transaction_data_filters_internal_transfer_persely_rows_without_description_filter(self):
        tx_list = [
            {
                "amount": 400.0,
                "category": "Savings",
                "date": "2024-01-03 10:00:00",
                "description": "Tanulmányok persely",
                "for_who": "Tanulmányok",
                "transaction_direction": "Kimenő",
                "tran_type": "ESETI ÁTVEZETÉS PERSELYBE",
                "user_id": "u1",
                "internal_transfer": "jar_in",
            },
            {
                "amount": 120.0,
                "category": "Food",
                "date": "2024-01-12 10:00:00",
                "description": "Tesco grocery",
                "for_who": "TESCO",
                "transaction_direction": "Kimenő",
                "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
                "user_id": "u1",
                "internal_transfer": "none",
            },
        ]

        monthly_series, exog, exog_forecast, used_status = prepare_transaction_data(uid="u1", tx_list=tx_list)

        self.assertIsNotNone(monthly_series)
        self.assertEqual(used_status, "from_db")
        self.assertEqual(len(monthly_series), 1)
        self.assertAlmostEqual(float(monthly_series.iloc[0]), 120.0)
        self.assertIsNotNone(exog)
        self.assertIsNotNone(exog_forecast)

    def test_prepare_transaction_data_does_not_drop_description_only_persely_row_when_internal_transfer_is_none(self):
        tx_list = [
            {
                "amount": 80.0,
                "category": "Misc",
                "date": "2024-01-08 10:00:00",
                "description": "Persely matrica vásárlás",
                "for_who": "Papírbolt",
                "transaction_direction": "Kimenő",
                "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
                "user_id": "u1",
                "internal_transfer": "none",
            },
            {
                "amount": 50.0,
                "category": "Food",
                "date": "2024-02-08 10:00:00",
                "description": "Coffee",
                "for_who": "Cafe",
                "transaction_direction": "Kimenő",
                "tran_type": "VÁSÁRLÁS KÁRTYÁVAL",
                "user_id": "u1",
                "internal_transfer": "none",
            },
        ]

        monthly_series, exog, exog_forecast, used_status = prepare_transaction_data(uid="u1", tx_list=tx_list)

        self.assertIsNotNone(monthly_series)
        self.assertEqual(used_status, "from_db")
        self.assertEqual(len(monthly_series), 2)
        self.assertAlmostEqual(float(monthly_series.sum()), 130.0)
        self.assertIsNotNone(exog)
        self.assertIsNotNone(exog_forecast)


if __name__ == "__main__":
    unittest.main()

