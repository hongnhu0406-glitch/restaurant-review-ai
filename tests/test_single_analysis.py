import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import database, processor
from src.constants import ASPECTS
from src.predictor import predict_review_mock


class TestSingleAnalysisPersistence(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.database_path_patch = patch.object(
            database,
            "DB_PATH",
            self.db_path,
        )
        self.database_path_patch.start()
        database.init_database()

    def tearDown(self):
        self.database_path_patch.stop()
        self.temp_dir.cleanup()

    def test_single_review_is_saved_as_completed_batch(self):
        predictions = predict_review_mock("Đồ ăn ngon")

        with patch(
            "src.processor.predict_review",
            return_value=predictions,
        ):
            results = processor.analyze_single_review("Đồ ăn ngon")

        batch_id = results[0]["batch_id"]
        detail = database.get_batch_detail(batch_id)

        self.assertEqual(detail["batch"]["status"], "Completed")
        self.assertEqual(len(results), len(ASPECTS))
        self.assertEqual(len(detail["results"]), len(ASPECTS))
        self.assertEqual(
            {result["Aspect"] for result in detail["results"]},
            set(ASPECTS),
        )

    def test_prediction_failure_marks_batch_failed_without_results(self):
        record = {
            "batch_id": "BATCH_TEST",
            "review_id": "REV_TEST",
            "Review": "Đồ ăn ngon",
        }

        with patch(
            "src.processor.create_review_record",
            return_value=record,
        ):
            with patch(
                "src.processor.predict_review",
                side_effect=RuntimeError("prediction failed"),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "prediction failed",
                ):
                    processor.analyze_single_review(record["Review"])

        detail = database.get_batch_detail(record["batch_id"])

        self.assertEqual(detail["batch"]["status"], "Failed")
        self.assertEqual(detail["results"], [])

if __name__ == "__main__":
    unittest.main()
