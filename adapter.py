import json
import pandas as pd


def read_json(src):
    # src là đường dẫn file hoặc file tải lên; xử lý cả file có BOM (UTF-8-SIG)
    raw = src.read() if hasattr(src, "read") else open(src, "rb").read()
    return json.loads(raw.decode("utf-8-sig"))


def completed_batches(obj):
    # Danh sách batch Completed (mới nhất trước). Batch Failed hoặc đang xử lý bị loại
    df = pd.DataFrame(obj.get("batches", []))
    if df.empty or "status" not in df.columns:
        return df
    df = df[df["status"] == "Completed"]
    return df.sort_values("created_at", ascending=False).reset_index(drop=True)


def parse_dashboard(obj):
    # Trả về (thông tin batch, bảng kết quả, thống kê backend theo khía cạnh)
    if obj.get("status") != "success":
        raise ValueError("Backend trả về trạng thái không thành công.")
    return obj["batch"], pd.DataFrame(obj["results"]), obj.get("aspect_statistics", {})


def compare_with_backend(tbl, backend):
    # Đối chiếu số đếm dashboard tự tính với thống kê của backend; rỗng nghĩa là khớp
    pairs = [("Tích cực", "Positive"), ("Tiêu cực", "Negative"), ("Trung lập", "Neutral"), ("Không đề cập", "Absent")]
    out = []
    for asp, s in backend.items():
        if asp not in tbl.index:
            out.append(f"{asp}: không có trong dashboard")
            continue
        for mine, theirs in pairs:
            if int(tbl.loc[asp, mine]) != int(s.get(theirs, -1)):
                out.append(f"{asp} / {theirs}: backend {s.get(theirs)} khác dashboard {int(tbl.loc[asp, mine])}")
    return out