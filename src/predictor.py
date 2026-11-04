import re

from src.constants import ASPECTS, SENTIMENT_LABELS


# =========================================================
# 1. TỪ KHÓA TÍCH CỰC THEO TỪNG KHÍA CẠNH
# =========================================================

POSITIVE_KEYWORDS = {
    "FOOD#QUALITY": [
        "ngon", "tươi", "đậm đà", "hấp dẫn",
        "delicious", "tasty", "fresh", "flavorful",
        "excellent food", "great food"
    ],

    "FOOD#PRICES": [
        "giá món ăn hợp lý", "giá đồ ăn hợp lý",
        "food prices are reasonable", "reasonable food prices",
        "affordable food", "food is affordable"
    ],

    "FOOD#STYLE&OPTIONS": [
        "đa dạng món", "nhiều lựa chọn món ăn",
        "variety of dishes", "many food options",
        "wide food selection"
    ],

    "DRINKS#QUALITY": [
        "đồ uống ngon", "nước ngon", "đồ uống chất lượng",
        "delicious drinks", "great drinks", "good drinks"
    ],

    "DRINKS#PRICES": [
        "giá đồ uống hợp lý", "đồ uống giá rẻ",
        "reasonable drink prices", "cheap drinks"
    ],

    "DRINKS#STYLE&OPTIONS": [
        "nhiều loại đồ uống", "đồ uống đa dạng",
        "variety of drinks", "many drink options"
    ],

    "RESTAURANT#GENERAL": [
        "nhà hàng tuyệt vời", "nhà hàng tốt",
        "great restaurant", "excellent restaurant",
        "wonderful restaurant"
    ],

    "RESTAURANT#PRICES": [
        "giá hợp lý", "giá cả phải chăng", "giá rẻ",
        "reasonable prices", "affordable prices",
        "cheap prices", "good value"
    ],

    "RESTAURANT#MISCELLANEOUS": [
        "đáng quay lại", "trải nghiệm tuyệt vời",
        "worth visiting", "worth coming back",
        "great experience"
    ],

    "SERVICE#GENERAL": [
        "nhiệt tình", "thân thiện", "nhanh chóng",
        "phục vụ tốt", "chu đáo",
        "friendly", "attentive", "helpful",
        "fast service", "excellent service",
        "great service"
    ],

    "AMBIENCE#GENERAL": [
        "không gian đẹp", "thoải mái", "ấm cúng",
        "sạch sẽ", "trang trí đẹp",
        "beautiful atmosphere", "cozy", "comfortable",
        "clean atmosphere", "nice decoration"
    ],

    "LOCATION#GENERAL": [
        "vị trí thuận tiện", "dễ tìm", "dễ di chuyển",
        "convenient location", "easy to find",
        "great location", "accessible"
    ]
}


# =========================================================
# 2. TỪ KHÓA TIÊU CỰC THEO TỪNG KHÍA CẠNH
# =========================================================

NEGATIVE_KEYWORDS = {
    "FOOD#QUALITY": [
        "dở", "tệ", "không ngon", "nguội", "ôi thiu",
        "bad food", "terrible food", "awful food",
        "tasteless", "bland", "disgusting"
    ],

    "FOOD#PRICES": [
        "giá món ăn đắt", "giá đồ ăn cao",
        "food prices are too high", "food prices are expensive",
        "expensive food", "overpriced food",
        "food is overpriced"
    ],

    "FOOD#STYLE&OPTIONS": [
        "ít món", "ít lựa chọn món ăn", "menu nghèo nàn",
        "limited food options", "few food choices",
        "limited menu"
    ],

    "DRINKS#QUALITY": [
        "đồ uống dở", "nước uống tệ",
        "bad drinks", "terrible drinks",
        "awful drinks"
    ],

    "DRINKS#PRICES": [
        "đồ uống quá đắt", "giá đồ uống cao",
        "expensive drinks", "overpriced drinks"
    ],

    "DRINKS#STYLE&OPTIONS": [
        "ít đồ uống", "ít lựa chọn đồ uống",
        "limited drink options", "few drink choices"
    ],

    "RESTAURANT#GENERAL": [
        "nhà hàng tệ", "nhà hàng thất vọng",
        "bad restaurant", "terrible restaurant",
        "disappointing restaurant"
    ],

    "RESTAURANT#PRICES": [
        "giá quá cao", "giá quá đắt",
        "đắt đỏ", "giá không hợp lý",
        "prices are too high", "price is too high",
        "overpriced prices", "expensive prices",
        "prices are high", "prices were too high",
        "prices were high", "the prices were too high",
        "the prices were high"
    ],

    "RESTAURANT#MISCELLANEOUS": [
        "không đáng tiền", "không muốn quay lại",
        "trải nghiệm tệ", "thất vọng",
        "not worth it", "not worth visiting",
        "would not return", "bad experience",
        "disappointing experience"
    ],

    "SERVICE#GENERAL": [
        "chậm", "thô lỗ", "không thân thiện",
        "phục vụ kém", "thiếu chuyên nghiệp",
        "slow service", "slow", "rude",
        "unfriendly", "poor service",
        "bad service", "terrible service"
    ],

    "AMBIENCE#GENERAL": [
        "ồn ào", "bẩn", "chật chội", "khó chịu",
        "noisy", "dirty", "crowded",
        "uncomfortable", "unpleasant atmosphere"
    ],

    "LOCATION#GENERAL": [
        "khó tìm", "xa", "bất tiện",
        "difficult to find", "hard to find",
        "inconvenient location", "far away"
    ]
}


# =========================================================
# 3. TỪ PHỦ ĐỊNH
# =========================================================

NEGATION_WORDS = [
    "not", "no", "never", "isn't", "wasn't",
    "aren't", "weren't", "don't", "doesn't",
    "didn't", "cannot", "can't",
    "không", "chẳng", "chưa", "không hề",
    "không có"
]


# =========================================================
# 4. HÀM KIỂM TRA TỪ KHÓA
# =========================================================

def contains_keyword(review, keywords):
    """
    Kiểm tra từ khóa xuất hiện trong câu.
    Sử dụng ranh giới từ để hạn chế nhận diện nhầm
    một từ nằm bên trong từ khác.
    """

    for keyword in keywords:
        pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"

        if re.search(pattern, review):
            return True

    return False


def find_keyword_matches(review, keywords):
    """
    Tìm từ khóa và kiểm tra từ phủ định đứng ngay trước nó.

    Ví dụ:
    delicious       -> tích cực
    not delicious   -> phủ định tích cực
    not very good   -> phủ định tích cực
    """

    matches = []

    for keyword in keywords:
        pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"

        for match in re.finditer(pattern, review):
            start = match.start()

            # Lấy tối đa 3 từ ngay trước từ khóa
            prefix = review[:start].split()
            preceding_words = prefix[-3:]

            is_negated = any(
                negation in preceding_words
                for negation in NEGATION_WORDS
            )

            matches.append({
                "keyword": keyword,
                "negated": is_negated
            })

    return matches


# =========================================================
# 5. XỬ LÝ TỪ "EXPENSIVE" THEO NGỮ CẢNH
# =========================================================

def detect_price_context(review, aspect):
    """
    Phân biệt giá món ăn và mức giá chung nhà hàng.

    Ví dụ:
    The food was expensive
        -> FOOD#PRICES

    The restaurant was expensive
        -> RESTAURANT#PRICES
    """

    expensive_keywords = [
        "expensive", "overpriced", "pricey",
        "too expensive", "đắt", "quá đắt", "đắt đỏ"
    ]

    has_expensive = contains_keyword(review, expensive_keywords)

    if not has_expensive:
        return None

    food_context = contains_keyword(
        review,
        [
            "food", "dish", "meal", "meal price",
            "món ăn", "đồ ăn", "thức ăn"
        ]
    )

    drink_context = contains_keyword(
        review,
        [
            "drink", "drinks", "beverage",
            "đồ uống", "nước uống"
        ]
    )

    restaurant_context = contains_keyword(
        review,
        [
            "restaurant", "restaurant price",
            "nhà hàng", "giá cả nhà hàng"
        ]
    )

    if aspect == "FOOD#PRICES" and food_context:
        return 2

    if aspect == "DRINKS#PRICES" and drink_context:
        return 2

    if aspect == "RESTAURANT#PRICES":
        if restaurant_context and not food_context and not drink_context:
            return 2

    return None


# =========================================================
# 6. DỰ ĐOÁN CẢM XÚC CHO MỘT KHÍA CẠNH
# =========================================================

def predict_aspect_sentiment(review, aspect):
    """
    Dự đoán cảm xúc cho một khía cạnh.

    0: Absent - Không đề cập
    1: Positive - Tích cực
    2: Negative - Tiêu cực
    3: Neutral - Trung lập
    """

    # Kiểm tra ngữ cảnh giá trước
    price_result = detect_price_context(review, aspect)

    if price_result is not None:
        return price_result, 0.90

    positive_matches = find_keyword_matches(
        review,
        POSITIVE_KEYWORDS.get(aspect, [])
    )

    negative_matches = find_keyword_matches(
        review,
        NEGATIVE_KEYWORDS.get(aspect, [])
    )

    positive = False
    negative = False

    # Từ tích cực bị phủ định sẽ chuyển thành tiêu cực
    for match in positive_matches:
        if match["negated"]:
            negative = True
        else:
            positive = True

    # Từ tiêu cực bị phủ định sẽ chuyển thành tích cực
    for match in negative_matches:
        if match["negated"]:
            positive = True
        else:
            negative = True

    # Hai cảm xúc cùng xuất hiện trên một khía cạnh
    if positive and negative:
        return 3, 0.75

    if positive:
        return 1, 0.90

    if negative:
        return 2, 0.90

    return 0, 0.95


# =========================================================
# 7. DỰ ĐOÁN TOÀN BỘ 12 KHÍA CẠNH
# =========================================================

def predict_review_mock(review):
    """
    Mô phỏng kết quả phân tích 12 khía cạnh.
    Hỗ trợ từ khóa tiếng Việt và tiếng Anh.
    """

    review = str(review).lower().strip()

    # Chuẩn hóa khoảng trắng
    review = re.sub(r"\s+", " ", review)

    results = []

    for aspect in ASPECTS:
        sentiment, confidence = predict_aspect_sentiment(
            review,
            aspect
        )

        results.append({
            "Aspect": aspect,
            "Sentiment": sentiment,
            "Sentiment_Label": SENTIMENT_LABELS[sentiment],
            "Confidence": confidence
        })

    return results


# =========================================================
# 8. HÀM DỰ ĐOÁN CHÍNH
# =========================================================

def predict_review(review):
    """
    Hàm dự đoán chính được processor sử dụng.

    Hiện tại vẫn sử dụng bộ dự đoán mock.
    Có thể thay thế bằng PhoBERT sau này.
    """

    return predict_review_mock(review)