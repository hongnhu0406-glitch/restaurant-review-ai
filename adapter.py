
import os
import pandas as pd
import requests

API_BASE_URL = os.environ.get(
    "RESTAURANT_API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

TIMEOUT = 15

# Các cột kết quả mà Backend trả về
RESULT_COLUMNS = [
    "batch_id",
    "review_id",
    "Review",
    "Aspect",
    "Sentiment",
    "Confidence"
]


class BackendError(Exception):
    """Lỗi Backend bằng tiếng Việt."""


# =====================================================
# HÀM GỌI API CHUNG
# =====================================================

def _get(path, raw=False):
    url = f"{API_BASE_URL}{path}"

    try:
        resp = requests.get(url, timeout=TIMEOUT)

    except requests.exceptions.ConnectionError:
        raise BackendError(
            f"Không kết nối được Backend tại {API_BASE_URL}. "
            "Hãy chạy FastAPI: uvicorn src.main:app --reload"
        )

    except requests.exceptions.Timeout:
        raise BackendError(
            "Backend phản hồi quá lâu. Vui lòng thử lại."
        )

    except requests.exceptions.RequestException as e:
        raise BackendError(f"Lỗi khi gọi Backend: {e}")

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", "")
        except (ValueError, AttributeError):
            detail = resp.text

        raise BackendError(
            f"Backend trả về lỗi {resp.status_code}. {detail}".strip()
        )

    if raw:
        return resp.content

    try:
        return resp.json()
    except ValueError:
        raise BackendError("Backend trả về dữ liệu JSON không hợp lệ.")


# =====================================================
# 1. DANH SÁCH BATCH
# =====================================================

def fetch_batches():
    """
    GET /batches
    Lấy danh sách tất cả các lần phân tích.
    """

    data = _get("/batches")

    if not isinstance(data, dict) or "batches" not in data:
        raise BackendError(
            "Response của /batches thiếu trường 'batches'."
        )

    return data["batches"]


def completed_batches(batches):
    """Lọc các Batch đã hoàn thành."""

    df = pd.DataFrame(batches)

    if df.empty or "status" not in df.columns:
        return pd.DataFrame(
            columns=["batch_id", "created_at", "total_reviews"]
        )

    df = df[df["status"] == "Completed"].copy()

    if "created_at" in df.columns:
        df = df.sort_values(
            "created_at",
            ascending=False
        )

    return df.reset_index(drop=True)


def status_counts(batches):
    """Đếm số Batch theo trạng thái."""

    counts = {}

    for batch in batches:
        status = batch.get("status")
        counts[status] = counts.get(status, 0) + 1

    return counts


# =====================================================
# 2. DỮ LIỆU DASHBOARD
# =====================================================

def fetch_dashboard_summary():
    """
    GET /dashboard/summary

    Lấy dữ liệu tổng hợp từ tất cả Batch Completed.
    """

    data = _get("/dashboard/summary")

    if not isinstance(data, dict):
        raise BackendError(
            "Dữ liệu Dashboard tổng hợp không hợp lệ."
        )

    return data


def fetch_dashboard(batch_id):
    """
    GET /dashboard/{batch_id}

    Lấy dữ liệu Dashboard của một Batch cụ thể.
    """

    return _get(f"/dashboard/{batch_id}")


def fetch_export(batch_id):
    """
    GET /batches/{batch_id}/export

    Tải dữ liệu kết quả của một Batch.
    """

    return _get(
        f"/batches/{batch_id}/export",
        raw=True
    )


# =====================================================
# 3. CHUẨN HÓA DỮ LIỆU DASHBOARD
# =====================================================

def parse_dashboard(payload):
    """
    Chuẩn hóa dữ liệu Backend trả về
    để sử dụng chung cho Dashboard tổng hợp
    và Dashboard của một Batch.
    """

    required_keys = [
        "batch",
        "results",
        "overall_statistics",
        "aspect_statistics"
    ]

    if not isinstance(payload, dict):
        raise BackendError(
            "Dữ liệu Dashboard không đúng định dạng."
        )

    for key in required_keys:
        if key not in payload:
            raise BackendError(
                f"Response của Dashboard thiếu trường '{key}'."
            )

    if not isinstance(payload["batch"], dict):
        raise BackendError("Thông tin Batch không hợp lệ.")

    if not isinstance(payload["results"], list):
        raise BackendError("Danh sách kết quả không hợp lệ.")

    if not isinstance(payload["overall_statistics"], dict):
        raise BackendError("Thống kê cảm xúc không hợp lệ.")

    if not isinstance(payload["aspect_statistics"], dict):
        raise BackendError("Thống kê khía cạnh không hợp lệ.")

    results = payload["results"]

    raw = (
        pd.DataFrame(results)
        if results
        else pd.DataFrame(columns=RESULT_COLUMNS)
    )

    # Kiểm tra các cột cần thiết
    missing_columns = [
        col for col in RESULT_COLUMNS
        if col not in raw.columns
    ]

    if missing_columns:
        raise BackendError(
            "Dữ liệu kết quả thiếu các cột: "
            + ", ".join(missing_columns)
        )

    raw = raw[RESULT_COLUMNS].copy()

    # Chuẩn hóa mã cảm xúc
    overall = {}

    for key, value in payload["overall_statistics"].items():
        overall[int(key)] = int(value)

    backend_stats = {
        "overall": overall,
        "aspects": payload["aspect_statistics"],
        "total_reviews": payload["batch"].get("total_reviews"),
        "total_batches": payload.get("total_batches")
    }

    return payload["batch"], raw, backend_stats


# =====================================================
# 4. ĐỐI CHIẾU SỐ LIỆU DASHBOARD VỚI BACKEND
# =====================================================

def compare_with_backend(tbl, ov, backend_stats):
    """
    So sánh thống kê trên giao diện Dashboard
    với số liệu do Backend trả về.
    """

    from dashboard_stats import ASPECT_NAMES

    diffs = []

    name_to_code = {
        value: key
        for key, value in ASPECT_NAMES.items()
    }

    cols = {
        "Tích cực": "Positive",
        "Tiêu cực": "Negative",
        "Trung lập": "Neutral",
        "Không đề cập": "Absent"
    }

    # Kiểm tra từng khía cạnh
    for _, row in tbl.iterrows():

        code = name_to_code.get(row["Khía cạnh"])

        aspects = backend_stats["aspects"]

        # Hỗ trợ key dạng số, chuỗi số hoặc tên khía cạnh
        stats = aspects.get(code)

        if stats is None:
            stats = aspects.get(str(code))

        if stats is None:
            stats = aspects.get(row["Khía cạnh"])

        if stats is None:
            diffs.append(
                f"{row['Khía cạnh']}: "
                "Backend không có thống kê."
            )
            continue

        for vi, en in cols.items():

            dashboard_value = int(row[vi])
            backend_value = int(stats.get(en, 0))

            if dashboard_value != backend_value:
                diffs.append(
                    f"{row['Khía cạnh']} {vi}: "
                    f"Dashboard {dashboard_value}, "
                    f"Backend {backend_value}"
                )

    # Kiểm tra tổng số cảm xúc
    backend_overall = backend_stats["overall"]

    for key, code in (
        ("pos", 1),
        ("neg", 2),
        ("neu", 3)
    ):

        dashboard_value = int(ov[key])
        backend_value = backend_overall.get(code, 0)

        if dashboard_value != backend_value:
            diffs.append(
                f"Tổng {key}: Dashboard {dashboard_value}, "
                f"Backend {backend_value}"
            )

    # Kiểm tra tổng số bình luận
    total = backend_stats.get("total_reviews")

    if total is not None:
        if int(ov["reviews"]) != int(total):
            diffs.append(
                f"Số bình luận: Dashboard {int(ov['reviews'])}, "
                f"Backend {total}"
            )

    return diffs
def fetch_dashboard_summary():
    """
    Lấy dữ liệu Dashboard tổng hợp
    từ tất cả Batch đã Completed.
    """
    return _get("/dashboard/summary")