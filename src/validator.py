
import math

from src.constants import ASPECTS, MAX_REVIEW_LENGTH, SENTIMENT_LABELS


def validate_review(review):
    """
    Kiểm tra dữ liệu đánh giá đầu vào.
    """

    if not isinstance(review, str):
        raise TypeError("Review phải là chuỗi văn bản.")

    review = review.strip()

    if not review:
        raise ValueError("Nội dung đánh giá không được để trống.")

    if len(review) > MAX_REVIEW_LENGTH:
        raise ValueError(
            f"Nội dung đánh giá không được vượt quá "
            f"{MAX_REVIEW_LENGTH} ký tự."
        )

    return review


def validate_prediction_results(results):
    """
    Kiểm tra tính hợp lệ của kết quả dự đoán.

    Yêu cầu:
    - Kết quả phải là danh sách.
    - Có đúng 12 khía cạnh.
    - Không có khía cạnh trùng lặp.
    - Đầy đủ các khía cạnh theo ASPECTS.
    - Sentiment phải là nhãn hợp lệ.
    - Confidence phải là số hữu hạn trong khoảng [0, 1].
    """

    # 1. Kiểm tra kiểu dữ liệu đầu vào
    if not isinstance(results, list):
        raise TypeError(
            "Kết quả dự đoán phải là một danh sách."
        )

    # 2. Kiểm tra số lượng kết quả
    if len(results) != len(ASPECTS):
        raise ValueError(
            f"Kết quả phải có đúng {len(ASPECTS)} khía cạnh."
        )

    # 3. Kiểm tra cấu trúc từng kết quả
    required_fields = {"Aspect", "Sentiment", "Confidence"}

    for index, item in enumerate(results):

        if not isinstance(item, dict):
            raise TypeError(
                f"Kết quả thứ {index + 1} phải là dictionary."
            )

        missing_fields = required_fields - set(item.keys())

        if missing_fields:
            raise ValueError(
                f"Kết quả thứ {index + 1} thiếu trường: "
                f"{', '.join(sorted(missing_fields))}."
            )

    # 4. Kiểm tra danh sách khía cạnh
    result_aspects = [item["Aspect"] for item in results]

    if not all(isinstance(aspect, str) for aspect in result_aspects):
        raise TypeError("Aspect phải là chuỗi văn bản.")

    if len(set(result_aspects)) != len(result_aspects):
        raise ValueError(
            "Phát hiện khía cạnh bị trùng lặp."
        )

    if set(result_aspects) != set(ASPECTS):
        raise ValueError(
            "Danh sách khía cạnh không hợp lệ."
        )

    # 5. Kiểm tra Sentiment và Confidence
    for index, item in enumerate(results):

        sentiment = item["Sentiment"]
        confidence = item["Confidence"]

        # Sentiment phải là số nguyên hợp lệ, không chấp nhận bool
        if isinstance(sentiment, bool) or not isinstance(sentiment, int):
            raise TypeError(
                f"Sentiment tại kết quả thứ {index + 1} phải là số nguyên."
            )

        if sentiment not in SENTIMENT_LABELS:
            raise ValueError(
                f"Nhãn Sentiment tại kết quả thứ {index + 1} không hợp lệ."
            )

        # Confidence phải là số, không chấp nhận bool
        if isinstance(confidence, bool) or not isinstance(
            confidence, (int, float)
        ):
            raise TypeError(
                f"Confidence tại kết quả thứ {index + 1} phải là số."
            )

        # Không chấp nhận NaN hoặc Infinity
        if not math.isfinite(confidence):
            raise ValueError(
                f"Confidence tại kết quả thứ {index + 1} phải là số hữu hạn."
            )

        if not 0 <= confidence <= 1:
            raise ValueError(
                f"Confidence tại kết quả thứ {index + 1} "
                "phải nằm trong khoảng 0 đến 1."
            )

    return True
