"""Quy tắc thống kê của Dashboard (không phụ thuộc Streamlit, dễ kiểm thử).

Quy ước:
- Nhãn: 0 = Không đề cập, 1 = Tích cực, 2 = Tiêu cực, 3 = Trung lập.
- Tỷ lệ cảm xúc của một khía cạnh = số nhãn đó / (tích cực + tiêu cực + trung lập). KHÔNG tính nhãn 0 vào mẫu số.
- Tổng số bình luận = số review_id khác nhau; tổng lượt đề cập có thể lớn hơn vì một bình luận nêu nhiều khía cạnh.
"""
import pandas as pd

ASPECT_NAMES = {
    "FOOD#QUALITY": "Chất lượng món ăn", "FOOD#PRICES": "Giá món ăn",
    "FOOD#STYLE&OPTIONS": "Phong cách và sự đa dạng món ăn", "DRINKS#QUALITY": "Chất lượng đồ uống",
    "DRINKS#PRICES": "Giá đồ uống", "DRINKS#STYLE&OPTIONS": "Phong cách và sự đa dạng đồ uống",
    "RESTAURANT#GENERAL": "Đánh giá chung", "RESTAURANT#PRICES": "Mức giá chung",
    "RESTAURANT#MISCELLANEOUS": "Các yếu tố khác", "SERVICE#GENERAL": "Chất lượng phục vụ",
    "AMBIENCE#GENERAL": "Không gian", "LOCATION#GENERAL": "Vị trí nhà hàng",
}
SENTIMENT_NAMES = {0: "Không đề cập", 1: "Tích cực", 2: "Tiêu cực", 3: "Trung lập"}
REQUIRED = ["batch_id", "review_id", "Review", "Aspect", "Sentiment"]


def validate(df):
    """Trả về danh sách lỗi (rỗng nếu dữ liệu hợp lệ). Có lỗi thì Dashboard không hiển thị số liệu."""
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        return [f"Thiếu cột bắt buộc: {', '.join(miss)}"]
    if df.empty:
        return ["File không có dữ liệu."]
    errs = []
    bad_a = sorted(set(df["Aspect"]) - set(ASPECT_NAMES))
    if bad_a:
        errs.append(f"Khía cạnh không hợp lệ: {', '.join(map(str, bad_a))}")
    if not pd.to_numeric(df["Sentiment"], errors="coerce").isin([0, 1, 2, 3]).all():
        errs.append("Cột Sentiment chỉ được nhận giá trị 0, 1, 2, 3.")
    if errs:
        return errs
    g = df.groupby(["batch_id", "review_id"])["Aspect"]
    bad = g.size()[(g.size() != 12) | (g.nunique() != 12)]
    if len(bad):
        ex = ", ".join(f"{b}/{r}" for b, r in list(bad.index[:3]))
        errs.append(f"{len(bad)} bình luận không có đúng 12 khía cạnh khác nhau (ví dụ: {ex}).")
    return errs


def aspect_table(df):
    """Bảng thống kê theo 12 khía cạnh. Tỷ lệ là NaN nếu khía cạnh chưa được nhắc tới (tránh chia cho 0)."""
    d = df.assign(Sentiment=df["Sentiment"].astype(int))
    c = (d.groupby(["Aspect", "Sentiment"]).size().unstack(fill_value=0)
           .reindex(index=list(ASPECT_NAMES), columns=[0, 1, 2, 3], fill_value=0))
    t = pd.DataFrame({"Khía cạnh": [ASPECT_NAMES[a] for a in c.index]}, index=c.index)
    t["Tích cực"], t["Tiêu cực"], t["Trung lập"] = c[1], c[2], c[3]
    t["Lượt đề cập"] = c[1] + c[2] + c[3]
    t["Không đề cập"] = c[0]
    for col, name in [("Tích cực", "% Tích cực"), ("Tiêu cực", "% Tiêu cực"), ("Trung lập", "% Trung lập")]:
        t[name] = (t[col] / t["Lượt đề cập"].where(t["Lượt đề cập"] > 0) * 100).round(1)
    return t


def overall(df):
    """Số liệu tổng quan cho các ô KPI."""
    d = df.assign(Sentiment=df["Sentiment"].astype(int))
    m = d[d["Sentiment"] > 0]
    cnt = m["Sentiment"].value_counts()
    n = len(m)
    return {
        "reviews": d.groupby(["batch_id", "review_id"]).ngroups,
        "mentions": n,
        "pos": int(cnt.get(1, 0)), "neg": int(cnt.get(2, 0)), "neu": int(cnt.get(3, 0)),
        "pos_rate": round(float(cnt.get(1, 0)) / n * 100, 1) if n else None,
    }


def strengths_weaknesses(t, min_mentions=10, k=3):
    """Khía cạnh mạnh/yếu theo % tích cực; bỏ qua khía cạnh quá ít lượt đề cập (kết quả không đáng tin)."""
    ok = t[t["Lượt đề cập"] >= min_mentions].sort_values("% Tích cực", ascending=False)
    return ok.head(k), ok.tail(k).iloc[::-1]
