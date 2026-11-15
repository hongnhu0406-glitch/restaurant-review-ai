import unittest

from src.predictor import predict_review_mock
from src.validator import validate_prediction_results
from src.constants import ASPECTS


class TestPredictor(unittest.TestCase):

    def test_generic_price_phrase_is_positive_for_restaurant_prices(self):
        results = predict_review_mock("giá ổn")
        sentiments = {
            item["Aspect"]: item["Sentiment"]
            for item in results
        }

        self.assertEqual(sentiments["RESTAURANT#PRICES"], 1)
        self.assertEqual(sentiments["FOOD#PRICES"], 0)
        self.assertEqual(sentiments["DRINKS#PRICES"], 0)

    def test_food_and_drink_price_phrases_use_specific_aspects(self):
        food_results = predict_review_mock("giá đồ ăn ổn")
        drink_results = predict_review_mock("giá nước ổn")
        food_sentiments = {
            item["Aspect"]: item["Sentiment"]
            for item in food_results
        }
        drink_sentiments = {
            item["Aspect"]: item["Sentiment"]
            for item in drink_results
        }

        self.assertEqual(food_sentiments["FOOD#PRICES"], 1)
        self.assertEqual(food_sentiments["RESTAURANT#PRICES"], 0)
        self.assertEqual(drink_sentiments["DRINKS#PRICES"], 1)
        self.assertEqual(drink_sentiments["RESTAURANT#PRICES"], 0)

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