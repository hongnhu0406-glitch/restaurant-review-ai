import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard_stats import (ASPECT_NAMES, SENTIMENT_NAMES, aspect_table, overall,
                             strengths_weaknesses, validate)
from adapter import compare_with_backend, completed_batches, parse_dashboard, read_json

st.set_page_config(page_title="Dashboard phân tích đánh giá nhà hàng", layout="wide")
COLORS = {"Tích cực": "#2E9E6B", "Tiêu cực": "#D9534F", "Trung lập": "#9AA0A6"}
BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(BASE, "data", "sample_results.csv")
DIR = os.path.join(BASE, "Dữ liệu")


@st.cache_data
def load_csv(src):
    return pd.read_csv(src, encoding="utf-8-sig")


@st.cache_data
def load_json(src):
    return read_json(src)


def pick_json(name):
    # Ưu tiên file trong data/duc/, không có thì cho tải lên
    path = os.path.join(DIR, name)
    if os.path.exists(path):
        return path
    return st.sidebar.file_uploader(f"Tải {name}", type=["json"], key=name)


# ---------- Nguồn dữ liệu ----------
st.title("Dashboard phân tích đánh giá nhà hàng")
backend_stats, batch_labels = None, {}
with st.sidebar:
    st.header("Dữ liệu")
    try:
        fb, fd = pick_json("batches.json"), pick_json("dashboard.json")
        if fb is None or fd is None:
            st.info("Chưa có dữ liệu phân tích. Hãy đặt batches.json và dashboard.json vào thư mục Dữ liệu hoặc tải lên.")
            st.stop()
        bt = completed_batches(load_json(fb))
        binfo, raw, backend_stats = parse_dashboard(load_json(fd))
        batches = list(bt["batch_id"]) if not bt.empty else []
        batch_labels = {r.batch_id: f"{r.batch_id} · {r.created_at} · {r.total_reviews} bình luận"
                        for r in bt.itertuples()}
    except Exception as e:
        st.error(f"Không đọc được dữ liệu: {e}")
        st.stop()

errs = validate(raw)
if errs:  # lỗi dữ liệu: không hiển thị số liệu hay biểu đồ
    st.error("Dữ liệu không hợp lệ, không thể hiển thị Dashboard:")
    for e in errs:
        st.write("- " + e)
    st.stop()

raw["Sentiment"] = pd.to_numeric(raw["Sentiment"]).astype(int)
if "status" in raw.columns:  # chỉ batch hoàn thành mới được thống kê
    raw = raw[raw["status"].isin(["Hoàn thành", "Completed"])]
    if raw.empty:
        st.warning("Chưa có batch nào ở trạng thái hoàn thành.")
        st.stop()

# ---------- Bộ lọc ----------
if not batches:
    st.warning("Chưa có batch nào ở trạng thái Completed.")
    st.stop()
default = batches.index(binfo["batch_id"]) if binfo["batch_id"] in batches else 0
with st.sidebar:
    batch = st.selectbox("Lần phân tích (batch)", batches, index=default,
                         format_func=lambda b: batch_labels.get(b, b))
    show_empty = st.checkbox("Hiển thị cả khía cạnh chưa được đề cập", value=False)
    min_m = st.number_input("Số lượt đề cập tối thiểu để xếp hạng mạnh/yếu", 1, 100, 10)

df = raw[raw["batch_id"] == batch]
if df.empty:  # batch có trong danh sách nhưng chưa có file kết quả
    have = ", ".join(dict.fromkeys(raw["batch_id"]))
    st.warning(f"Chưa có dữ liệu kết quả của batch {batch}. File kết quả hiện chỉ chứa: {have}.")
    st.stop()
tbl = aspect_table(df)
ov = overall(df)
shown = tbl if show_empty else tbl[tbl["Lượt đề cập"] > 0]
if backend_stats is not None:  # đối chiếu số liệu tự tính với thống kê của backend
    diff = compare_with_backend(tbl, backend_stats)
    if diff:
        st.warning("Số liệu dashboard lệch với thống kê của backend, cần hỏi lại Đức: " + "; ".join(diff[:5]))

# ---------- KPI ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tổng số bình luận", f"{ov['reviews']:,}")
c2.metric("Tổng lượt đề cập khía cạnh", f"{ov['mentions']:,}",
          help="Một bình luận có thể nhắc nhiều khía cạnh nên con số này có thể lớn hơn tổng số bình luận.")
c3.metric("Tỷ lệ tích cực chung", f"{ov['pos_rate']}%" if ov["pos_rate"] is not None else "—")
c4.metric("Khía cạnh được nhắc tới", f"{(tbl['Lượt đề cập'] > 0).sum()}/12")
st.caption("Tỷ lệ cảm xúc = số lượt cảm xúc đó ÷ số lượt đề cập của khía cạnh. "
           "Nhãn \"Không đề cập\" không tính vào tỷ lệ và được hiển thị riêng.")

# ---------- Tổng quan ----------
left, right = st.columns([1, 1.4])
with left:
    st.subheader("Cơ cấu cảm xúc chung")
    fig = go.Figure(go.Pie(labels=list(COLORS), values=[ov["pos"], ov["neg"], ov["neu"]], hole=.55,
                           marker_colors=list(COLORS.values()), sort=False, textinfo="percent+value"))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, legend=dict(orientation="h", y=-0.05))
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("Điểm mạnh và điểm cần cải thiện")
    top, low = strengths_weaknesses(tbl, int(min_m))
    if top.empty:
        st.info(f"Chưa có khía cạnh nào đạt tối thiểu {int(min_m)} lượt đề cập để xếp hạng.")
    else:
        a, b = st.columns(2)
        a.markdown("**Nên phát huy**")
        for _, r in top.iterrows():
            a.write(f"{r['Khía cạnh']}: **{r['% Tích cực']}%** tích cực ({int(r['Lượt đề cập'])} lượt)")
        b.markdown("**Cần cải thiện**")
        for _, r in low.iterrows():
            b.write(f"{r['Khía cạnh']}: **{r['% Tích cực']}%** tích cực ({int(r['Lượt đề cập'])} lượt)")
    st.caption(f"Chỉ xếp hạng các khía cạnh có từ {int(min_m)} lượt đề cập trở lên.")

# ---------- Biểu đồ theo 12 khía cạnh ----------
st.subheader("Cảm xúc theo từng khía cạnh")
order = shown.sort_values("Lượt đề cập")  # nhiều lượt đề cập nằm trên cùng
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Số lượng**")
    f1 = go.Figure([go.Bar(name=k, y=order["Khía cạnh"], x=order[k], orientation="h", marker_color=v)
                    for k, v in COLORS.items()])
    f1.update_layout(barmode="stack", height=max(320, 32 * len(order) + 90), margin=dict(t=10, b=10),
                     legend=dict(orientation="h", y=1.08), xaxis_title="Số lượt đề cập")
    st.plotly_chart(f1, width="stretch")
with col_b:
    st.markdown("**Tỷ lệ (%)**")
    ment = order[order["Lượt đề cập"] > 0]
    f2 = go.Figure([go.Bar(name=k, y=ment["Khía cạnh"], x=ment[f"% {k}"], orientation="h", marker_color=v,
                           text=ment[f"% {k}"].round(0).astype(int).astype(str) + "%", textposition="inside")
                    for k, v in COLORS.items()])
    f2.update_layout(barmode="stack", height=max(320, 32 * len(ment) + 90), margin=dict(t=10, b=10),
                     legend=dict(orientation="h", y=1.08), xaxis=dict(range=[0, 100], title="% trên số lượt đề cập"))
    st.plotly_chart(f2, width="stretch")

# ---------- Bảng thống kê ----------
st.subheader("Bảng thống kê chi tiết")
view = shown.reset_index(drop=True)
st.dataframe(view, width="stretch", hide_index=True, column_config={
    "% Tích cực": st.column_config.ProgressColumn("% Tích cực", min_value=0, max_value=100, format="%.1f%%"),
    "% Tiêu cực": st.column_config.NumberColumn(format="%.1f%%"),
    "% Trung lập": st.column_config.NumberColumn(format="%.1f%%")})
st.download_button("Tải bảng thống kê (CSV)", view.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"thong_ke_{batch}.csv", mime="text/csv")

# ---------- Xem bình luận theo khía cạnh ----------
st.subheader("Xem bình luận theo khía cạnh")
x1, x2 = st.columns([1, 1])
asp = x1.selectbox("Khía cạnh", list(ASPECT_NAMES), format_func=lambda k: ASPECT_NAMES[k])
sel = x2.multiselect("Cảm xúc", ["Tích cực", "Tiêu cực", "Trung lập"], default=["Tiêu cực"])
codes = [k for k, v in SENTIMENT_NAMES.items() if v in sel]
rv = df[(df["Aspect"] == asp) & (df["Sentiment"].isin(codes))].copy()
if rv.empty:
    st.info("Không có bình luận nào khớp bộ lọc này.")
else:
    rv["Cảm xúc"] = rv["Sentiment"].map(SENTIMENT_NAMES)
    cols = ["review_id", "Review", "Cảm xúc"] + (["Confidence"] if "Confidence" in rv.columns else [])
    st.dataframe(rv[cols], width="stretch", hide_index=True)