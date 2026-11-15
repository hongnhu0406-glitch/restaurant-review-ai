import html
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from adapter import (
    API_BASE_URL as DASHBOARD_API_BASE_URL,
    BackendError,
    compare_with_backend,
    completed_batches,
    fetch_batches,
    fetch_dashboard,
    parse_dashboard,
    status_counts,
)
from dashboard_stats import (
    ASPECT_NAMES as DASHBOARD_ASPECT_NAMES,
    SENTIMENT_NAMES as DASHBOARD_SENTIMENT_NAMES,
    aspect_table,
    overall,
    strengths_weaknesses,
    validate,
)

# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Restaurant Review AI",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# 2. BACKEND CONFIGURATION
# =========================================================
# Chạy FastAPI trước khi chạy Streamlit. Có thể override bằng biến môi trường.
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = 120

ASPECT_NAMES = {
    "FOOD#QUALITY": "Chất lượng món ăn",
    "FOOD#PRICES": "Giá món ăn",
    "FOOD#STYLE&OPTIONS": "Phong cách chế biến món ăn",
    "DRINKS#QUALITY": "Chất lượng đồ uống",
    "DRINKS#PRICES": "Giá đồ uống",
    "DRINKS#STYLE&OPTIONS": "Phong cách chế biến đồ uống",
    "RESTAURANT#GENERAL": "Đánh giá chung",
    "RESTAURANT#PRICES": "Mức giá chung",
    "RESTAURANT#MISCELLANEOUS": "Các yếu tố khác",
    "SERVICE#GENERAL": "Chất lượng phục vụ",
    "AMBIENCE#GENERAL": "Không gian",
    "LOCATION#GENERAL": "Vị trí nhà hàng",
}
SENTIMENT_NAMES = {
    0: "Không đề cập",
    1: "Tích cực",
    2: "Tiêu cực",
    3: "Trung lập",
}
SENTIMENT_CLASSES = {
    "Tích cực": "positive",
    "Tiêu cực": "negative",
    "Trung lập": "neutral",
    "Không đề cập": "absent",
}
STYLE_TAG_NAMES = {
    "sarcasm": "Mỉa mai",
    "mockery": "Chê bai / giễu cợt",
    "figurative": "Ví von / ẩn dụ",
}


# =========================================================
# 3. API HELPERS
# =========================================================
def api_request(method, endpoint, **kwargs):
    """Gửi request đến FastAPI và chuyển lỗi API thành thông báo dễ hiểu."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.request(
            method,
            url,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Không kết nối được Backend. Hãy chạy FastAPI bằng lệnh "
            "`uvicorn src.main:app --reload` tại thư mục D:\\RESTAURANT_AI."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Backend phản hồi quá lâu. Vui lòng thử lại.")

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"Backend báo lỗi ({response.status_code}): {detail}")

    return response


def sentiment_label(value):
    try:
        return SENTIMENT_NAMES.get(int(value), f"Không xác định ({value})")
    except (TypeError, ValueError):
        return f"Không xác định ({value})"


def prepare_results(results):
    """Chuẩn hóa dữ liệu API để hiển thị bằng tiếng Việt."""
    rows = []
    for item in results:
        aspect = item.get("Aspect", "")
        sentiment = sentiment_label(item.get("Sentiment"))
        confidence = item.get("Confidence")
        rows.append({
            "Khía cạnh": ASPECT_NAMES.get(aspect, aspect),
            "Cảm xúc": sentiment,
            "Độ tin cậy": (
                f"{float(confidence):.0%}"
                if confidence is not None else "—"
            ),
        })
    return rows


def render_results_table(results, key_prefix="results", show_filter=True):
    """Hiển thị bảng kết quả theo đúng phong cách giao diện hiện tại."""
    if not results:
        st.info("Batch này chưa có kết quả để hiển thị.")
        return

    rows = prepare_results(results)
    df = pd.DataFrame(rows)

    if show_filter:
        show_all = st.checkbox(
            "Hiển thị tất cả khía cạnh, kể cả Không đề cập",
            value=False,
            key=f"{key_prefix}_show_all",
        )
        if not show_all:
            df = df[df["Cảm xúc"] != "Không đề cập"]

    if df.empty:
        st.info(
            "Chưa nhận diện được khía cạnh trong đánh giá này. "
            "Hãy thử bổ sung chi tiết về món ăn, giá cả, dịch vụ hoặc không gian."
        )
        return

    st.markdown(
        f'<div class="result-count">Hiển thị {len(df)} kết quả</div>',
        unsafe_allow_html=True,
    )

    table_rows = ""
    for _, item in df.iterrows():
        aspect = html.escape(str(item["Khía cạnh"]))
        sentiment = html.escape(str(item["Cảm xúc"]))
        confidence = html.escape(str(item["Độ tin cậy"]))
        css_class = SENTIMENT_CLASSES.get(item["Cảm xúc"], "absent")
        table_rows += f"""
        <tr>
            <td class="aspect-cell">{aspect}</td>
            <td class="sentiment-cell">
                <span class="sentiment-badge {css_class}">{sentiment}</span>
            </td>
            <td class="confidence-cell">{confidence}</td>
        </tr>
        """

    table_html = f"""
    <div class="result-table-wrapper">
        <table class="result-table">
            <thead>
                <tr><th>Khía cạnh</th><th>Cảm xúc</th><th>Độ tin cậy</th></tr>
            </thead>
            <tbody>{table_rows}</tbody>
        </table>
    </div>
    """
    st.html(table_html)
def render_batch_summary(batch):
    """Hiển thị các trường Batch có trong API response."""
    cols = st.columns(4)
    metrics = [
        ("Tổng số dòng", batch.get("total_rows", "—")),
        ("Đánh giá hợp lệ", batch.get("total_reviews", "—")),
        ("Dòng bỏ qua", batch.get("skipped_rows", "—")),
        ("Tổng kết quả", batch.get("total_results", "—")),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)


def render_feedback_form(result):
    review_id = str(result.get("review_id", ""))
    review = str(result.get("review", ""))
    predictions = {
        item.get("Aspect"): item.get("Sentiment")
        for item in result.get("results", [])
    }

    st.caption(
        "Nhãn chỉ được dùng để học sau khi bạn tự kiểm tra và xác nhận. "
        "Hãy chọn “Không đề cập” nếu bình luận không nhắc đến khía cạnh đó."
    )
    with st.form(key=f"feedback_form_{review_id}"):
        labels = {}
        columns = st.columns(3)
        for index, aspect in enumerate(ASPECT_NAMES):
            prediction = predictions.get(aspect, 0)
            try:
                default_index = int(prediction)
            except (TypeError, ValueError):
                default_index = 0
            if default_index not in SENTIMENT_NAMES:
                default_index = 0
            with columns[index % len(columns)]:
                labels[aspect] = st.selectbox(
                    ASPECT_NAMES[aspect],
                    options=list(SENTIMENT_NAMES),
                    index=list(SENTIMENT_NAMES).index(default_index),
                    format_func=sentiment_label,
                    key=f"feedback_{review_id}_{aspect}",
                )

        style_tags = st.multiselect(
            "Cách diễn đạt được xác nhận",
            options=list(STYLE_TAG_NAMES),
            format_func=lambda tag: STYLE_TAG_NAMES[tag],
            key=f"feedback_style_{review_id}",
        )
        notes = st.text_area(
            "Ghi chú (không bắt buộc)",
            max_chars=1000,
            key=f"feedback_notes_{review_id}",
        )
        confirmed = st.checkbox(
            "Tôi đã kiểm tra và xác nhận đủ 12 nhãn khía cạnh.",
            key=f"feedback_confirmed_{review_id}",
        )
        style_reviewed = st.checkbox(
            "Tôi đã xem xét nhãn mỉa mai / giễu cợt / ví von.",
            key=f"feedback_style_reviewed_{review_id}",
        )
        submitted = st.form_submit_button(
            "Lưu phản hồi đã xác nhận",
            use_container_width=True,
        )

    if submitted:
        try:
            response = api_request(
                "POST",
                "/learning/feedback",
                json={
                    "review_id": review_id,
                    "review": review,
                    "labels": labels,
                    "style_tags": style_tags,
                    "notes": notes,
                    "confirmed": confirmed,
                    "style_reviewed": style_reviewed,
                },
            ).json()
            st.session_state[f"feedback_saved_{review_id}"] = bool(
                response.get("saved")
            )
        except RuntimeError as error:
            st.error(str(error))

    if st.session_state.get(f"feedback_saved_{review_id}"):
        st.success(
            "Đã lưu nhãn người dùng xác nhận. Nhãn này sẽ được đưa vào "
            "tập huấn luyện có kiểm định."
        )


# =========================================================
# 3A. DASHBOARD HELPERS (INTEGRATED)
# =========================================================
COLORS = {"Tích cực": "#68765D", "Tiêu cực": "#A65D50", "Trung lập": "#D4BE96"}
BADGE_CLASS = {"Tích cực": "positive", "Tiêu cực": "negative", "Trung lập": "neutral"}


def style_fig(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(t=30, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro, Arial, sans-serif", color="#2F2925", size=12),
        legend=dict(orientation="h", y=1.1, x=0.02),
        hoverlabel=dict(font_family="Be Vietnam Pro, Arial, sans-serif"),
    )
    fig.update_xaxes(gridcolor="#EAD9C6", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True)
    return fig


def pct(v):
    return "—" if pd.isna(v) else f"{v:.1f}%"


def width(v):
    return 0 if pd.isna(v) else max(0, min(100, float(v)))


def stats_table_html(data, compact=False):
    rows = ""
    for _, r in data.sort_values("Lượt đề cập", ascending=False).iterrows():
        mix = (
            '<span class="dim">—</span>'
            if r["Lượt đề cập"] == 0
            else (
                '<div class="mix-wrap"><div class="mix">'
                f'<i class="p" style="width:{width(r["% Tích cực"])}%"></i>'
                f'<i class="n" style="width:{width(r["% Tiêu cực"])}%"></i>'
                f'<i class="u" style="width:{width(r["% Trung lập"])}%"></i>'
                "</div><span>"
                f"{pct(r['% Tích cực'])}</span></div>"
            )
        )
        rows += (
            f'<tr><td><b>{html.escape(str(r["Khía cạnh"]))}</b></td>'
            f'<td class="num pos-n">{int(r["Tích cực"])}</td>'
            f'<td class="num neg-n">{int(r["Tiêu cực"])}</td>'
            f'<td class="num neu-n">{int(r["Trung lập"])}</td>'
            f'<td class="num">{int(r["Lượt đề cập"])}</td>'
        )
        if not compact:
            rows += f'<td class="num dim">{int(r["Không đề cập"])}</td>'
        rows += f'<td>{mix}</td>'
        if not compact:
            rows += f'<td class="num">{pct(r["% Tiêu cực"])}</td><td class="num">{pct(r["% Trung lập"])}</td>'
        rows += "</tr>"

    head = (
        "<th>Khía cạnh</th><th>Tích cực</th><th>Tiêu cực</th><th>Trung lập</th><th>Lượt đề cập</th>"
        + ("" if compact else "<th>Không đề cập</th>")
        + "<th>Tỷ lệ tích cực</th>"
        + ("" if compact else "<th>% Tiêu cực</th><th>% Trung lập</th>")
    )
    return (
        '<div class="tbl-wrap"><table class="tbl"><thead><tr>'
        f"{head}</tr></thead><tbody>{rows}</tbody></table></div>"
    )


@st.cache_data(ttl=30, show_spinner=False)
def load_batch_list():
    return fetch_batches()


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_batch(batch_id):
    return fetch_dashboard(batch_id)


def render_dashboard_panel():
    st.markdown(
        """
        <div class="dashboard-shell">
            <div class="panel-heading">
                <div class="section-kicker">Dashboard</div>
                <div class="section-title">Biểu đồ và phân bổ cảm xúc</div>
                <div class="section-description">
                    Thống kê từ các batch đã hoàn tất, theo khía cạnh và cảm xúc của đánh giá nhà hàng.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        with st.spinner("Đang tải danh sách batch từ backend..."):
            batches = load_batch_list()
    except BackendError as error:
        st.error(str(error))
        st.caption(f"Địa chỉ API đang dùng: {DASHBOARD_API_BASE_URL}")
        if st.button("Thử kết nối lại"):
            st.cache_data.clear()
            st.rerun()
        return

    completed = completed_batches(batches)
    counts = status_counts(batches)
    if completed.empty:
        st.warning("Chưa có batch nào ở trạng thái Completed. Hãy phân tích một bình luận hoặc CSV ở các tab khác.")
        return

    batch_ids = list(completed["batch_id"])
    labels = {
        row.batch_id: f"{row.batch_id} · {row.created_at} · {row.total_reviews} bình luận"
        for row in completed.itertuples()
    }
    batch_col, count_col, empty_col, reload_col = st.columns([2.2, 1.1, 1.1, 0.8], gap="large")
    batch_id = batch_col.selectbox("Lần phân tích (batch)", batch_ids, format_func=lambda b: labels.get(b, b))
    min_mentions = count_col.number_input("Số lượt đề cập tối thiểu", min_value=1, max_value=100, value=10)
    show_empty = empty_col.checkbox("Hiện khía cạnh chưa đề cập", value=False)
    if reload_col.button("Tải lại", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if counts.get("Processing") or counts.get("Failed"):
        note = []
        if counts.get("Processing"):
            note.append(f"{counts['Processing']} batch đang xử lý")
        if counts.get("Failed"):
            note.append(f"{counts['Failed']} batch thất bại")
        st.caption(" · ".join(note) + " (không đưa vào thống kê).")

    try:
        with st.spinner("Đang tải thống kê của batch..."):
            batch_info, raw, backend_stats = parse_dashboard(load_dashboard_batch(batch_id))
    except BackendError as error:
        st.error(str(error))
        return

    errors = validate(raw)
    if errors:
        st.error("Dữ liệu không hợp lệ, không thể hiển thị Dashboard:")
        for entry in errors:
            st.write("- " + entry)
        return

    raw["Sentiment"] = pd.to_numeric(raw["Sentiment"]).astype(int)
    df = raw[raw["batch_id"] == batch_id]
    if df.empty:
        st.warning(f"Chưa có dữ liệu kết quả của batch {batch_id}.")
        return

    tbl = aspect_table(df)
    ov = overall(df)
    shown = tbl if show_empty else tbl[tbl["Lượt đề cập"] > 0]
    diff = compare_with_backend(tbl, ov, backend_stats)
    if diff:
        st.warning("Số liệu dashboard lệch với thống kê backend: " + "; ".join(diff[:5]))

    top, low = strengths_weaknesses(tbl, int(min_mentions))
    if not top.empty and not low.empty:
        best = top.iloc[0]
        worst = low.iloc[0]
        st.markdown(
            f"""
            <div class="insight">
              <div class="insight-item good">
                <div class="insight-icon">↑</div>
                <div class="insight-text">Được khen nhiều nhất<b>{html.escape(str(best['Khía cạnh']))}</b>{best['% Tích cực']:.1f}% tích cực trên {int(best['Lượt đề cập'])} lượt</div>
              </div>
              <div class="insight-item bad">
                <div class="insight-icon">↓</div>
                <div class="insight-text">Cần chú ý nhất<b>{html.escape(str(worst['Khía cạnh']))}</b>chỉ {worst['% Tích cực']:.1f}% tích cực trên {int(worst['Lượt đề cập'])} lượt</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    k1.markdown(
        f'<div class="kpi"><div class="kpi-label">Tổng số bình luận</div><div class="kpi-value">{ov["reviews"]:,}</div><div class="kpi-note">Số review_id khác nhau</div></div>',
        unsafe_allow_html=True,
    )
    k2.markdown(
        f'<div class="kpi"><div class="kpi-label">Lượt đề cập khía cạnh</div><div class="kpi-value">{ov["mentions"]:,}</div><div class="kpi-note">Một bình luận có thể nhắc nhiều khía cạnh</div></div>',
        unsafe_allow_html=True,
    )
    k3.markdown(
        f'<div class="kpi"><div class="kpi-label">Tỷ lệ tích cực chung</div><div class="kpi-value">{ov["pos_rate"]:.1f}%</div><div class="kpi-note">Không tính “Không đề cập”</div></div>' if ov["pos_rate"] is not None else '<div class="kpi"><div class="kpi-label">Tỷ lệ tích cực chung</div><div class="kpi-value">—</div><div class="kpi-note">Không tính “Không đề cập”</div></div>',
        unsafe_allow_html=True,
    )
    k4.markdown(
        f'<div class="kpi"><div class="kpi-label">Khía cạnh được nhắc tới</div><div class="kpi-value">{int((tbl["Lượt đề cập"] > 0).sum())}/12</div><div class="kpi-note">Trên tổng 12 khía cạnh</div></div>',
        unsafe_allow_html=True,
    )

    order = shown.sort_values("Lượt đề cập")
    mentions = order[order["Lượt đề cập"] > 0]

    def pie_chart():
        fig = go.Figure(
            go.Pie(
                labels=["Tích cực", "Tiêu cực", "Trung lập"],
                values=[ov["pos"], ov["neg"], ov["neu"]],
                hole=0.66,
                sort=False,
                marker=dict(colors=[COLORS[k] for k in ["Tích cực", "Tiêu cực", "Trung lập"]], line=dict(color="#FBF1E4", width=3)),
                textinfo="percent",
                textfont=dict(size=13, color="#FFFFFF"),
                hovertemplate="%{label}: %{value} lượt (%{percent})<extra></extra>",
            )
        )
        fig.add_annotation(
            text=f"<b style='font-size:30px;color:#552824'>{ov['mentions']:,}</b><br>lượt đề cập",
            showarrow=False,
            font=dict(size=12, color="#6F6258"),
        )
        return style_fig(fig, 360).update_layout(
            margin=dict(t=70, b=40, l=10, r=10),
            legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        )

    def nice_step(mx):
        raw = max(1, -(-int(mx) // 6))
        for step in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000):
            if step >= raw:
                return step
        return raw

    def counts_chart():
        fig = go.Figure(
            [
                go.Bar(
                    name=k,
                    y=order["Khía cạnh"],
                    x=order[k],
                    orientation="h",
                    marker_color=v,
                    hovertemplate="%{y}<br>" + k + ": %{x} lượt<extra></extra>",
                )
                for k, v in COLORS.items()
            ]
        )
        mx = int(order[["Tích cực", "Tiêu cực", "Trung lập"]].sum(axis=1).max()) if len(order) else 1
        fig.update_layout(barmode="stack", xaxis_title="Số lượt đề cập", bargap=0.35)
        fig = style_fig(fig, max(340, 40 * len(order) + 100))
        return fig.update_xaxes(dtick=nice_step(mx), tickformat="d", rangemode="tozero")

    def percent_chart():
        fig = go.Figure(
            [
                go.Bar(
                    name=k,
                    y=mentions["Khía cạnh"],
                    x=mentions[f"% {k}"],
                    orientation="h",
                    marker_color=v,
                    text=mentions[f"% {k}"].round(0).astype(int).astype(str) + "%",
                    textposition="inside",
                    textfont=dict(color="#FFFFFF" if k != "Trung lập" else "#5B4A2A"),
                    hovertemplate="%{y}<br>" + k + ": %{x:.1f}%<extra></extra>",
                )
                for k, v in COLORS.items()
            ]
        )
        fig.update_layout(barmode="stack", xaxis=dict(range=[0, 100], title="% trên số lượt đề cập"), bargap=0.35)
        fig = style_fig(fig, max(340, 40 * len(mentions) + 100))
        fig.update_layout(margin=dict(t=30, b=10, l=10, r=30))
        return fig.update_xaxes(tickmode="array", tickvals=[0, 20, 40, 60, 80, 100], ticktext=[f"{t}%" for t in [0, 20, 40, 60, 80, 100]])

    overview_mode = st.radio("Kiểu hiển thị", ["Số lượt đề cập", "Phần trăm"], horizontal=True)
    chart_col, summary_col = st.columns([1.2, 1])
    with chart_col:
        st.plotly_chart(pie_chart(), use_container_width=True)
    with summary_col:
        st.plotly_chart(counts_chart() if overview_mode == "Số lượt đề cập" else percent_chart(), use_container_width=True)

    st.markdown("<div class='section-kicker' style='margin-top:1.5rem;'>Bảng khảo sát</div>", unsafe_allow_html=True)
    st.markdown(stats_table_html(shown, compact=True), unsafe_allow_html=True)

    st.markdown("<div class='section-kicker' style='margin-top:1.5rem;'>Bình luận theo khía cạnh</div>", unsafe_allow_html=True)
    aspect_select = st.selectbox("Khía cạnh", list(DASHBOARD_ASPECT_NAMES), format_func=lambda k: DASHBOARD_ASPECT_NAMES[k])
    sentiment_filter = st.multiselect("Cảm xúc", ["Tích cực", "Tiêu cực", "Trung lập"], default=["Tiêu cực"])
    codes = [k for k, v in DASHBOARD_SENTIMENT_NAMES.items() if v in sentiment_filter]
    review_subset = df[(df["Aspect"] == aspect_select) & (df["Sentiment"].isin(codes))]
    if review_subset.empty:
        st.info("Không có bình luận nào khớp bộ lọc hiện tại.")
    else:
        cards = ""
        for item in review_subset.head(50).itertuples():
            sentiment_name = DASHBOARD_SENTIMENT_NAMES[item.Sentiment]
            conf = f"{float(item.Confidence):.0%}" if pd.notna(getattr(item, "Confidence", None)) else "—"
            cards += (
                f'<div class="rv {BADGE_CLASS.get(sentiment_name, "neutral")}"><div class="rv-head"><span class="rv-id">{html.escape(str(item.review_id))}</span>'
                f'<span><span class="badge {BADGE_CLASS.get(sentiment_name, "neutral")}">{sentiment_name}</span><span class="rv-conf">Tin cậy {conf}</span></span></div>'
                f'<div class="rv-body">{html.escape(str(item.Review))}</div></div>'
            )
        st.html(cards)
        st.caption(f"Hiển thị {min(50, len(review_subset))} / {len(review_subset)} bình luận.")


# =========================================================
# 4. DESIGN SYSTEM — GIỮ PHONG CÁCH LONG TRIỀU
# =========================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Lato:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">

<style>
:root {
    --ivory:#F5F0E7; --paper:#FFFEFC; --burgundy:#552824;
    --burgundy-deep:#351B19; --wine:#87443B; --gold:#B18A4E;
    --gold-light:#D4BE96; --ink:#2F2925; --muted:#6F6258;
    --line:#DCCFBD; --sage:#68765D; --rose:#A65D50;
}
html, body, [class*="css"], .stApp {
    font-family:'Lato',sans-serif !important; color:var(--ink); font-weight:400;
}
.stApp, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 420px 250px at -40px -50px,
            transparent 58%, rgba(199,151,91,.34) 58.4%, transparent 59%,
            transparent 68%, rgba(199,151,91,.18) 68.4%, transparent 69%),
        radial-gradient(ellipse 460px 270px at calc(100% + 45px) calc(100% + 55px),
            transparent 58%, rgba(199,151,91,.30) 58.4%, transparent 59%,
            transparent 68%, rgba(199,151,91,.16) 68.4%, transparent 69%),
        radial-gradient(ellipse at 12% 5%, rgba(222,177,125,.22), transparent 34rem),
        radial-gradient(ellipse at 92% 48%, rgba(204,151,105,.12), transparent 32rem),
        #F8F1E8 !important;
    background-attachment:scroll !important;
}
[data-testid="stHeader"] {background:transparent;}
#MainMenu, footer, .stDeployButton {visibility:hidden;}
.block-container {
    max-width:1500px !important; padding-top:0.7rem !important;
    padding-bottom:2.4rem !important; position:relative;
}
.topline {
    display:flex; justify-content:space-between; gap:1rem;
    border-top:1px solid var(--gold); border-bottom:1px solid var(--line);
    padding:12px 0; margin-bottom:2.2rem; color:var(--muted);
    font-size:10px; font-weight:700; letter-spacing:2.2px; text-transform:uppercase;
}
.topline .brand-mark {color:var(--burgundy); letter-spacing:3px;}
.hero {
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    width:100%; max-width:100%; box-sizing:border-box;
    padding:0.7rem 0 1.45rem; text-align:center !important;
}
.eyebrow {
    color:var(--gold); font-size:10px; font-weight:900;
    letter-spacing:4px; text-transform:uppercase; margin-bottom:1rem;
}
.hero-title {
    color:var(--burgundy) !important; font-family:'Cormorant Garamond',Georgia,serif !important;
    font-size:clamp(3rem,5.2vw,4.7rem) !important; font-weight:600 !important;
    letter-spacing:-1.5px !important; line-height:.94 !important; margin:0 !important;
}
.hero-title em {color:var(--gold); font-weight:400;}
.hero-subtitle {
    display:block; width:min(780px,100%); max-width:780px;
    margin:1.1rem auto 0 !important; padding:0 1rem; box-sizing:border-box;
    align-self:center; color:var(--ink); font-size:15px; font-weight:500;
    line-height:1.9; text-align:center !important;
}
.ornament {display:flex; align-items:center; justify-content:center; gap:12px; margin:1.6rem auto 0; color:var(--gold);}
.ornament:before,.ornament:after {content:""; width:52px; height:1px; background:var(--gold-light);}
h1,h2,h3 {font-family:'Cormorant Garamond',Georgia,serif !important; color:var(--burgundy) !important; font-weight:500 !important;}
h2 {font-size:2rem !important;} h3 {font-size:1.55rem !important;}
.section-kicker {color:var(--gold);font-size:9px;font-weight:900;letter-spacing:2.8px;text-transform:uppercase;margin-bottom:5px;}
.section-title {color:var(--burgundy);font-family:'Cormorant Garamond',Georgia,serif;font-size:2.15rem;font-weight:600;line-height:1.1;margin:0 0 .35rem;}
.section-description {color:var(--muted);font-size:13px;font-weight:500;line-height:1.75;margin-bottom:1rem;}
div[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"],
.stVerticalBlockBorderWrapper,
div[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: linear-gradient(135deg, #FFF8EF 0%, #FBEFE2 55%, #F7E6D7 100%) !important;
    background-color: #F9EEE2 !important;
    border: 1.6px solid #98564B !important;
    border-radius: 19px !important;
    box-shadow: 0 5px 12px rgba(84, 45, 42, 0.06), 0 18px 32px rgba(84, 45, 42, 0.15) !important;
    overflow: hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
    background: transparent !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 1.05rem 1.1rem !important;
}
div[data-testid="stTextArea"] small {display:none !important;}
[data-testid="stWidgetLabel"] p,.stTextArea label,.stCheckbox label {
    color:var(--burgundy) !important;font-family:'Lato',sans-serif !important;
    font-size:13px !important;font-weight:800 !important;
}
.stTextArea textarea,.stTextInput input {
    background:#FFFEFC !important;border:1px solid #D9C8B5 !important;
    border-radius:2px !important;color:var(--ink) !important;
    font-family:'Lato',sans-serif !important;font-size:15px !important;
    font-weight:500 !important;line-height:1.8 !important;padding:14px 16px !important;box-shadow:none !important;
}
.stTextArea textarea:focus,.stTextInput input:focus {border:1px solid var(--gold) !important;box-shadow:0 0 0 1px var(--gold) !important;}
.stTextArea textarea::placeholder {color:#A99D91 !important;font-style:italic;}
div[role="tablist"] {
    gap: 1.2rem !important;
    border-bottom: 1px solid var(--line) !important;
    margin-bottom: 1.1rem !important;
    padding-left: 0.2rem !important;
}
div[role="tab"] {
    color: #111111 !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding-left: 0.55rem !important;
    padding-right: 0.55rem !important;
    margin-right: 0.25rem !important;
    font-family:'Lato',sans-serif !important;
    font-size:12px !important;
    font-weight:800 !important;
    letter-spacing:1.3px !important;
    text-transform:uppercase !important;
}
div[role="tab"] p,
div[role="tab"] span,
div[role="tab"] div {
    color: #111111 !important;
}
div[role="tab"][aria-selected="true"] {
    background: rgba(255,255,255,.30) !important;
    border-bottom: 2px solid var(--gold) !important;
    color: #111111 !important;
}
.stButton>button,.stDownloadButton>button {
    min-height:44px;border-radius:2px !important;border:1px solid var(--burgundy) !important;
    background:var(--burgundy) !important;color:#111111 !important;
    font-family:'Lato',sans-serif !important;font-size:12px !important;
    font-weight:900 !important;letter-spacing:1.5px !important;text-transform:uppercase;
    transition:all .2s ease;
}
.stButton>button:hover,.stDownloadButton>button:hover {background:var(--burgundy-deep) !important;border-color:var(--gold) !important;transform:translateY(-1px);}
.stButton>button p,.stButton>button span,.stDownloadButton>button p {color:#111111 !important;font-family:'Lato',sans-serif !important;}
[data-testid="stAlert"] {border-radius:2px !important;font-family:'Lato',sans-serif !important;}
.metadata {background:#F2EBDD;border-left:3px solid var(--gold);padding:13px 15px;margin:12px 0;}
.metadata-label {color:var(--muted);font-size:9px;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:3px;}
.metadata-value {color:var(--burgundy);font-size:14px;font-weight:800;line-height:1.6;overflow-wrap:anywhere;}
.review-content {color:var(--ink);font-size:14px;font-weight:500;line-height:1.9;padding:12px 0 2px;overflow-wrap:anywhere;}
.result-count {display:inline-block;border:1px solid var(--gold-light);color:var(--burgundy);padding:6px 11px;font-size:10px;font-weight:900;letter-spacing:1.1px;text-transform:uppercase;margin:4px 0 12px;}
.result-table-wrapper {width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:11px;background:#fff;}
.result-table {width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;font-family:'Lato',sans-serif;font-size:12px;color:var(--ink);}
.result-table th {background:#F4F0E9;color:var(--muted);font-size:11px;font-weight:700;text-align:left;padding:12px;border-bottom:1px solid var(--line);}
.result-table td {padding:11px 12px;border-bottom:1px solid #F0ECE6;background:#fff;vertical-align:middle;overflow-wrap:anywhere;}
.result-table tbody tr:nth-child(even) td {background:#FCFBF9;}
.result-table tbody tr:hover td {background:#F8F5F0;}
.result-table tbody tr:last-child td {border-bottom:none;}
.result-table th:nth-child(1),.result-table td:nth-child(1) {width:43%;}
.result-table th:nth-child(2),.result-table td:nth-child(2) {width:34%;}
.result-table th:nth-child(3),.result-table td:nth-child(3) {width:23%;text-align:center;}
[data-testid="stMetric"] {background:rgba(255,255,255,.82);border:1px solid var(--line);border-radius:12px;padding:12px 14px;}
.sentiment-badge {display:inline-block;padding:5px 10px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap;}
.positive {background:#E8F1E5;color:#46653F;}
.negative {background:#F8E8E5;color:#914C3D;}
.neutral {background:#F8F0DC;color:#86651F;}
.absent {background:#F0EDE8;color:#736B61;}
.confidence-cell {font-weight:600;color:var(--burgundy);}
[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fff;}
[data-testid="stCaptionContainer"] p,.stCaption {color:var(--muted) !important;font-family:'Lato',sans-serif !important;font-size:11px !important;font-weight:400 !important;}
hr {border-color:var(--line) !important;}
.dashboard-shell {margin-bottom:1rem;}
.panel-heading {border-bottom:1px solid #D9BFA0;padding-bottom:18px;margin-bottom:20px;}
.insight {display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:4px 0 18px;}
.insight-item {display:flex;gap:14px;align-items:center;background:#FFFEFC;border:1px solid var(--line);border-radius:14px;padding:14px 18px;}
.insight-icon {flex:0 0 42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:19px;font-weight:700;}
.insight-item.good .insight-icon {background:#E3ECD9;color:#526B43;}
.insight-item.bad .insight-icon {background:#F0DDD6;color:#914C3D;}
.insight-text {font-size:13px;color:var(--muted);line-height:1.5;}
.insight-text b {display:block;color:var(--burgundy);font-size:1.35rem;font-weight:700;line-height:1.2;margin:4px 0;}
.kpi {background:#FFFEFC;border:1px solid var(--line);border-top:3px solid var(--gold);border-radius:12px;padding:16px 18px;height:100%;}
.kpi-label {color:var(--muted);font-size:12px;font-weight:700;margin-bottom:6px;}
.kpi-value {color:var(--burgundy);font-size:2.6rem;font-family:'Cormorant Garamond',Georgia,serif;font-weight:700;line-height:1;}
.kpi-note {color:#8A7D72;font-size:12px;font-weight:500;margin-top:8px;line-height:1.4;}
.tbl-wrap {width:100%;overflow-x:auto;border:1px solid #E3D0BC;border-radius:9px;background:#FFFEFC;}
.tbl {width:100%;border-collapse:separate;border-spacing:0;font-family:'Lato',sans-serif;font-size:13px;color:#4A342E;}
.tbl th {background:#EAD7C2;color:var(--burgundy);font-weight:800;text-align:left;padding:12px 14px;border-bottom:1px solid #D8B98F;white-space:nowrap;}
.tbl td {padding:11px 14px;border-bottom:1px solid #F0E4D6;background:#FFFEFC;vertical-align:middle;}
.tbl tbody tr:nth-child(even) td {background:#FBF5EC;}
.tbl tbody tr:hover td {background:#F6EAD9;}
.tbl tbody tr:last-child td {border-bottom:none;}
.tbl .num {text-align:center;font-weight:700;font-variant-numeric:tabular-nums;}
.tbl .pos-n {color:#526B43;} .tbl .neg-n {color:#914C3D;} .tbl .neu-n {color:#8A641F;} .tbl .dim {color:#B0A294;font-weight:500;}
.badge {display:inline-block;padding:5px 10px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap;}
.badge.positive,.positive {background:#E3ECD9;color:#526B43;}
.badge.negative,.negative {background:#F0DDD6;color:#914C3D;}
.badge.neutral,.neutral {background:#F5E6C8;color:#8A641F;}
.mix {display:flex;width:150px;height:9px;border-radius:5px;overflow:hidden;background:#EADFCF;}
.mix i {display:block;height:100%;}
.mix .p {background:#68765D;} .mix .n {background:#A65D50;} .mix .u {background:#D4BE96;}
.mix-wrap {display:flex;align-items:center;gap:10px;}
.mix-wrap span {font-weight:700;min-width:44px;}
.rv {background:#FFFEFC;border:1px solid var(--line);border-left:4px solid var(--sage);border-radius:10px;padding:13px 16px;margin-bottom:10px;}
.rv.negative {border-left-color:var(--rose);} .rv.neutral {border-left-color:#D4BE96;}
.rv-head {display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:7px;}
.rv-id {color:var(--muted);font-size:12px;font-weight:700;}
.rv-conf {color:var(--muted);font-size:12px;font-weight:600;margin-left:8px;}
.rv-body {color:var(--ink);font-size:14px;line-height:1.9;font-weight:500;overflow-wrap:anywhere;}
.page-footer {border-top:1px solid var(--gold-light);margin-top:2.5rem;padding-top:15px;display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:9px;font-weight:700;letter-spacing:1.7px;text-transform:uppercase;}
@media(max-width:760px) {
    .block-container {padding:1rem 1rem 2rem !important;}
    .hero {padding:.5rem 0 1.5rem;}
    .hero-title {font-size:3.2rem !important;}
    .page-footer {flex-direction:column;}
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# 5. SESSION STATE
# =========================================================
defaults = {
    "review": "",
    "single_result": None,
    "last_batch": None,
    "selected_batch_id": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def clear_review():
    st.session_state.review = ""
    st.session_state.single_result = None


# =========================================================
# 6. HEADER
# =========================================================
st.markdown("""
<section class="hero">
    <div class="eyebrow">Phân tích cảm xúc theo khía cạnh</div>
    <h1 class="hero-title">Restaurant Review <em>AI</em></h1>
    <p class="hero-subtitle">
        Khám phá cảm xúc ẩn sau từng đánh giá nhà hàng.
        Phân tích các khía cạnh trải nghiệm — từ chất lượng món ăn,
        giá cả đến dịch vụ và không gian.
    </p>
</section>
""", unsafe_allow_html=True)

tab_single, tab_batch, tab_dashboard, tab_history, tab_model, tab_learning = st.tabs([
    "Phân tích lẻ",
    "Phân tích CSV",
    "Dashboard",
    "Lịch sử",
    "Hiệu năng",
    "Học & góp ý",
])


# =========================================================
# 7. SINGLE REVIEW — POST /analyze
# =========================================================
with tab_single:
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        with st.container(border=True):
            st.markdown("""
            <div class="panel-heading">
                <div class="section-kicker">01 / Gửi đánh giá</div>
                <div class="section-title">Phân tích bình luận</div>
                <div class="section-description">
                    Nhập nội dung đánh giá để hệ thống tiếp nhận và phân tích.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.text_area(
                "Nội dung đánh giá",
                key="review",
                placeholder="Ví dụ: Đồ ăn ngon, giá hợp lý nhưng phục vụ hơi chậm...",
                height=180,
                max_chars=1000,
            )
            st.caption(
                f"{len(st.session_state.review)} / 1.000 ký tự · "
                "Bình luận dài được phân tích theo các đoạn chồng lấn."
            )
            button_col1, button_col2 = st.columns(2, gap="small")
            with button_col1:
                analyze_single = st.button(
                    "Phân tích  →", use_container_width=True, key="analyze_single"
                )
            with button_col2:
                st.button(
                    "Xóa nội dung", use_container_width=True,
                    on_click=clear_review, key="clear_single"
                )

    if analyze_single:
        review_content = st.session_state.review.strip()
        if not review_content:
            st.warning("Vui lòng nhập nội dung bình luận trước khi phân tích.")
        else:
            try:
                with st.spinner("Đang phân tích bình luận..."):
                    response = api_request(
                        "POST",
                        "/analyze",
                        json={"review": review_content},
                    ).json()
                st.session_state.single_result = response
                st.success("Phân tích bình luận thành công.")
            except RuntimeError as error:
                st.session_state.single_result = None
                st.error(str(error))

    with right_col:
        with st.container(border=True):
            st.markdown("""
            <div class="panel-heading">
                <div class="section-kicker">02 / Cảm xúc theo khía cạnh</div>
                <div class="section-title">Kết quả phân tích</div>
                <div class="section-description">
                    Tổng hợp cảm xúc theo từng khía cạnh trong trải nghiệm nhà hàng.
                </div>
            </div>
            """, unsafe_allow_html=True)

            result = st.session_state.single_result
            if result:
                meta1, meta2 = st.columns(2, gap="small")
                with meta1:
                    st.markdown(
                        f'<div class="metadata"><div class="metadata-label">Review ID</div>'
                        f'<div class="metadata-value">{html.escape(str(result.get("review_id", "—")))}</div></div>',
                        unsafe_allow_html=True,
                    )
                with meta2:
                    st.markdown(
                        f'<div class="metadata"><div class="metadata-label">Batch ID</div>'
                        f'<div class="metadata-value">{html.escape(str(result.get("batch_id", "—")))}</div></div>',
                        unsafe_allow_html=True,
                    )
                st.markdown('<div class="metadata-label">Original review</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="review-content">{html.escape(str(result.get("review", "")))}</div>',
                    unsafe_allow_html=True,
                )
                st.divider()
                render_results_table(
                    result.get("results", []),
                    key_prefix="single",
                    show_filter=True,
                )
                st.caption(
                    "Độ tin cậy là điểm số của mô hình, chưa được hiệu chuẩn "
                    "thành xác suất."
                )
                style_result = result.get("writing_style", {})
                if style_result.get("available"):
                    st.markdown("### Dấu hiệu cách diễn đạt")
                    if style_result.get("labels"):
                        st.write(
                            ", ".join(
                                STYLE_TAG_NAMES.get(tag, tag)
                                for tag in style_result["labels"]
                            )
                        )
                    else:
                        st.info("Chưa nhận diện thấy dấu hiệu cách diễn đạt đặc biệt.")
                    if style_result.get("message"):
                        st.caption(style_result["message"])

                with st.expander("Kiểm tra nhãn và góp phần cải thiện mô hình"):
                    render_feedback_form(result)
            else:
                st.markdown("""
                <div style="min-height:280px;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;text-align:center;
                    padding:30px 18px;border:1px dashed #D6B98C;background:rgba(255,250,242,.72);">
                    <div style="color:#A77C45;font-family:'Be Vietnam Pro',sans-serif;font-size:28px;font-weight:700;margin-bottom:8px;">✦</div>
                    <div style="color:#542D2A;font-family:'Be Vietnam Pro',sans-serif;font-size:19px;font-weight:700;margin-bottom:7px;">Sẵn sàng phân tích</div>
                    <div style="max-width:320px;color:#716A62;font-family:'Be Vietnam Pro',sans-serif;font-size:12px;line-height:1.8;">
                        Nhập bình luận ở khung bên trái và chọn <strong>Phân tích</strong> để xem kết quả tại đây.
                    </div>
                </div>
                """, unsafe_allow_html=True)


# =========================================================
# 8. BATCH ANALYSIS — POST /analyze/batch
# =========================================================
with tab_batch:
    with st.container(border=True):
        st.markdown("""
        <div class="panel-heading">
            <div class="section-kicker">03 / Phân tích hàng loạt</div>
            <div class="section-title">Phân tích hàng loạt</div>
            <div class="section-description">
                Tải lên tệp CSV chứa các đánh giá. Tệp cần có cột <b>Review</b>
                và dung lượng không vượt quá 10 MB.
            </div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Chọn tệp CSV",
            type=["csv"],
            accept_multiple_files=False,
            key="batch_csv_upload",
        )
        if uploaded_file is not None:
            st.caption(f"Tệp đã chọn: {uploaded_file.name} · {uploaded_file.size / 1024:.1f} KB")

        run_batch = st.button(
            "Phân tích CSV  →",
            use_container_width=True,
            disabled=uploaded_file is None,
            key="run_batch",
        )

        if run_batch and uploaded_file is not None:
            if uploaded_file.size > 10 * 1024 * 1024:
                st.error("Tệp vượt quá dung lượng tối đa 10 MB.")
            else:
                try:
                    with st.spinner("Đang tải CSV lên và phân tích. Vui lòng chờ..."):
                        response = api_request(
                            "POST",
                            "/analyze/batch",
                            files={
                                "file": (
                                    uploaded_file.name,
                                    uploaded_file.getvalue(),
                                    "text/csv",
                                )
                            },
                        ).json()
                    st.session_state.last_batch = response
                    st.session_state.selected_batch_id = response.get("batch_id")
                    st.success("Phân tích tệp hoàn tất.")
                except RuntimeError as error:
                    st.error(str(error))

    if st.session_state.last_batch:
        batch_response = st.session_state.last_batch
        st.markdown("### Kết quả xử lý tệp vừa tải lên")
        st.markdown(
            f'<div class="metadata"><div class="metadata-label">Batch ID</div>'
            f'<div class="metadata-value">{html.escape(str(batch_response.get("batch_id", "—")))}</div></div>',
            unsafe_allow_html=True,
        )
        # API batch trả về các trường tổng hợp này.
        render_batch_summary(batch_response)


# =========================================================
# 9. DASHBOARD INTEGRATION
# =========================================================
with tab_dashboard:
    render_dashboard_panel()


# =========================================================
# 10. BATCH HISTORY + DETAIL + CSV EXPORT
# =========================================================
with tab_history:
    st.markdown("""
    <div class="section-kicker">04 / Lịch sử phân tích</div>
    <div class="section-title">Lịch sử phân tích</div>
    <div class="section-description">
        Danh sách các Batch được lưu trong SQLite Database.
    </div>
    """, unsafe_allow_html=True)

    refresh_col, _ = st.columns([1, 3])
    with refresh_col:
        refresh_history = st.button("↻ Làm mới lịch sử", key="refresh_history")

    if refresh_history or "batch_history" not in st.session_state:
        try:
            history_response = api_request("GET", "/batches").json()
            st.session_state.batch_history = history_response.get("batches", [])
        except RuntimeError:
            st.session_state.batch_history = None
            st.error("Không thể tải dữ liệu lịch sử phân tích.")

    batches = st.session_state.get("batch_history")
    if isinstance(batches, list):
        if not batches:
            st.info("Chưa có Batch nào trong lịch sử.")
        else:
            history_rows = []
            for batch in batches:
                history_rows.append({
                    "Batch ID": batch.get("batch_id", ""),
                    "Tổng số dòng": batch.get("total_rows", 0),
                    "Đánh giá hợp lệ": batch.get("total_reviews", 0),
                    "Dòng bỏ qua": batch.get("skipped_rows", 0),
                    "Tổng kết quả": batch.get("total_results", 0),
                    "Thời gian tạo": batch.get("created_at", ""),
                })
            st.dataframe(
                pd.DataFrame(history_rows),
                use_container_width=True,
                hide_index=True,
            )

            batch_ids = [
                str(batch.get("batch_id"))
                for batch in batches
                if batch.get("batch_id")
            ]
            if batch_ids:
                default_index = 0
                if st.session_state.selected_batch_id in batch_ids:
                    default_index = batch_ids.index(st.session_state.selected_batch_id)

                selected_batch = st.selectbox(
                    "Chọn Batch để xem chi tiết",
                    options=batch_ids,
                    index=default_index,
                    key="history_batch_select",
                )
                st.session_state.selected_batch_id = selected_batch

                detail_col, export_col = st.columns([2, 1], gap="small")
                with detail_col:
                    load_detail = st.button(
                        "Xem chi tiết Batch  →",
                        use_container_width=True,
                        key="load_batch_detail",
                    )
                with export_col:
                    export_clicked = st.button(
                        "Tải CSV ↓",
                        use_container_width=True,
                        key="export_batch",
                    )

                if load_detail:
                    try:
                        detail_response = api_request(
                            "GET",
                            f"/batches/{selected_batch}",
                        ).json()
                        st.session_state.batch_detail = detail_response
                        st.session_state.batch_detail_id = selected_batch
                    except RuntimeError as error:
                        st.error(str(error))

                if export_clicked:
                    try:
                        export_response = api_request(
                            "GET",
                            f"/batches/{selected_batch}/export",
                        )
                        st.download_button(
                            "Lưu file kết quả CSV",
                            data=export_response.content,
                            file_name=f"{selected_batch}_results.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key=f"download_{selected_batch}",
                        )
                    except RuntimeError as error:
                        st.error(str(error))

                detail = st.session_state.get("batch_detail")
                if detail and st.session_state.get("batch_detail_id") == selected_batch:
                    st.divider()
                    batch_info = detail.get("batch", {})
                    st.markdown("### Thông tin Batch")
                    st.markdown(
                        f'<div class="metadata"><div class="metadata-label">Batch ID</div>'
                        f'<div class="metadata-value">{html.escape(str(batch_info.get("batch_id", selected_batch)))}</div></div>',
                        unsafe_allow_html=True,
                    )
                    render_batch_summary(batch_info)
                    if batch_info.get("status") == "Completed":
                        st.markdown("### Kết quả theo từng đánh giá và khía cạnh")
                        all_results = detail.get("results", [])
                        if all_results:
                            review_ids = list(dict.fromkeys(
                                str(item.get("review_id", ""))
                                for item in all_results
                            ))
                            chosen_review = st.selectbox(
                                "Lọc theo Review ID",
                                options=["Tất cả đánh giá"] + review_ids,
                                key=f"review_filter_{selected_batch}",
                            )
                            if chosen_review != "Tất cả đánh giá":
                                visible_results = [
                                    item for item in all_results
                                    if str(item.get("review_id", "")) == chosen_review
                                ]
                            else:
                                visible_results = all_results
                            render_results_table(
                                visible_results,
                                key_prefix=f"batch_{selected_batch}_{chosen_review}",
                                show_filter=True,
                            )
                        else:
                            st.info("Batch đã hoàn thành nhưng không có bản ghi kết quả.")
                    else:
                        st.info("Batch chưa ở trạng thái Completed nên chưa có kết quả chi tiết.")
    elif batches is None:
        st.info("Chưa có dữ liệu lịch sử để hiển thị.")


# =========================================================
# 10. MODEL PERFORMANCE — TRAINING AND EVALUATION REPORTS
# =========================================================
with tab_model:
    st.markdown("""
    <div class="section-kicker">05 / Đánh giá mô hình</div>
    <div class="section-title">Hiệu năng PhoBERT ABSA V6</div>
    """, unsafe_allow_html=True)

    try:
        report = api_request("GET", "/model/report").json()
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric(
                "Validation Aspect Macro-F1 · V6",
                f"{report['validation_macro_f1']:.4f}",
            )
        with metrics_col2:
            st.metric(
                "Test Aspect Macro-F1 · V6",
                f"{report['test_macro_f1']:.4f}",
            )
        with metrics_col3:
            st.metric(
                "Epoch tốt nhất",
                report["best_epoch"],
            )
        st.caption(
            "Kết quả đánh giá checkpoint PhoBERT ABSA V6 trên các tập dữ liệu "
            "huấn luyện và kiểm định đã tách riêng."
        )

        dataset_cols = st.columns(3)
        for column, label, key in zip(
            dataset_cols,
            ("Tập train", "Tập validation", "Tập test"),
            ("train", "validation", "test"),
        ):
            with column:
                st.metric(label, f"{report['dataset_sizes'][key]:,} bình luận")

        aspect_test = pd.DataFrame(report["aspect_test_results"]).rename(
            columns={
                "Aspect": "Khía cạnh",
                "Test_Macro_F1": "V6 · Test Macro-F1",
            }
        )
        aspect_test["Khía cạnh"] = aspect_test["Khía cạnh"].map(
            lambda aspect: ASPECT_NAMES.get(aspect, aspect)
        )
        st.markdown("### Kết quả V6 trên tập test theo từng khía cạnh")
        st.bar_chart(
            aspect_test.set_index("Khía cạnh"),
            stack=False,
        )
        st.dataframe(
            aspect_test,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Phân bố nhãn trong dữ liệu train")
        st.bar_chart(pd.Series(
            report["label_distribution"],
            name="Số nhãn",
        ))

        history = pd.DataFrame(report["training_history"]).set_index("epoch")
        st.markdown("### Quá trình huấn luyện V6")
        loss_col, score_col = st.columns(2, gap="large")
        with loss_col:
            st.caption("Train loss")
            st.line_chart(history[["train_loss"]])
        with score_col:
            st.caption("Validation Aspect Macro-F1")
            st.line_chart(history[["val_macro_f1"]])

    except (RuntimeError, KeyError, ValueError, IndexError) as error:
        st.error(f"Không tải được báo cáo hiệu năng mô hình: {error}")


# =========================================================
# 11. HUMAN-VERIFIED LEARNING
# =========================================================
with tab_learning:
    st.markdown("""
    <div class="section-kicker">06 / Học có xác nhận</div>
    <div class="section-title">Học từ phản hồi đã xác nhận</div>
    <div class="section-description">
        Mô hình không tự coi dự đoán của chính nó là nhãn đúng.
        Chỉ các phản hồi được người dùng kiểm tra mới tham gia huấn luyện;
        checkpoint mới phải vượt qua kiểm định trước khi được kích hoạt.
    </div>
    """, unsafe_allow_html=True)

    st.button(
        "↻ Cập nhật trạng thái học",
        key="refresh_learning_status",
    )
    try:
        learning_status = api_request("GET", "/learning/status").json()
        model_status = api_request("GET", "/model/status").json()

        learning_cols = st.columns(4)
        learning_metrics = [
            ("Bình luận đã xác nhận", learning_status.get("reviewed_reviews", 0)),
            ("Cần để huấn luyện", learning_status.get("minimum_reviews_to_train", 50)),
            ("Checkpoint đang dùng", model_status.get("active_checkpoint", "—")),
            ("Test Aspect Macro-F1 · V6", f"{model_status.get('test_aspect_macro_f1', 0):.4f}"),
        ]
        for col, (label, value) in zip(learning_cols, learning_metrics):
            with col:
                st.metric(label, value)

        if not model_status.get("available"):
            st.error(
                "Mô hình chưa sẵn sàng. Kiểm tra checkpoint, tokenizer "
                "và các thư viện trong requirements.txt."
            )
        if model_status.get("writing_style_available"):
            st.success(
                "Bộ nhận diện cách diễn đạt đã đạt điều kiện dữ liệu và "
                "đánh giá nội bộ."
            )
        training_state = learning_status.get("training", {})
        training_state_name = training_state.get("status", "idle")
        if training_state_name == "running":
            st.info(training_state.get("message", "Đang huấn luyện..."))
        elif training_state_name in ("accepted", "rejected", "failed"):
            if training_state_name == "accepted":
                st.success(training_state.get("message", "Đã kích hoạt checkpoint mới."))
            else:
                st.warning(training_state.get("message", "Checkpoint chưa được kích hoạt."))
        elif learning_status.get("ready_to_train"):
            st.success(
                "Đã đủ phản hồi để tạo một ứng viên. Huấn luyện có thể mất "
                "thời gian; checkpoint hiện tại vẫn được dùng nếu ứng viên "
                "không đạt kiểm định."
            )
        else:
            st.info(
                "Chưa đủ dữ liệu đã xác nhận. Hãy phân tích bình luận rồi "
                "kiểm tra và lưu phản hồi ở phần kết quả."
            )

        if training_state.get("report"):
            report = training_state["report"]
            report_cols = st.columns(3)
            report_cols[0].metric(
                "Validation trước",
                f"{report.get('validation_aspect_macro_f1_before', 0):.4f}",
            )
            report_cols[1].metric(
                "Validation sau",
                f"{report.get('validation_aspect_macro_f1_after', 0):.4f}",
            )
            report_cols[2].metric(
                "Feedback test sau",
                f"{report.get('feedback_aspect_macro_f1_after', 0):.4f}",
            )

        can_train = (
            learning_status.get("ready_to_train", False)
            and training_state_name != "running"
            and model_status.get("available", False)
        )
        if st.button(
            "Huấn luyện và kiểm định ứng viên",
            key="start_feedback_training",
            disabled=not can_train,
        ):
            try:
                start_response = api_request("POST", "/learning/train").json()
                st.session_state["learning_start_message"] = start_response.get(
                    "message",
                    "Đã gửi yêu cầu huấn luyện.",
                )
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))
        if st.session_state.get("learning_start_message"):
            st.info(
                st.session_state.pop("learning_start_message")
            )
    except RuntimeError as error:
        st.error(f"Không tải được trạng thái học: {error}")


# =========================================================
# 12. FOOTER
# =========================================================
st.markdown("""
<div class="page-footer">
    <span>Restaurant Review AI</span>
    <span>Aspect-Based Sentiment Analysis</span>
    <span>Designed with care · 2026</span>
</div>
""", unsafe_allow_html=True)
