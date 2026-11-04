import os
import pandas as pd
import requests

API_BASE_URL = os.environ.get("RESTAURANT_API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = 15

# Các cột kết quả mà backend trả về (src/constants.py: OUTPUT_COLUMNS)
RESULT_COLUMNS = ["batch_id", "review_id", "Review", "Aspect", "Sentiment", "Confidence"]


class BackendError(Exception):
    """Lỗi khi gọi backend, message đã là tiếng Việt để hiển thị thẳng cho người dùng."""


def _get(path, raw=False):
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
    except requests.exceptions.ConnectionError:
        raise BackendError(f"Không kết nối được Backend tại {API_BASE_URL}. "
                           "Hãy chạy FastAPI: uvicorn src.main:app --reload")
    except requests.exceptions.Timeout:
        raise BackendError("Backend phản hồi quá lâu. Vui lòng thử lại.")
    except requests.exceptions.RequestException as e:
        raise BackendError(f"Lỗi khi gọi Backend: {e}")

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", "")
        except ValueError:
            detail = ""
        raise BackendError(f"Backend trả về lỗi {resp.status_code}. {detail}".strip())
    return resp.content if raw else resp.json()

# 1. DANH SÁCH BATCH
def fetch_batches():
    """GET /batches -> list[dict] gồm batch_id, status, total_reviews, created_at, ..."""
    data = _get("/batches")
    if "batches" not in data:
        raise BackendError("Response của /batches thiếu trường 'batches'.")
    return data["batches"]


def completed_batches(batches):
    df = pd.DataFrame(batches)
    if df.empty or "status" not in df.columns:
        return pd.DataFrame(columns=["batch_id", "created_at", "total_reviews"])
    df = df[df["status"] == "Completed"].copy()
    return df.sort_values("created_at", ascending=False).reset_index(drop=True)


def status_counts(batches):
    counts = {}
    for b in batches:
        counts[b.get("status")] = counts.get(b.get("status"), 0) + 1
    return counts

# 2. DỮ LIỆU DASHBOARD CỦA MỘT BATCH
def fetch_dashboard(batch_id):
    return _get(f"/dashboard/{batch_id}")

def fetch_export(batch_id):
    return _get(f"/batches/{batch_id}/export", raw=True)

def parse_dashboard(payload):
    for key in ("batch", "results", "overall_statistics", "aspect_statistics"):
        if key not in payload:
            raise BackendError(f"Response của /dashboard thiếu trường '{key}'.")

    results = payload["results"]
    raw = pd.DataFrame(results, columns=RESULT_COLUMNS) if results else pd.DataFrame(columns=RESULT_COLUMNS)
    backend_stats = {
        "overall": {int(k): int(v) for k, v in payload["overall_statistics"].items()},
        "aspects": payload["aspect_statistics"],
        "total_reviews": payload["batch"].get("total_reviews"),
    }
    return payload["batch"], raw, backend_stats

# 3. ĐỐI CHIẾU SỐ LIỆU DASHBOARD VỚI BACKEND
def compare_with_backend(tbl, ov, backend_stats):
    from dashboard_stats import ASPECT_NAMES  # import tại đây để tránh import vòng

    diffs = []
    name_to_code = {v: k for k, v in ASPECT_NAMES.items()}
    cols = {"Tích cực": "Positive", "Tiêu cực": "Negative", "Trung lập": "Neutral", "Không đề cập": "Absent"}

    for _, row in tbl.iterrows():
        code = name_to_code.get(row["Khía cạnh"])
        stats = backend_stats["aspects"].get(code)
        if stats is None:
            diffs.append(f"{row['Khía cạnh']}: backend không có thống kê")
            continue
        for vi, en in cols.items():
            if int(row[vi]) != int(stats[en]):
                diffs.append(f"{row['Khía cạnh']} {vi}: dashboard {int(row[vi])}, backend {stats[en]}")

    bo = backend_stats["overall"]
    for key, code in (("pos", 1), ("neg", 2), ("neu", 3)):
        if int(ov[key]) != bo.get(code, 0):
            diffs.append(f"Tổng {key}: dashboard {int(ov[key])}, backend {bo.get(code, 0)}")

    total = backend_stats.get("total_reviews")
    if total is not None and int(ov["reviews"]) != int(total):
        diffs.append(f"Số bình luận: dashboard {int(ov['reviews'])}, batch {total}")
    return diffs