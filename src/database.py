
import sqlite3
from pathlib import Path
from src.constants import ASPECTS, SENTIMENT_LABELS

# Đường dẫn database
DB_PATH = Path("data/restaurant_ai.db")


def get_connection():
    """Tạo kết nối đến SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Bật kiểm tra khóa ngoại
    conn.execute("PRAGMA foreign_keys = ON")

    return conn

def init_database():
    """Khởi tạo các bảng trong database."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            total_rows INTEGER DEFAULT 0,
            total_reviews INTEGER DEFAULT 0,
            skipped_rows INTEGER DEFAULT 0,
            total_results INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            review_id TEXT NOT NULL,
            Review TEXT NOT NULL,
            Aspect TEXT NOT NULL,
            Sentiment INTEGER NOT NULL,
            Confidence REAL,
            UNIQUE(batch_id, review_id, Aspect),
            FOREIGN KEY(batch_id) REFERENCES batches(batch_id)
        )
    """)

    conn.commit()
    conn.close()



def save_batch(batch_result):
    """
    Kiểm tra và lưu toàn bộ kết quả batch.
    Chỉ chuyển sang Completed khi dữ liệu hợp lệ.
    """

    import math

    # 1. Kiểm tra các trường bắt buộc
    required_fields = [
        "batch_id",
        "status",
        "total_rows",
        "total_reviews",
        "skipped_rows",
        "total_results",
        "results"
    ]

    for field in required_fields:
        if field not in batch_result:
            raise ValueError(f"Thiếu trường dữ liệu: {field}")

    if batch_result["status"] != "Completed":
        raise ValueError("Chỉ lưu batch đã Completed.")

    batch_id = batch_result["batch_id"]
    results = batch_result["results"]

    if not isinstance(results, list) or not results:
        raise ValueError("Danh sách kết quả không hợp lệ hoặc rỗng.")

    # 2. Kiểm tra số lượng dữ liệu
    total_rows = batch_result["total_rows"]
    total_reviews = batch_result["total_reviews"]
    skipped_rows = batch_result["skipped_rows"]
    total_results = batch_result["total_results"]

    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in [total_rows, total_reviews, skipped_rows, total_results]
    ):
        raise ValueError("Các thông tin số lượng phải là số nguyên.")

    if min(total_rows, total_reviews, skipped_rows, total_results) < 0:
        raise ValueError("Các thông tin số lượng không được âm.")

    if total_rows != total_reviews + skipped_rows:
        raise ValueError("Tổng số dòng không khớp với số đánh giá và dòng bị bỏ qua.")

    if total_results != len(results):
        raise ValueError("Tổng số kết quả không khớp với dữ liệu thực tế.")

    # 3. Kiểm tra từng kết quả
    review_aspects = {}

    for item in results:
        required_result_fields = [
            "batch_id",
            "review_id",
            "Review",
            "Aspect",
            "Sentiment",
            "Confidence"
        ]

        if not isinstance(item, dict):
            raise ValueError("Một kết quả phân tích không đúng định dạng.")

        for field in required_result_fields:
            if field not in item:
                raise ValueError(f"Kết quả thiếu trường: {field}")

        if item["batch_id"] != batch_id:
            raise ValueError("Phát hiện kết quả thuộc batch khác.")

        if not isinstance(item["review_id"], str) or not item["review_id"].strip():
            raise ValueError("review_id không hợp lệ.")

        if not isinstance(item["Review"], str) or not item["Review"].strip():
            raise ValueError("Nội dung đánh giá không hợp lệ.")

        if item["Aspect"] not in ASPECTS:
            raise ValueError(f"Aspect không hợp lệ: {item['Aspect']}")

        sentiment = item["Sentiment"]
        confidence = item["Confidence"]

        if (
            not isinstance(sentiment, int)
            or isinstance(sentiment, bool)
            or sentiment not in SENTIMENT_LABELS
        ):
            raise ValueError("Sentiment không hợp lệ.")

        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("Confidence phải nằm trong khoảng từ 0 đến 1.")

        review_id = item["review_id"]

        if review_id not in review_aspects:
            review_aspects[review_id] = {
                "Review": item["Review"],
                "Aspects": set()
            }

        if review_aspects[review_id]["Review"] != item["Review"]:
            raise ValueError("Một review_id đang gắn với nhiều nội dung đánh giá.")

        if item["Aspect"] in review_aspects[review_id]["Aspects"]:
            raise ValueError("Một đánh giá có Aspect bị trùng.")

        review_aspects[review_id]["Aspects"].add(item["Aspect"])

    # 4. Kiểm tra mỗi đánh giá có đủ 12 Aspect
    if len(review_aspects) != total_reviews:
        raise ValueError("Số review_id không khớp với total_reviews.")

    for review_id, data in review_aspects.items():
        if data["Aspects"] != set(ASPECTS):
            raise ValueError(
                f"Đánh giá {review_id} không có đủ 12 Aspect."
            )

    if len(results) != total_reviews * len(ASPECTS):
        raise ValueError("Tổng số kết quả không đúng với số Aspect yêu cầu.")

    # 5. Lưu dữ liệu trong transaction
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status
            FROM batches
            WHERE batch_id = ?
        """, (batch_id,))

        batch = cursor.fetchone()

        if batch is None:
            raise ValueError("Không tìm thấy batch.")

        if batch["status"] != "Processing":
            raise ValueError(
                "Chỉ có thể hoàn thành batch đang Processing."
            )

        data = [
            (
                item["batch_id"],
                item["review_id"],
                item["Review"],
                item["Aspect"],
                item["Sentiment"],
                item["Confidence"]
            )
            for item in results
        ]

        cursor.executemany("""
            INSERT INTO results (
                batch_id, review_id, Review,
                Aspect, Sentiment, Confidence
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, data)

        cursor.execute("""
            UPDATE batches
            SET status = ?,
                total_rows = ?,
                total_reviews = ?,
                skipped_rows = ?,
                total_results = ?
            WHERE batch_id = ?
              AND status = 'Processing'
        """, (
            "Completed",
            total_rows,
            total_reviews,
            skipped_rows,
            total_results,
            batch_id
        ))

        if cursor.rowcount != 1:
            raise ValueError("Không thể cập nhật trạng thái batch.")

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def check_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM batches")
    print("Tổng số batch:", cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM results")
    print("Tổng số kết quả:", cursor.fetchone()[0])

    cursor.execute("""
        SELECT batch_id, status, total_reviews, total_results
        FROM batches
        ORDER BY created_at DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    print("Batch mới nhất:", dict(row) if row else "Chưa có batch")

    conn.close()

def get_batch_results(batch_id):
    """
    Lấy kết quả phân tích của một batch đã hoàn thành.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status
        FROM batches
        WHERE batch_id = ?
    """, (batch_id,))

    batch = cursor.fetchone()

    if batch is None:
        conn.close()
        raise ValueError("Không tìm thấy batch.")

    if batch["status"] != "Completed":
        conn.close()
        raise ValueError("Batch chưa hoàn thành.")

    cursor.execute("""
        SELECT batch_id, review_id, Review,
               Aspect, Sentiment, Confidence
        FROM results
        WHERE batch_id = ?
        ORDER BY review_id, Aspect
    """, (batch_id,))

    results = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return results

def get_all_batches():
    """
    Lấy toàn bộ lịch sử Batch, sắp xếp mới nhất lên đầu.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                batch_id,
                status,
                total_rows,
                total_reviews,
                skipped_rows,
                total_results,
                created_at,
                error_message
            FROM batches
            ORDER BY created_at DESC, batch_id DESC
        """)

        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()

def get_batch_statistics(batch_id):
    """
    Thống kê kết quả phân tích của một batch.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            Aspect,
            Sentiment,
            COUNT(*) AS total
        FROM results
        WHERE batch_id = ?
        GROUP BY Aspect, Sentiment
        ORDER BY Aspect, Sentiment
    """, (batch_id,))

    statistics = [
        dict(row) for row in cursor.fetchall()
    ]

    conn.close()

    return statistics


def get_completed_batches():
    """
    Lấy danh sách các batch đã hoàn thành.
    Chỉ những batch này được phép hiển thị trên Dashboard.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM batches
        WHERE status = 'Completed'
        ORDER BY created_at DESC
    """)

    batches = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return batches



def get_overall_statistics(batch_id):
    """
    Thống kê tổng quan cảm xúc của một batch.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            Sentiment,
            COUNT(*) AS total
        FROM results
        WHERE batch_id = ?
        GROUP BY Sentiment
        ORDER BY Sentiment
    """, (batch_id,))

    statistics = {
        0: 0,
        1: 0,
        2: 0,
        3: 0
    }

    for row in cursor.fetchall():
        statistics[row["Sentiment"]] = row["total"]

    conn.close()

    return statistics


def get_aspect_sentiment_statistics(batch_id):
    """
    Thống kê số lượng và tỷ lệ cảm xúc của từng khía cạnh.
    Không tính Absent vào mẫu số khi tính tỷ lệ cảm xúc.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            Aspect,
            Sentiment,
            COUNT(*) AS total
        FROM results
        WHERE batch_id = ?
        GROUP BY Aspect, Sentiment
    """, (batch_id,))

    raw_statistics = cursor.fetchall()
    conn.close()

    statistics = {}

    for aspect in ASPECTS:
        statistics[aspect] = {
            "Absent": 0,
            "Positive": 0,
            "Negative": 0,
            "Neutral": 0
        }

    sentiment_names = {
        0: "Absent",
        1: "Positive",
        2: "Negative",
        3: "Neutral"
    }

    for row in raw_statistics:
        aspect = row["Aspect"]
        sentiment = sentiment_names[row["Sentiment"]]
        statistics[aspect][sentiment] = row["total"]

    # Tính tổng và tỷ lệ cảm xúc
    for aspect, data in statistics.items():
        analyzed = (
            data["Positive"]
            + data["Negative"]
            + data["Neutral"]
        )

        data["Analyzed"] = analyzed
        data["Total"] = analyzed + data["Absent"]

        for sentiment in ["Positive", "Negative", "Neutral"]:
            if analyzed > 0:
                percentage = data[sentiment] / analyzed * 100
            else:
                percentage = 0

            data[sentiment + "_Percentage"] = round(
                percentage, 2
            )

    return statistics


def create_batch(batch_id):
    """Tạo batch mới với trạng thái Processing."""

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO batches (
                batch_id,
                status
            )
            VALUES (?, ?)
        """, (batch_id, "Processing"))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def update_batch_status(
    batch_id,
    status,
    total_rows=None,
    total_reviews=None,
    skipped_rows=None,
    total_results=None,
    error_message=None
):
    """
    Cập nhật trạng thái Batch mà không làm mất
    các số liệu đã được ghi nhận trước đó.
    """

    if status not in ["Processing", "Failed"]:
        raise ValueError(
            "Chỉ được cập nhật Processing hoặc Failed. "
            "Completed phải thông qua save_batch()."
        )

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE batches
            SET status = ?,
                total_rows = COALESCE(?, total_rows),
                total_reviews = COALESCE(?, total_reviews),
                skipped_rows = COALESCE(?, skipped_rows),
                total_results = COALESCE(?, total_results),
                error_message = COALESCE(?, error_message)
            WHERE batch_id = ?
              AND status = 'Processing'
        """, (
            status,
            total_rows,
            total_reviews,
            skipped_rows,
            total_results,
            error_message,
            batch_id
        ))

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT status
                FROM batches
                WHERE batch_id = ?
            """, (batch_id,))

            batch = cursor.fetchone()

            if batch is None:
                raise ValueError("Không tìm thấy Batch.")

            raise ValueError(
                f"Không thể cập nhật Batch có trạng thái "
                f"{batch['status']}."
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
def fail_stale_batches(timeout_minutes=30):
    """
    Chuyển các Batch Processing quá thời gian cho phép
    sang Failed.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE batches
            SET status = 'Failed',
                error_message = ?
            WHERE status = 'Processing'
              AND created_at <= datetime(
                  'now',
                  ?
              )
        """, (
            f"Batch bị gián đoạn hoặc xử lý quá "
            f"{timeout_minutes} phút.",
            f"-{timeout_minutes} minutes"
        ))

        affected_rows = cursor.rowcount

        conn.commit()

        return affected_rows

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_dashboard_data(batch_id):
    """
    Lấy toàn bộ dữ liệu cần thiết cho Dashboard.
    Chỉ chấp nhận batch đã Completed.
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT *
            FROM batches
            WHERE batch_id = ?
              AND status = 'Completed'
        """, (batch_id,))

        batch = cursor.fetchone()

        if batch is None:
            raise ValueError(
                "Không tìm thấy batch Completed."
            )

        batch_info = dict(batch)

        # Thống kê tổng số lượng cảm xúc
        cursor.execute("""
            SELECT
                Sentiment,
                COUNT(*) AS total
            FROM results
            WHERE batch_id = ?
            GROUP BY Sentiment
        """, (batch_id,))

        overall = {0: 0, 1: 0, 2: 0, 3: 0}

        for row in cursor.fetchall():
            overall[row["Sentiment"]] = row["total"]

        # Thống kê số lượng và tỷ lệ theo từng khía cạnh
        aspect_stats = get_aspect_sentiment_statistics(batch_id)

        # Lấy toàn bộ kết quả phân tích
        cursor.execute("""
            SELECT batch_id, review_id, Review,
                   Aspect, Sentiment, Confidence
            FROM results
            WHERE batch_id = ?
            ORDER BY review_id, Aspect
        """, (batch_id,))

        results = [
            dict(row) for row in cursor.fetchall()
        ]

        return {
            "batch": batch_info,
            "overall_statistics": overall,
            "aspect_statistics": aspect_stats,
            "results": results
        }

    finally:
        conn.close()



def get_batch_detail(batch_id):
    """
    Lấy thông tin chi tiết của một Batch.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM batches
            WHERE batch_id = ?
        """, (batch_id,))

        batch = cursor.fetchone()

        if batch is None:
            raise ValueError("Không tìm thấy Batch.")

        batch = dict(batch)

        if batch["status"] == "Completed":
            cursor.execute("""
                SELECT
                    batch_id,
                    review_id,
                    Review,
                    Aspect,
                    Sentiment,
                    Confidence
                FROM results
                WHERE batch_id = ?
                ORDER BY review_id, Aspect
            """, (batch_id,))

            results = [dict(row) for row in cursor.fetchall()]
        else:
            results = []

        return {
            "batch": batch,
            "results": results
        }

    finally:
        conn.close()

if __name__ == "__main__":
    init_database()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )

    print("Các bảng:", [row["name"] for row in cursor.fetchall()])

    conn.close()
    check_database()