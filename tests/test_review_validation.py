import unittest

from src.constants import MAX_REVIEW_LENGTH
from src.validator import validate_review


class TestReviewValidation(unittest.TestCase):

    def test_rejects_empty_or_whitespace_review(self):
        for review in ("", "   ", "\n\t"):
            with self.subTest(review=repr(review)):
                with self.assertRaises(ValueError):
                    validate_review(review)

    def test_accepts_review_at_maximum_length(self):
        review = "a" * MAX_REVIEW_LENGTH

        self.assertEqual(validate_review(review), review)

    def test_rejects_review_over_maximum_length(self):
        review = "a" * (MAX_REVIEW_LENGTH + 1)

        with self.assertRaisesRegex(ValueError, str(MAX_REVIEW_LENGTH)):
            validate_review(review)


if __name__ == "__main__":
    unittest.main()
