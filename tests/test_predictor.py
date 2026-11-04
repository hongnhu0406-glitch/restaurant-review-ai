import unittest

from src.predictor import predict_review_mock
from src.validator import validate_prediction_results
from src.constants import ASPECTS


class TestPredictor(unittest.TestCase):

    def test_prediction_has_12_aspects(self):
        results = predict_review_mock("Đồ ăn ngon")
        self.assertEqual(len(results), 12)

    def test_prediction_contains_all_aspects(self):
        results = predict_review_mock("Đồ ăn ngon")
        result_aspects = [item["Aspect"] for item in results]
        self.assertEqual(set(result_aspects), set(ASPECTS))

    def test_prediction_is_valid(self):
        results = predict_review_mock("Đồ ăn ngon")
        self.assertTrue(validate_prediction_results(results))


if __name__ == "__main__":
    unittest.main()