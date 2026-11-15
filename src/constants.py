
ASPECTS = [
    "FOOD#QUALITY",
    "FOOD#PRICES",
    "FOOD#STYLE&OPTIONS",
    "DRINKS#QUALITY",
    "DRINKS#PRICES",
    "DRINKS#STYLE&OPTIONS",
    "RESTAURANT#GENERAL",
    "RESTAURANT#PRICES",
    "RESTAURANT#MISCELLANEOUS",
    "SERVICE#GENERAL",
    "AMBIENCE#GENERAL",
    "LOCATION#GENERAL",
]

SENTIMENT_LABELS = {
    0: "Absent",
    1: "Positive",
    2: "Negative",
    3: "Neutral",
}

BATCH_STATUSES = [
    "Processing",
    "Completed",
    "Failed",
]

OUTPUT_COLUMNS = [
    "batch_id",
    "review_id",
    "Review",
    "Aspect",
    "Sentiment",
    "Confidence",
]

MAX_REVIEW_LENGTH = 1000
