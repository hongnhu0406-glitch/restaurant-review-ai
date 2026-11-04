
import uuid


def generate_batch_id():
    """Tạo mã định danh duy nhất cho mỗi lần phân tích."""
    return f"BATCH_{uuid.uuid4().hex[:12].upper()}"


def generate_review_id():
    """Tạo mã định danh duy nhất cho mỗi đánh giá."""
    return f"REV_{uuid.uuid4().hex[:12].upper()}"
