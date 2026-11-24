import html
import os
import sys
from pathlib import Path
import re

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
    fetch_dashboard_summary,
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
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
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
API_BASE_URL = DASHBOARD_API_BASE_URL
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
    url = f"{API_BASE_URL}{endpoint}"

    token = st.session_state.get("access_token")

    headers = kwargs.pop("headers", {})

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method,
            url,
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            **kwargs,
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Không kết nối được Backend.")
    except requests.exceptions.Timeout:
        raise RuntimeError("Backend phản hồi quá lâu.")

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text

        raise RuntimeError(
            f"Backend báo lỗi ({response.status_code}): {detail}"
        )

    return response


def sentiment_label(value):
    try:
        return SENTIMENT_NAMES.get(int(value), f"Không xác định ({value})")
    except (TypeError, ValueError):
        return f"Không xác định ({value})"


def prepare_results(results):
    """Chuẩn hóa kết quả phân tích để hiển thị bằng tiếng Việt."""
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
    """Hiển thị bảng kết quả phân tích theo khía cạnh và cảm xúc."""

    if not results:
        st.info("Batch này chưa có kết quả để hiển thị.")
        return

    df = pd.DataFrame(prepare_results(results))

    if df.empty:
        st.info(
            "Chưa nhận diện được khía cạnh trong đánh giá này. "
            "Hãy thử bổ sung chi tiết về món ăn, giá cả, dịch vụ hoặc không gian."
        )
        return

    # Bộ lọc và số lượng kết quả trên cùng một hàng
    if show_filter:
        col_filter = st.container()

        with col_filter:
            show_all = st.checkbox(
                "Hiển thị tất cả khía cạnh",
                value=False,
                key=f"{key_prefix}_show_all",
            )

        if not show_all:
            df = df[df["Cảm xúc"] != "Không đề cập"]

        

    # Hiển thị số lượng kết quả
    if df.empty:
        st.info("Không có khía cạnh nào phù hợp với bộ lọc hiện tại.")
        return

    # Tạo các dòng của bảng
    table_rows = []

    for _, item in df.iterrows():
        aspect = html.escape(str(item["Khía cạnh"]))
        sentiment = html.escape(str(item["Cảm xúc"]))
        confidence = html.escape(str(item["Độ tin cậy"]))

        css_class = SENTIMENT_CLASSES.get(item["Cảm xúc"], "absent")

        table_rows.append(
            f"""
            <tr>
                <td class="aspect-cell">{aspect}</td>
                <td class="sentiment-cell">
                    <span class="sentiment-badge {css_class}">{sentiment}</span>
                </td>
                <td class="confidence-cell">{confidence}</td>
            </tr>
            """
        )

    table_html = f"""
    <div class="result-table-wrapper">
        <table class="result-table">
            <thead>
                <tr>
                    <th>Khía cạnh</th>
                    <th>Cảm xúc</th>
                    <th>Độ tin cậy</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
    </div>
    """

    st.html(table_html)


def render_batch_summary(batch):
    """Hiển thị tổng quan kết quả của Batch CSV."""

    metrics = [
        {
            "label": "Tổng bình luận",
            "value": batch.get("total_rows"),
            "description": "Số bình luận trong tệp CSV",
            "class": "default",
        },
        {
            "label": "Đã phân tích",
            "value": batch.get("total_reviews"),
            "description": "Số bình luận được phân tích thành công",
            "class": "success",
        },
    ]

    cards_html = ""

    for item in metrics:
        raw_value = item["value"]

        display_value = (
            "—" if raw_value is None
            else html.escape(str(raw_value))
        )

        cards_html += f"""
        <div class="batch-metric-card">
            <div class="batch-metric-label">
                {item["label"]}
            </div>

            <div class="batch-metric-value {item["class"]}">
                {display_value}
            </div>

            <div class="batch-metric-description">
                {item["description"]}
            </div>
        </div>
        """

    st.html(f"""
    <style>
        .batch-metric-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            width: 100%;
            margin: 4px 0 0;
        }}

        .batch-metric-card {{
            min-width: 0;
            box-sizing: border-box;
            padding: 20px;
            background: #FFFCF7;
            border: 1px solid #E4D5C4;
            border-radius: 12px;
        }}

        .batch-metric-label {{
            color: #79685B;
            font-family: 'Lato', sans-serif;
            font-size: 14px;
            font-weight: 700;
        }}

        .batch-metric-value {{
            color: #552824;
            font-family: 'Cormorant Garamond', Georgia, serif;
            font-size: 42px;
            font-weight: 700;
            line-height: 1.1;
            margin: 10px 0 6px;
        }}

        .batch-metric-value.success {{
            color: #477A58;
        }}

        .batch-metric-description {{
            color: #948477;
            font-family: 'Lato', sans-serif;
            font-size: 12px;
            line-height: 1.5;
        }}

        @media (max-width: 600px) {{
            .batch-metric-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>

    <div class="batch-metric-grid">
        {cards_html}
    </div>
    """)


def render_empty_state(message):
    """Hiển thị giao diện chờ khi chưa có kết quả phân tích."""

    empty_state_html = f"""
<div class="empty-state">
    <div class="empty-state-icon">✦</div>
    <div class="empty-state-title">
        Sẵn sàng phân tích
    </div>
    <p class="empty-state-description">
        {html.escape(message)}
    </p>
</div>
"""

    st.html(empty_state_html)

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
        font=dict(family="Lato, Arial, sans-serif", color="#2F2925", size=12),
        legend=dict(orientation="h", y=1.1, x=0.02),
        hoverlabel=dict(font_family="Lato, Arial, sans-serif"),
    )
    fig.update_xaxes(gridcolor="#EAD9C6", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True)
    return fig


def pct(v):
    return "—" if pd.isna(v) else f"{v:.1f}%"


def width(v):
    return 0 if pd.isna(v) else max(0, min(100, float(v)))

def summarize_batch_results(results):
    """Tổng hợp số lượng cảm xúc theo 12 khía cạnh của toàn bộ CSV."""

    df = pd.DataFrame(results)

    if df.empty:
        return pd.DataFrame()

    df["Sentiment"] = pd.to_numeric(
        df["Sentiment"], errors="coerce"
    ).fillna(0).astype(int)

    summary = []

    for aspect_code, aspect_name in ASPECT_NAMES.items():
        aspect_data = df[df["Aspect"] == aspect_code]

        positive = int((aspect_data["Sentiment"] == 1).sum())
        negative = int((aspect_data["Sentiment"] == 2).sum())
        neutral = int((aspect_data["Sentiment"] == 3).sum())
        absent = int((aspect_data["Sentiment"] == 0).sum())

        mentions = positive + negative + neutral

        summary.append({
            "Khía cạnh": aspect_name,
            "Tích cực": positive,
            "Tiêu cực": negative,
            "Trung lập": neutral,
            "Không đề cập": absent,
            "Lượt đề cập": mentions,
            "% Tích cực": (
                positive / mentions * 100 if mentions else None
            ),
            "% Tiêu cực": (
                negative / mentions * 100 if mentions else None
            ),
            "% Trung lập": (
                neutral / mentions * 100 if mentions else None
            ),
        })

    return pd.DataFrame(summary)


def stats_table_html(data, compact=False, variant="default"):
    rows = ""

    # Riêng bảng CSV sẽ hiển thị thanh tỷ lệ cảm xúc
    # Dashboard vẫn giữ cột Độ tin cậy TB
    show_mix = not compact or variant == "batch"

    for _, r in data.sort_values(
        "Lượt đề cập", ascending=False
    ).iterrows():

        mentions = int(r["Lượt đề cập"])

        if mentions == 0:
            mix = '<span class="dim">—</span>'
        else:
            positive_count = int(r["Tích cực"])
            negative_count = int(r["Tiêu cực"])
            neutral_count = int(r["Trung lập"])

            mix = (
                '<div class="mix-wrap">'
                '<div class="mix">'

                f'<i class="p" '
                f'title="Tích cực: {positive_count} lượt '
                f'({pct(r["% Tích cực"])})" '
                f'style="width:{width(r["% Tích cực"])}%"></i>'

                f'<i class="n" '
                f'title="Tiêu cực: {negative_count} lượt '
                f'({pct(r["% Tiêu cực"])})" '
                f'style="width:{width(r["% Tiêu cực"])}%"></i>'

                f'<i class="u" '
                f'title="Trung lập: {neutral_count} lượt '
                f'({pct(r["% Trung lập"])})" '
                f'style="width:{width(r["% Trung lập"])}%"></i>'

                '</div></div>'
            )

        confidence = r.get("Độ tin cậy TB")

        confidence_html = (
            f'<span class="confidence-value">{confidence:.1f}%</span>'
            if pd.notna(confidence)
            else '<span class="dim">—</span>'
        )

        rows += (
            f'<tr><td><b>{html.escape(str(r["Khía cạnh"]))}</b></td>'
            f'<td class="num pos-n">{int(r["Tích cực"])}</td>'
            f'<td class="num neg-n">{int(r["Tiêu cực"])}</td>'
            f'<td class="num neu-n">{int(r["Trung lập"])}</td>'
            f'<td class="num">{mentions}</td>'
        )

        if not compact:
            rows += (
                f'<td class="num dim">{int(r["Không đề cập"])}</td>'
            )

        if show_mix:
            rows += f'<td class="num">{mix}</td>'
        else:
            rows += f'<td class="num">{confidence_html}</td>'

        if not compact:
            rows += (
                f'<td class="num">{pct(r["% Tiêu cực"])}</td>'
                f'<td class="num">{pct(r["% Trung lập"])}</td>'
            )

        rows += "</tr>"

    head = (
        "<th>Khía cạnh</th>"
        "<th>Tích cực</th>"
        "<th>Tiêu cực</th>"
        "<th>Trung lập</th>"
        "<th>Lượt đề cập</th>"
        + ("" if compact else "<th>Không đề cập</th>")
        + (
            "<th>Tỷ lệ cảm xúc</th>"
            if variant == "batch"
            else (
                "<th>Tỷ lệ tích cực</th>"
                if not compact
                else "<th>Độ tin cậy TB</th>"
            )
        )
        + (
            ""
            if compact
            else "<th>% Tiêu cực</th><th>% Trung lập</th>"
        )
    )

    wrap_class = "tbl-wrap"
    table_class = "tbl"

    if variant == "batch":
        wrap_class += " batch-summary-wrap"
        table_class += " batch-summary-table"

    return (
        f'<div class="{wrap_class}">'
        f'<table class="{table_class}">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )

def load_batch_list():
    return fetch_batches()


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_batch(batch_id):
    return fetch_dashboard(batch_id)

def load_dashboard_summary():
    """Tải Dashboard tổng hợp tất cả Batch Completed."""
    return fetch_dashboard_summary()
def render_dashboard_panel():
    st.markdown(
        """
        <div class="dashboard-shell">
            <div class="panel-heading">
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
        st.info(
            "Chưa có dữ liệu phân tích. "
            "Các chỉ số bên dưới sẽ được cập nhật sau khi bạn tải lên CSV."
        )

        # 1. KPI mặc định bằng 0
        k1, k2, k3, k4 = st.columns(4, gap="medium")

        empty_kpis = [
            ("Tổng số bình luận", "0", "Số review_id khác nhau"),
            ("Lượt đề cập khía cạnh", "0", "Tổng lượt đề cập"),
            ("Tỷ lệ tích cực chung", "0%", "Chưa có dữ liệu cảm xúc"),
            ("Khía cạnh được nhắc tới", "0/12", "Trên tổng 12 khía cạnh"),
        ]

        for col, (label, value, note) in zip(
            [k1, k2, k3, k4], empty_kpis
        ):
            col.markdown(
                f"""
                <div class="kpi">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 2. Biểu đồ tròn mặc định khi chưa có dữ liệu
        fig_empty_pie = go.Figure(
            go.Pie(
                labels=["Chưa có dữ liệu"],
                values=[1],
                hole=0.70,
                sort=False,
                marker=dict(
                    colors=["#E8DED0"],
                    line=dict(color="#FBF1E4", width=3)
                ),
                hoverinfo="skip",
                textinfo="none",
                showlegend=False
            )
        )

        fig_empty_pie.add_annotation(
            text="<b>0</b><br>lượt đề cập",
            showarrow=False,
            font=dict(size=20, color="#552824")
        )

        # Biểu đồ tròn nhỏ gọn hơn, phù hợp với card bên trái.
        fig_empty_pie = style_fig(fig_empty_pie, 460)

        fig_empty_pie.update_layout(
            height=460,
            margin=dict(t=25, b=20, l=5, r=5),
            showlegend=False
        )

        # Thu nhỏ vùng vẽ của vòng tròn để tạo khoảng thở bên trong card.
        fig_empty_pie.update_traces(
            domain=dict(x=[0.08, 0.92], y=[0.06, 0.94])
        )

        # 3. Biểu đồ 12 khía cạnh mặc định bằng 0
        aspect_codes = list(DASHBOARD_ASPECT_NAMES.keys())

        # Chuyển mã khía cạnh thành tên tiếng Việt
        aspect_names = [
            ASPECT_NAMES.get(code, code)
            for code in aspect_codes
        ]

        fig_empty_bar = go.Figure()

        fig_empty_bar.add_trace(
            go.Bar(
                name="Tích cực",
                y=aspect_names,
                x=[0] * len(aspect_names),
                orientation="h",
                marker_color=COLORS["Tích cực"],
                showlegend=True
            )
        )

        fig_empty_bar.add_trace(
            go.Bar(
                name="Tiêu cực",
                y=aspect_names,
                x=[0] * len(aspect_names),
                orientation="h",
                marker_color=COLORS["Tiêu cực"],
                showlegend=True
            )
        )

        fig_empty_bar.add_trace(
            go.Bar(
                name="Trung lập",
                y=aspect_names,
                x=[0] * len(aspect_names),
                orientation="h",
                marker_color=COLORS["Trung lập"],
                showlegend=True
            )
        )

        fig_empty_bar.update_layout(
            barmode="stack",
            xaxis_title="Số lượt đề cập",
            yaxis_title="",
            height=460,
            margin=dict(t=80, b=35, l=15, r=25),
        )

        fig_empty_bar = style_fig(fig_empty_bar, 460)

        # Đặt chú giải nằm ngang và căn giữa phía trên biểu đồ
        fig_empty_bar.update_layout(
            legend=dict(
                orientation="h",
                x=0.5,
                xanchor="center",
                y=1.02,
                yanchor="bottom",
                traceorder="normal",
                entrywidth=65,
                entrywidthmode="pixels"
            )
        )


        fig_empty_bar.update_xaxes(
            range=[0, 1],
            tickmode="array",
            tickvals=[0],
            ticktext=["0"],
            title="Số lượt đề cập"
        )

        fig_empty_bar.update_yaxes(
            automargin=True,
            categoryorder="array",
            categoryarray=aspect_names
        )

        # 4. Hiển thị hai biểu đồ trong card riêng biệt
        # Tạo khoảng cách giữa KPI và khu vực biểu đồ
        st.markdown(
            "<div style='height: 20px;'></div>",
            unsafe_allow_html=True
        )

        # Thu hẹp card Phân bố cảm xúc và dành nhiều chiều ngang
        # hơn cho card Thống kê theo khía cạnh.
        chart_col, summary_col = st.columns(
            [0.8, 1.8],
            gap="medium"
        )
        

        with chart_col:
            with st.container(border=True):
                st.markdown(
                    """
                    <div class="empty-chart-heading">
                        <div class="empty-chart-title">Phân bố cảm xúc</div>
                        <div class="empty-chart-description">
                            Tỷ trọng các cảm xúc trong đánh giá nhà hàng
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.plotly_chart(
                    fig_empty_pie,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )

        with summary_col:
            with st.container(border=True):
                st.markdown(
                    """
                    <div class="empty-chart-heading">
                        <div class="empty-chart-title">
                            Thống kê theo khía cạnh
                        </div>
                        <div class="empty-chart-description">
                            Số lượt đề cập trên 12 khía cạnh trải nghiệm
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.plotly_chart(
                    fig_empty_bar,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )

        st.markdown("### Bảng khảo sát")

        st.caption(
            "Chưa có lượt đề cập nào. "
            "Các khía cạnh sẽ được cập nhật sau khi phân tích Review."
        )

        return

    # Danh sách Batch đã hoàn thành
    batch_ids = list(completed["batch_id"])

    def format_vietnam_time(created_at):
        """Chuyển thời gian UTC từ database sang giờ Việt Nam."""

        if not created_at:
            return "Không rõ thời gian"

        dt = datetime.fromisoformat(str(created_at))

        # SQLite CURRENT_TIMESTAMP lưu thời gian UTC
        dt = dt.replace(tzinfo=timezone.utc)

        # Chuyển sang múi giờ Việt Nam
        vn_time = dt.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))

        return vn_time.strftime("%d/%m/%Y %H:%M:%S")


    labels = {
        row.batch_id: (
            f"{row.batch_id} · "
            f"{format_vietnam_time(row.created_at)} · "
            f"{row.total_reviews} bình luận"
        )
        for row in completed.itertuples()
    }

    # Thêm lựa chọn xem tất cả dữ liệu
    options = ["ALL"] + batch_ids


    filter_col1, filter_col2, filter_col3 = st.columns([1.4, 1, 1.2])

    with filter_col1:
        selected_batch = st.selectbox(
            "Bộ lọc",
            options,
            format_func=lambda b: (
                "Tất cả dữ liệu đã phân tích"
                if b == "ALL"
                else labels.get(b, b)
            ),
            key="dashboard_batch_filter"
        )

    with filter_col2:
        aspect_options = ["ALL"] + list(DASHBOARD_ASPECT_NAMES)

        aspect_select = st.selectbox(
            "Khía cạnh",
            aspect_options,
            format_func=lambda k: (
                "Tất cả khía cạnh"
                if k == "ALL"
                else DASHBOARD_ASPECT_NAMES[k]
            ),
            key="dashboard_aspect_filter"
        )

    with filter_col3:
        def sort_sentiment_filter():
            sentiment_order = {
                "Tích cực": 1,
                "Trung lập": 2,
                "Tiêu cực": 3
            }

            selected = st.session_state["dashboard_sentiment_filter"]

            st.session_state["dashboard_sentiment_filter"] = sorted(
                selected,
                key=lambda x: sentiment_order[x]
            )


        sentiment_filter = st.multiselect(
            "Cảm xúc",
            ["Tích cực", "Trung lập", "Tiêu cực"],
            default=["Tích cực", "Trung lập", "Tiêu cực"],
            key="dashboard_sentiment_filter",
            on_change=sort_sentiment_filter
        )

    # Ngưỡng nội bộ để nhận định
    min_mentions = 10


    # Tải dữ liệu theo phạm vi được chọn
    try:
        with st.spinner("Đang tổng hợp dữ liệu phân tích..."):

            if selected_batch == "ALL":
                payload = load_dashboard_summary()
            else:
                payload = load_dashboard_batch(selected_batch)

            batch_info, raw, backend_stats = parse_dashboard(
                payload
            )

    except BackendError as error:
        st.error(str(error))
        return

    # Kiểm tra dữ liệu
    errors = validate(raw)

    if errors:
        st.error(
            "Dữ liệu không hợp lệ, không thể hiển thị Dashboard:"
        )

        for entry in errors:
            st.write("- " + entry)

        return

    raw["Sentiment"] = pd.to_numeric(
        raw["Sentiment"]
    ).astype(int)

    # 1. Lọc theo Batch
    if selected_batch == "ALL":
        df = raw.copy()
    else:
        df = raw[
            raw["batch_id"] == selected_batch
        ].copy()

    # 2. Lọc theo Khía cạnh
    if aspect_select != "ALL":
        df = df[
            df["Aspect"] == aspect_select
        ].copy()

    # 3. Lọc theo Cảm xúc
    codes = [
        code
        for code, name in DASHBOARD_SENTIMENT_NAMES.items()
        if name in sentiment_filter
    ]

    df = df[
        df["Sentiment"].isin(codes)
    ].copy()

    # Kiểm tra kết quả sau khi áp dụng cả 3 bộ lọc
    if df.empty:
        st.info("Không có dữ liệu khớp với các bộ lọc hiện tại.")
        return


    tbl = aspect_table(df)
    ov = overall(df)

    # Tính độ tin cậy trung bình theo từng khía cạnh
    confidence_by_aspect = (
        df.groupby("Aspect")["Confidence"]
        .mean()
        .mul(100)
    )

    confidence_by_name = {
        ASPECT_NAMES.get(code, code): value
        for code, value in confidence_by_aspect.items()
    }

    tbl["Độ tin cậy TB"] = tbl["Khía cạnh"].map(
        confidence_by_name
    )

    shown = tbl[tbl["Lượt đề cập"] > 0]
    
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
    st.markdown(
        "<div style='height: 20px;'></div>",
        unsafe_allow_html=True
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
            margin=dict(t=30, b=40, l=10, r=10),
            showlegend=False
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
        fig.update_layout(
            barmode="stack",
            showlegend=False,
            xaxis_title="Số lượt đề cập",
            bargap=0.35,
            legend=dict(
                orientation="h",
                x=0.5,
                xanchor="center",
                y=1.12,
                yanchor="bottom"
            )
        )

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
        fig.update_layout(
            barmode="stack",
            showlegend=False,
            xaxis=dict(
                range=[0, 100],
                visible=False,
                title=None
            ),
            bargap=0.35,
            legend=dict(
                orientation="h",
                x=0.5,
                xanchor="center",
                y=1.12,
                yanchor="bottom"
            )
        )

        fig = style_fig(fig, max(340, 40 * len(mentions) + 100))
        fig.update_layout(margin=dict(t=30, b=10, l=10, r=30))
        return fig.update_xaxes(tickmode="array", tickvals=[0, 20, 40, 60, 80, 100], ticktext=[f"{t}%" for t in [0, 20, 40, 60, 80, 100]])

 
    # Khung tổng thể cho hai biểu đồ
    with st.container(border=True):

        st.markdown("""
        <div style="
            text-align:center;
            color:#552824;
            font-family:'Cormorant Garamond', Georgia, serif;
            font-size:25px;
            font-weight:600;
            margin-bottom:12px;
        ">
            Tổng quan cảm xúc khách hàng
        </div>
        """, unsafe_allow_html=True)

        # Chú giải chung – đồng bộ màu với biểu đồ
        st.html("""
        <div style="
            display:flex;
            justify-content:center;
            align-items:center;
            gap:32px;
            margin:0 0 12px;
            flex-wrap:wrap;
            color:#4A342E;
            font-size:13px;
        ">
            <span style="display:flex; align-items:center; gap:7px;">
                <span style="width:12px; height:12px; background:#68765D; border-radius:2px;"></span>
                Tích cực
            </span>

            <span style="display:flex; align-items:center; gap:7px;">
                <span style="width:12px; height:12px; background:#A65D50; border-radius:2px;"></span>
                Tiêu cực
            </span>

            <span style="display:flex; align-items:center; gap:7px;">
                <span style="width:12px; height:12px; background:#D4BE96; border-radius:2px;"></span>
                Trung lập
            </span>
        </div>
        """)

        chart_col, summary_col = st.columns(
            [0.8, 1.8],
            gap="medium"
        )

        with chart_col:
            st.markdown("""
            <div style="
                text-align:center;
                color:#8B5E3C;
                font-size:14px;
                font-weight:700;
                margin-bottom:4px;
            ">
                Phân bố cảm xúc tổng thể
            </div>
            """, unsafe_allow_html=True)

            st.plotly_chart(
                pie_chart(),
                use_container_width=True,
                key="dashboard_pie_chart"
            )

        with summary_col:
            st.markdown("""
            <div style="
                text-align:center;
                color:#8B5E3C;
                font-size:14px;
                font-weight:700;
                margin-bottom:4px;
            ">
                Cảm xúc theo từng khía cạnh
            </div>
            """, unsafe_allow_html=True)

            st.plotly_chart(
                percent_chart(),
                use_container_width=True,
                key="dashboard_percent_chart"
            )


    # TỔNG HỢP ĐÁNH GIÁ VÀ MINH CHỨNG TỪ KHÁCH HÀNG
    st.markdown(
        """
        <div class="section-kicker" style="margin-top:1.5rem;">
            TỔNG HỢP ĐÁNH GIÁ & MINH CHỨNG TỪ KHÁCH HÀNG
        </div>
        """,
        unsafe_allow_html=True
    )

    table_col, review_col = st.columns([1.2, 1], gap="medium")

    # CỘT TRÁI: BẢNG TỔNG HỢP
    with table_col:
        st.markdown(
            """
            <div class="section-description"
                style="font-weight:700; color:#8B5E3C; margin-bottom:10px;">
                01. Tổng hợp theo khía cạnh
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            stats_table_html(shown, compact=True),
            unsafe_allow_html=True
        )

    # CỘT PHẢI: REVIEW KHÁCH HÀNG
    with review_col:
        st.markdown(
            """
            <div class="section-description"
                style="font-weight:700; color:#8B5E3C; margin-bottom:10px;">
                02. Minh chứng từ khách hàng
            </div>
            """,
            unsafe_allow_html=True
        )


        # Mỗi review_id chỉ hiển thị một lần,
        # đồng thời giữ lại tất cả khía cạnh khớp bộ lọc
        review_groups = df.groupby(
            ["batch_id", "review_id"],
            sort=False,
            dropna=False
        )
        if review_groups.ngroups == 0:
            st.info("Không có bình luận nào khớp bộ lọc hiện tại.")
        else:
            cards = ""

            for review_id, group in review_groups:
                review_text = group["Review"].iloc[0]

                evidence_html = ""

                # Hiển thị các khía cạnh và cảm xúc
                # tương ứng với từng bình luận
                for item in group.itertuples():
                    aspect_name = ASPECT_NAMES.get(
                        item.Aspect, item.Aspect
                    )

                    sentiment = sentiment_label(item.Sentiment)
                    sentiment_class = BADGE_CLASS.get(
                        sentiment, "neutral"
                    )

                    confidence = (
                        f"{item.Confidence:.0%}"
                        if pd.notna(item.Confidence)
                        else "—"
                    )

                    evidence_html += (
                        f'<span class="sentiment-badge {sentiment_class}">'
                        f'{html.escape(str(aspect_name))}'
                        f' · {html.escape(str(sentiment))}'
                        f' · {confidence}'
                        f'</span> '
                    )

                cards += (
                    '<div class="rv">'
                    '<div style="display:flex; align-items:flex-start; gap:12px; margin-bottom:10px;">'
                    f'<span class="rv-id" style="flex-shrink:0;">'
                    f'{html.escape(str(review_id))}'
                    '</span>'
                    f'<span style="font-size:13px; line-height:1.5;">'
                    f'{html.escape(str(review_text))}'
                    '</span>'
                    '</div>'
                    f'<div style="margin-bottom:8px;">'
                    f'{evidence_html}'
                    '</div>'
                    '</div>'
                )
            st.html(
                f"""
                <div style="
                    max-height: 480px;
                    overflow-y: auto;
                    padding-right: 6px;
                ">
                    {cards}
                </div>
                """
            )

            st.caption(
                f"Hiển thị {min(50, review_groups.ngroups)} / "
                f"{review_groups.ngroups} bình luận."
            )


    

# =========================================================
# 4. DESIGN SYSTEM — GIỮ PHONG CÁCH LONG TRIỀU
# =========================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Lato:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">

<style>


:root {
    --ivory: #F5F0E7;
    --paper: #FFFEFC;
    --burgundy: #552824;
    --burgundy-deep: #351B19;
    --wine: #87443B;
    --gold: #B18A4E;
    --gold-light: #D4BE96;
    --ink: #2F2925;
    --muted: #6F6258;
    --line: #DCCFBD;
    --sage: #68765D;
    --rose: #A65D50;
}

/* Base page */
html, body, [class*="css"], .stApp {
    font-family: 'Lato', sans-serif !important;
    color: var(--ink);
    font-weight: 400;
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
    background-attachment: scroll !important;
}
/* Remove Streamlit's reserved top header/toolbar space (the red-box area) */
/* Hide Streamlit's top chrome, including Deploy */
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stDeployButton"],
.stDeployButton {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    visibility: hidden !important;
}

/* Cân chỉnh khoảng cách đầu trang */
[data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

.main .block-container {
    padding-top: 1.5rem !important;
    margin-top: 0 !important;
}

#MainMenu, footer { display: none !important; }


.block-container {
    width: min(calc(100% - 80px), 1320px) !important;
    max-width: 1320px !important;
    margin: 0 auto !important;
    padding-top: .7rem !important;
    padding-bottom: 2rem !important;
    box-sizing: border-box !important;
}


/* Brand header */
.topline {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    border-top: 1px solid var(--gold);
    border-bottom: 1px solid var(--line);
    padding: 12px 0;
    margin-bottom: 1.4rem;
    color: var(--muted);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2.2px;
    text-transform: uppercase;
}
.topline .brand-mark { color: var(--burgundy); letter-spacing: 3px; }

.hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    padding: .8rem 0 1.2rem;
    text-align: center !important;
}

.eyebrow {
    color: var(--gold);
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 3.5px;
    text-transform: uppercase;
    margin-bottom: .55rem;
}
.hero-title {
    color: var(--burgundy) !important;
    font-family: 'Cormorant Garamond', Georgia, serif !important;
    font-size: clamp(2.8rem, 4.8vw, 4.4rem) !important;
    font-weight: 600 !important;
    letter-spacing: -1.5px !important;
    line-height: 1 !important;
    margin: 0 !important;
}
.hero-title em { color: var(--gold) !important; font-weight: 400; }
.hero-subtitle {
    display: block;
    width: min(780px, 100%);
    max-width: 780px;
    margin: .7rem auto 0 !important;
    padding: 0 1rem;
    box-sizing: border-box;
    align-self: center;
    color: var(--muted);
    font-size: 14px;
    font-weight: 500;
    line-height: 1.65;
    text-align: center !important;
}
.ornament {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin: 1.2rem auto 0;
    color: var(--gold);
}
.ornament:before, .ornament:after {
    content: "";
    width: 52px;
    height: 1px;
    background: var(--gold-light);
}

/* Headings and section labels */
h1, h2, h3 {
    font-family: 'Cormorant Garamond', Georgia, serif !important;
    color: var(--burgundy) !important;
    font-weight: 500 !important;
}
h2 { font-size: 2rem !important; }
h3 { font-size: 1.55rem !important; }

/* =========================================
   EDITORIAL ANALYTICS — SECTION TYPOGRAPHY
========================================= */

/* Section label */
.section-kicker {
    display: block;
    color: #9A7847 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 1.1px !important;
    line-height: 1.5 !important;
    text-transform: uppercase;

    margin: 0 0 7px 0 !important;
    padding: 0 !important;
}

/* Main section title */
.section-title {
    color: var(--burgundy) !important;
    font-family: 'Cormorant Garamond', Georgia, serif !important;
    font-size: 2.15rem !important;
    font-weight: 600 !important;
    line-height: 1.15 !important;

    margin: 0 0 7px 0 !important;
    padding: 0 !important;
}

/* Section description */
.section-description {
    color: var(--muted) !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    line-height: 1.65 !important;

    margin: 0 !important;
    padding: 0 !important;
    max-width: 900px;
}

/* Heading container */
.panel-heading {
    border-bottom: 1px solid rgba(185, 150, 105, 0.38) !important;
    padding: 0 0 14px 0 !important;
    margin: 0 0 18px 0 !important;
}


/* =========================================
   UNIFIED SEGMENTED CONTROL
   MAIN NAVIGATION + INPUT MODE
========================================= */


/* Menu điều hướng chính */
.st-key-main_navigation {
    width: 100% !important;
    margin: 0 auto 0 !important;
    padding-bottom: 0 !important;
}

/* Menu chọn phương thức nhập */
.st-key-input_mode_selector {
    width: 100% !important;
    margin: 0 auto 0px !important;
    padding-bottom: 0 !important;
}

/* Thu hẹp khoảng cách trước ô nhập bình luận */
.st-key-input_mode_selector + div {
    margin-top: -12px !important;
}


/* Căn chỉnh vị trí */
.st-key-main_navigation > div,
.st-key-main_navigation [data-testid="stElementContainer"],
.st-key-input_mode_selector > div,
.st-key-input_mode_selector [data-testid="stElementContainer"] {
    width: 100% !important;
}

/* Khung menu */
.st-key-main_navigation [role="radiogroup"],
.st-key-input_mode_selector [role="radiogroup"] {
    display: flex !important;
    align-items: center !important;
    gap: 0 !important;

    width: fit-content !important;
    max-width: 100% !important;

    padding: 5px !important;
    background: #F0E7DC !important;
    border: 1px solid #E4D5C4 !important;
    border-radius: 10px !important;

    box-shadow: none !important;
}

/* Căn giữa menu chính */
.st-key-main_navigation [role="radiogroup"] {
    justify-content: center !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* Căn trái menu nhập liệu */
.st-key-input_mode_selector [role="radiogroup"] {
    justify-content: flex-start !important;
    margin-left: 0 !important;
    margin-right: auto !important;
}

/* Các nút */
.st-key-main_navigation button[data-variant="segmented_control"],
.st-key-input_mode_selector button[data-variant="segmented_control"] {
    min-height: 40px !important;
    padding: 8px 20px !important;

    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 5px !important;

    color: #6F6258 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;

    box-shadow: none !important;
    transition: all .18s ease !important;
}

/* Nội dung chữ */
.st-key-main_navigation button[data-variant="segmented_control"] p,
.st-key-input_mode_selector button[data-variant="segmented_control"] p {
    color: inherit !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
}

/* Nút đang được chọn */
.st-key-main_navigation button[data-variant="segmented_control"][data-selected="true"],
.st-key-input_mode_selector button[data-variant="segmented_control"][data-selected="true"] {
    background: #552824 !important;
    border-color: #552824 !important;
    color: #FFFEFC !important;
}

/* Hover nút chưa chọn */
.st-key-main_navigation button[data-variant="segmented_control"]:not([data-selected="true"]):hover,
.st-key-input_mode_selector button[data-variant="segmented_control"]:not([data-selected="true"]):hover {
    background: #E8D9C8 !important;
    color: #552824 !important;
}


/* Streamlit bordered panels and columns */
/* MAIN CONTENT — BALANCED PANELS */

div[data-testid="stHorizontalBlock"] {
    gap: 1.25rem !important;
    align-items: stretch !important;
}


div[data-testid="stVerticalBlockBorderWrapper"] {
    min-height: 0 !important;
    height: 100% !important;
    background: linear-gradient(
        145deg,
        #FFFCF7 0%,
        #F8EEE2 100%
    ) !important;
    border: 1px solid #D9BFA8 !important;
    border-radius: 9px !important;
    box-shadow: 0 3px 10px rgba(84, 45, 42, .035) !important;
    overflow: hidden !important;
}


div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 1.35rem !important;
    background: transparent !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
    background: transparent !important;
}


/* =========================================
   LUXURY EDITORIAL — REVIEW TEXTAREA
========================================= */

.stTextArea textarea,
[data-testid="stTextArea"] textarea {
    /* Typography */
    font-family: 'Lato', Arial, sans-serif !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    line-height: 1.8 !important;
    color: #4A342E !important;

    /* Background */
    background: #FFFCF7 !important;

    /* Border */
    border: 1px solid #DCCFBD !important;
    border-radius: 9px !important;

    /* Spacing */
    padding: 15px 17px !important;
    min-height: 140px !important;

    /* Effects */
    box-shadow: 0 2px 8px rgba(85, 40, 36, 0.025) !important;
    transition: all 0.25s ease !important;

    /* Other */
    resize: vertical !important;
    outline: none !important;
}

/* Placeholder */
.stTextArea textarea::placeholder {
    color: #A99A8B !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    opacity: 1 !important;
}

/* Khi người dùng click vào ô nhập */
.stTextArea textarea:focus,
[data-testid="stTextArea"] textarea:focus {
    background: #FFFEFC !important;
    border: 1px solid #B18A4E !important;
    box-shadow: 0 0 0 3px rgba(177, 138, 78, 0.12) !important;
}

/* Hover */
.stTextArea textarea:hover:not(:focus) {
    border-color: #C8AD8C !important;
    background: #FFFEFC !important;
}


/* CHARACTER COUNTER */
[data-testid="stCaptionContainer"] {
    margin-top: -5px !important;
}



/* =========================================
   MINIMAL LUXURY - CSV SECTION
========================================= */

.csv-intro {
    margin: 8px 0 18px !important;
}

.csv-intro-title {
    color: #552824 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 17px !important;
    font-weight: 700 !important;
    margin-bottom: 6px !important;
}

.csv-description {
    color: #79685B !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 12px !important;
    line-height: 1.6 !important;
    margin: 0 !important;
}

/* Upload container */
[data-testid="stFileUploader"] {
    margin: 0 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: #F7F0E6 !important;
    border: 1px dashed #CBB99F !important;
    border-radius: 9px !important;
    padding: 18px !important;
    transition: .2s ease !important;
}

[data-testid="stFileUploaderDropzone"]:hover {
    background: #FBF5EC !important;
    border-color: #A98249 !important;
}

/* Hướng dẫn */
.csv-guideline {
    display: flex;
    align-items: center;
    gap: 9px;
    margin: 12px 0 16px !important;
    padding: 10px 12px !important;
    background: #F4EBDD !important;
    border-left: 2px solid #B18A4E !important;
    border-radius: 3px 6px 6px 3px !important;
}

.csv-guideline p {
    margin: 0 !important;
    color: #79685B !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 11px !important;
    line-height: 1.6 !important;
}

/* CSV SELECTED FILE — LUXURY FILE CARD */

.csv-selected-file {
    display: flex;
    align-items: center;
    gap: 14px;

    width: 100%;
    box-sizing: border-box;

    padding: 14px 16px;
    margin: 10px 0 14px;

    background: #FBF6EE;
    border: 1px solid #E4D5C4;
    border-radius: 9px;

    transition: all .2s ease;
}

.csv-selected-file:hover {
    border-color: #C5A77D;
    background: #FFFCF7;
}

/* Biểu tượng CSV */
.csv-file-icon {
    display: flex;
    align-items: center;
    justify-content: center;

    flex: 0 0 42px;
    width: 42px;
    height: 42px;

    background: #552824;
    color: #FFFFFF;

    border-radius: 7px;

    font-family: 'Lato', sans-serif;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .5px;
}

/* Khu vực thông tin file */
.csv-file-info {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 5px;

    min-width: 0;
    flex: 1;
}

/* Tên file */
.csv-file-info strong {
    color: #552824 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;

    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Dung lượng và trạng thái */
.csv-file-info span {
    color: #8A7D72 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 11px !important;
    font-weight: 500 !important;
}

/* Trạng thái sẵn sàng */
.csv-file-status {
    display: flex;
    align-items: center;
    gap: 5px;

    color: #68765D !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    white-space: nowrap;
}

.csv-file-status::before {
    content: "✓";
    display: inline-flex;
    align-items: center;
    justify-content: center;

    width: 17px;
    height: 17px;

    background: #E4EEDF;
    border-radius: 50%;
    color: #68765D;
    font-size: 10px;
}

/* Ẩn các nhãn hướng dẫn cũ nếu còn sử dụng */
.csv-upload-heading,
.csv-limit {
    display: none !important;
}


/* Buttons */
.stButton > button, .stDownloadButton > button,
.stFormSubmitButton > button {
    min-height: 42px;
    border-radius: 6px !important;
    border: 1px solid var(--burgundy) !important;
    background: var(--burgundy) !important;
    color: #FFFFFF !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 11px !important;
    font-weight: 900 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase;
    transition: background .18s ease, border-color .18s ease, transform .18s ease;
}
.stButton > button p, .stButton > button span,
.stDownloadButton > button p, .stFormSubmitButton > button p {
    color: #FFFFFF !important;
}
.stButton > button:hover, .stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: var(--burgundy-deep) !important;
    border-color: var(--gold) !important;
    transform: translateY(-1px);
}

/* Metadata and review content */
.metadata {
    background: #F2EBDD;
    border-left: 3px solid var(--gold);
    padding: 12px 14px;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
}
.metadata-label {
    color: var(--muted);
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 3px;
}
.metadata-value {
    color: var(--burgundy);
    font-size: 13px;
    font-weight: 800;
    line-height: 1.6;
    overflow-wrap: anywhere;
}
.review-content {
    color: var(--ink);
    font-size: 14px;
    font-weight: 500;
    line-height: 1.8;
    padding: 10px 0 2px;
    overflow-wrap: anywhere;
}


/* Results table */
.result-count {
    display: inline-block;
    border: 1px solid var(--gold-light);
    border-radius: 4px;
    color: var(--burgundy);
    padding: 6px 11px;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: 4px 0 12px;
}

.result-table-wrapper {
    width: 100%;
    overflow-x: auto;
    border: 1px solid #E8D8C5;
    border-radius: 9px;
    background: #F8F0E5;
}

.result-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    table-layout: fixed;
    font-family: 'Lato', sans-serif;
    font-size: 13px;
    color: #654B40;
}


/* TIÊU ĐỀ BẢNG - FIX FONT TIẾNG VIỆT */
.result-table thead th,
.result-table thead th * {
    background: #EAD7BF !important;
    color: #654B40 !important;

    font-family: 'Lato', Arial, sans-serif !important;
    font-style: normal !important;
    font-weight: 700 !important;
    font-size: 13px !important;

    text-align: left;
    line-height: 1.5 !important;
    letter-spacing: 0 !important;

    padding: 13px 14px;
    border-bottom: 1px solid #DFC8AE;

    -webkit-font-smoothing: antialiased;
}


/* Căn giữa cột cảm xúc và độ tin cậy */
.result-table th:nth-child(2),
.result-table td:nth-child(2),
.result-table th:nth-child(3),
.result-table td:nth-child(3) {
    text-align: center;
}

/* Nội dung bảng */
.result-table td {
    padding: 12px 14px;
    border-bottom: 1px solid #EADFD2;
    background: #F8F0E5;
    vertical-align: middle;
    overflow-wrap: anywhere;
}

/* Nền xen kẽ */
.result-table tbody tr:nth-child(even) td {
    background: #F2E6D8;
}

.result-table tbody tr:hover td {
    background: #F6EAD9;
}

.result-table tbody tr:last-child td {
    border-bottom: none;
}

/* Tỷ lệ chiều rộng các cột */
.result-table th:nth-child(1),
.result-table td:nth-child(1) { width: 43%; }

.result-table th:nth-child(2),
.result-table td:nth-child(2) { width: 34%; }

.result-table th:nth-child(3),
.result-table td:nth-child(3) { width: 23%; }

/* Nhãn cảm xúc */
.sentiment-badge {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
}

.positive {
    background: #E4EEDF;
    color: #66845C;
}

.negative {
    background: #F1DFD9;
    color: #A66B5C;
}

.neutral {
    background: #F5E9C9;
    color: #9B7A37;
}

.absent {
    background: #E8E3DC;
    color: #81766B;
}

.confidence-cell {
    font-weight: 700;
    color: var(--burgundy);
}


/* Metrics, dataframes and general Streamlit elements */
[data-testid="stMetric"] {
    background: rgba(255,255,255,.82);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 12px 14px;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 9px;
    overflow: hidden;
    background: #FFFFFF;
}
[data-testid="stCaptionContainer"] p, .stCaption {
    color: var(--muted) !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 11px !important;
}
[data-testid="stAlert"] { border-radius: 8px !important; }
hr { border-color: var(--line) !important; }

/* Dashboard */
.dashboard-shell { margin-bottom: .9rem; }

/* EMPTY DASHBOARD — CHART CARDS */

.empty-chart-heading {
    padding: 2px 2px 12px;
    margin-bottom: 4px;
    border-bottom: 1px solid #E8DCCB;
}

.empty-chart-title {
    color: #552824;
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.45rem;
    font-weight: 600;
    line-height: 1.3;
}

.empty-chart-description {
    color: #8A7D72;
    font-family: 'Lato', sans-serif;
    font-size: 11px;
    line-height: 1.6;
    margin-top: 4px;
}

/* Card biểu đồ */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #DCCFBD !important;
    border-radius: 12px !important;
    background: linear-gradient(
        145deg,
        #FFFCF7 0%,
        #F8F1E8 100%
    ) !important;
    box-shadow: 0 3px 12px rgba(85, 40, 36, 0.035) !important;
}


.insight {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: stretch;
    gap: 16px;
    margin: 4px 0 18px;
}

.insight-item {
    display: flex;
    align-items: center;
    gap: 16px;
    box-sizing: border-box;
    min-height: 124px;
    padding: 20px 22px;
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 12px;
}

.insight-icon {
    flex: 0 0 42px;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.insight-text {
    flex: 1;
    min-width: 0;
    font-size: 12px;
    color: var(--muted);
    line-height: 1.5;
}

.insight-icon {
    flex: 0 0 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
    font-weight: 700;
}
.insight-item.good .insight-icon { background: #E3ECD9; color: #526B43; }
.insight-item.bad .insight-icon { background: #F0DDD6; color: #914C3D; }
.insight-text { font-size: 12px; color: var(--muted); line-height: 1.5; }
.insight-text b {
    display: block;
    color: var(--burgundy);
    font-size: 1.3rem;
    font-weight: 700;
    line-height: 1.2;
    margin: 4px 0;
}
.kpi {
    background: var(--paper);
    border: 1px solid var(--line);
    border-top: 3px solid var(--gold);
    border-radius: 11px;
    padding: 15px 16px;
    height: 100%;
}
.kpi-label { color: var(--muted); font-size: 11px; font-weight: 700; margin-bottom: 6px; }
.kpi-value {
    color: var(--burgundy);
    font-size: 2.4rem;
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-weight: 700;
    line-height: 1;
}
.kpi-note { color: #8A7D72; font-size: 11px; font-weight: 500; margin-top: 8px; line-height: 1.4; }
.tbl-wrap { width: 100%; overflow-x: auto; border: 1px solid #E3D0BC; border-radius: 9px; background: var(--paper); }
.tbl { width: 100%; border-collapse: separate; border-spacing: 0; font-family: 'Lato', sans-serif; font-size: 12px; color: #4A342E; }
.tbl th { background: #EAD7C2; color: var(--burgundy); font-weight: 800; text-align: left; padding: 11px 13px; border-bottom: 1px solid #D8B98F; white-space: nowrap; }
.tbl td { padding: 10px 13px; border-bottom: 1px solid #F0E4D6; background: var(--paper); vertical-align: middle; }
.tbl tbody tr:nth-child(even) td { background: #FBF5EC; }
.tbl tbody tr:hover td { background: #F6EAD9; }
.tbl tbody tr:last-child td { border-bottom: none; }
.tbl .num { text-align: center; font-weight: 700; font-variant-numeric: tabular-nums; }
.tbl .pos-n { color: #526B43; }
.tbl .neg-n { color: #914C3D; }
.tbl .neu-n { color: #8A641F; }
.tbl .dim { color: #B0A294; font-weight: 500; }
/* =====================================
   CSV BATCH SUMMARY TABLE
===================================== */

.batch-summary-wrap {
    width: 100%;
    overflow-x: auto;
    border: 1px solid #E3D0BC;
    border-radius: 10px;
    background: #FFFCF7;
    box-shadow: 0 2px 8px rgba(85, 40, 36, 0.04);
}

.batch-summary-table {
    width: 100%;
    min-width: 0;
    table-layout: fixed;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 11px;
}

/* Tiêu đề */
.batch-summary-table th {
    padding: 13px 10px;
    background: #EAD7C2;
    color: #552824;
    font-size: 11px;
    font-weight: 800;
    text-align: center;
    white-space: nowrap;
    border-bottom: 1px solid #D8B98F;
}

/* Nội dung */
.batch-summary-table td {
    padding: 13px 10px;
    height: 48px;
    vertical-align: middle;
    border-bottom: 1px solid #F0E4D6;
    white-space: nowrap;
}

/* Cột Khía cạnh */
.batch-summary-table th:first-child,
.batch-summary-table td:first-child {
    width: 30%;
    text-align: left;
    white-space: normal;
    overflow-wrap: break-word;
    line-height: 1.4;
}

/* 4 cột số liệu */
.batch-summary-table th:nth-child(2),
.batch-summary-table th:nth-child(3),
.batch-summary-table th:nth-child(4),
.batch-summary-table th:nth-child(5),
.batch-summary-table td:nth-child(2),
.batch-summary-table td:nth-child(3),
.batch-summary-table td:nth-child(4),
.batch-summary-table td:nth-child(5) {
    width: 11%;
    text-align: center;
    white-space: nowrap;
}

/* Cột Tỷ lệ tích cực */
.batch-summary-table th:last-child,
.batch-summary-table td:last-child {
    width: 26%;
    text-align: center;
    white-space: nowrap;
}

/* Màu số liệu */
.batch-summary-table td:nth-child(2) {
    color: #526B43;
    font-weight: 700;
}

.batch-summary-table td:nth-child(3) {
    color: #A65D50;
    font-weight: 700;
}

.batch-summary-table td:nth-child(4) {
    color: #9B7A37;
    font-weight: 700;
}


.batch-summary-table tbody tr:nth-child(even) td {
    background: #FBF5EC;
}

.batch-summary-table tbody tr:hover td {
    background: #F3E8D9;
}

.batch-summary-table tbody tr:last-child td {
    border-bottom: none;
}
.mix {
    display: flex;
    width: 150px;
    max-width: 100%;
    height: 12px;
    border-radius: 20px;
    overflow: hidden;
    background: #EADFCF;
}

.mix i {
    display: block;
    height: 100%;
    cursor: help;
}

.mix .p { background: #68765D; }
.mix .n { background: #A65D50; }
.mix .u { background: #D4BE96; }

.mix-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
}
.rv {
    background: var(--paper);
    border: 1px solid var(--line);
    border-left: 4px solid var(--sage);
    border-radius: 9px;
    padding: 12px 15px;
    margin-bottom: 10px;
}
.rv.negative { border-left-color: var(--rose); }
.rv.neutral { border-left-color: #D4BE96; }
.rv-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 7px; }
.rv-id { color: var(--muted); font-size: 11px; font-weight: 700; }
.rv-conf { color: var(--muted); font-size: 11px; font-weight: 600; margin-left: 8px; }
.rv-body { color: var(--ink); font-size: 13px; line-height: 1.8; font-weight: 500; overflow-wrap: anywhere; }
/* EMPTY STATE — KHUNG CHỜ PHÂN TÍCH */

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;

    width: 100%;
    min-height: 250px;
    box-sizing: border-box;

    padding: 35px 25px;
    margin-top: 4px;

    background: #FBF6EE;
    border: 1px dashed #DCC9AE;
    border-radius: 3px;
}

.empty-state-icon {
    color: #B18A4E;
    font-size: 34px;
    line-height: 1;
    margin-bottom: 22px;
}

.empty-state-title {
    color: #552824 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 20px !important;
    font-weight: 800 !important;
    margin-bottom: 12px !important;
}

.empty-state-description {
    max-width: 430px;
    color: #8A7D72 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    line-height: 1.8 !important;
    margin: 0 !important;
}

@media screen and (max-width: 760px) {
    .empty-state {
        min-height: 210px;
        padding: 25px 15px;
    }

    .empty-state-title {
        font-size: 18px !important;
    }
}
/* Footer */
.page-footer {
    border-top: 1px solid var(--gold-light);
    margin-top: 1.7rem;
    padding-top: 13px;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--muted);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* Short laptop screens */
@media screen and (min-width: 761px) and (max-height: 850px) {
    .block-container { padding-top: .3rem !important; padding-bottom: 1rem !important; }
    .hero { padding: .15rem 0 .55rem; }
    .hero-title { font-size: clamp(2.6rem, 4vw, 3.7rem) !important; }
    .hero-subtitle { margin-top: .45rem !important; line-height: 1.5; }
    div[role="tablist"] { margin-bottom: .65rem !important; }
}

/* Tablet and mobile */
@media screen and (max-width: 760px) {
    .block-container {
        width: calc(100% - 24px) !important;
        padding: .5rem .25rem 1rem !important;
    }
    .hero { padding: .25rem 0 .7rem; }
    .hero-title { font-size: clamp(2.35rem, 9vw, 3.2rem) !important; }
    .hero-subtitle { font-size: 12px; line-height: 1.55; padding: 0 .4rem; }
    div[data-testid="stHorizontalBlock"] { gap: .7rem !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: .8rem !important; }
    .section-title { font-size: 1.65rem; }
    .insight { grid-template-columns: 1fr; }
    .page-footer { flex-direction: column; gap: 6px; }
    .topline { flex-wrap: wrap; margin-bottom: .8rem; }
}


/* =========================================
   UNIFIED UI TYPOGRAPHY — LATO
========================================= */

/* EDITORIAL TYPOGRAPHY SYSTEM */

/* Nội dung mặc định */
.stApp,
.stApp p,
.stApp label,
.stApp input,
.stApp textarea,
.stApp select,
.stApp button,
.stApp [data-testid="stMarkdownContainer"] {
    font-family: 'Lato', sans-serif !important;
}

/* Tiêu đề lớn */
.hero-title,
h1,
h2,
h3,
.section-title {
    font-family: 'Cormorant Garamond', Georgia, serif !important;
    color: #552824 !important;
}

/* Tiêu đề khu vực */
.section-title {
    font-size: 2.15rem !important;
    font-weight: 600 !important;
    line-height: 1.15 !important;
}

/* Nội dung mô tả */
.hero-subtitle,
.section-description,
.review-content {
    font-family: 'Lato', sans-serif !important;
    color: #6F6258 !important;
}

/* Các control nhập liệu */
.stTextArea textarea,
.stTextInput input,
.stSelectbox,
.stMultiSelect,
[data-testid="stSegmentedControl"] button {
    font-family: 'Lato', sans-serif !important;
}


/* =========================================
   DASHBOARD — SENTIMENT MULTISELECT TAGS
========================================= */

/* TAG 1 — TÍCH CỰC: XANH SAGE */
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Tích cực"] {
    background-color: #68765D !important;
    border: 1px solid #68765D !important;
    border-radius: 6px !important;
    color: #FFFFFF !important;
}

/* TAG 2 — TRUNG LẬP: VÀNG CHAMPAGNE */
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Trung lập"] {
    background-color: #D4BE96 !important;
    border: 1px solid #D4BE96 !important;
    border-radius: 6px !important;
    color: #552824 !important;
}

/* TAG 3 — TIÊU CỰC: NÂU ĐỎ */
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Tiêu cực"] {
    background-color: #A65D50 !important;
    border: 1px solid #A65D50 !important;
    border-radius: 6px !important;
    color: #FFFFFF !important;
}

/* Đảm bảo chữ kế thừa đúng màu từ tag */
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Tích cực"] span,
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Tiêu cực"] span {
    color: #FFFFFF !important;
}

[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Trung lập"] span {
    color: #552824 !important;
}

/* Icon X — Tích cực và Tiêu cực: trắng */
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Tích cực"] button,
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Tiêu cực"] button {
    color: #FFFFFF !important;
}

/* Icon X — Trung lập: nâu đậm */
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag][aria-label="Trung lập"] button {
    color: #552824 !important;
}

/* Giữ màu icon SVG theo currentColor */
[data-testid="stMultiSelect"]
[data-testid="stMultiSelectTagsContainer"]
span[data-tag] button svg path {
    stroke: currentColor !important;
}


</style>
""", unsafe_allow_html=True)
# =========================================================
# 5. SESSION STATE
# =========================================================
# Lưu trạng thái nhập liệu và kết quả phân tích
# để duy trì dữ liệu khi Streamlit thực hiện rerun.
defaults = {
    "review": "",
    "single_result": None,
    "last_batch": None,
    "last_batch_detail": None,
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
    <h1 class="hero-title">Restaurant Review <em>AI</em></h1>
    <p class="hero-subtitle">
        Khám phá cảm xúc ẩn sau từng đánh giá nhà hàng.
        Phân tích các khía cạnh trải nghiệm — từ chất lượng món ăn,
        giá cả đến dịch vụ và không gian.
    </p>
</section>
""", unsafe_allow_html=True)

# Thanh điều hướng chính
with st.container(key="main_navigation"):
    selected_tab = st.segmented_control(
        "Điều hướng chức năng",
        [
            "Phân tích bình luận",
            "Dashboard",
        ],
        default="Phân tích bình luận",
        selection_mode="single",
        label_visibility="collapsed",
        key="main_navigation_control",
    )

# =========================================================
# 7. UNIFIED REVIEW ANALYSIS — SINGLE REVIEW + CSV
# =========================================================
if selected_tab == "Phân tích bình luận":

    left_col, right_col = st.columns([1, 1], gap="large")

    # -----------------------------------------------------
    # LEFT: INPUT
    # -----------------------------------------------------
    with left_col:
        with st.container(border=True):
            st.markdown(
                """
                <div class="panel-heading">
                    <div class="section-title">Phân tích bình luận</div>
                    <div class="section-description">
                        Nhập trực tiếp một bình luận hoặc tải lên tệp CSV
                        để phân tích nhiều đánh giá cùng lúc.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.container(key="input_mode_selector"):
                input_mode = st.segmented_control(
                    "Phương thức nhập dữ liệu",
                    ["Nhập bình luận", "Tải tệp CSV"],
                    default="Nhập bình luận",
                    selection_mode="single",
                    label_visibility="collapsed",
                    key="review_input_mode",
                )

            if input_mode == "Nhập bình luận":
                st.text_area(
                    "Nội dung đánh giá",
                    key="review",
                    placeholder="Ví dụ: Đồ ăn ngon, giá hợp lý nhưng phục vụ hơi chậm...",
                    height=140,
                    max_chars=1000,
                    label_visibility="collapsed",
                )


                st.caption(f"{len(st.session_state.review)} / 1.000 ký tự")

                button_col1, button_col2 = st.columns(2)
                with button_col1:
                    analyze_single = st.button(
                        "Phân tích →",
                        use_container_width=True,
                        key="analyze_single",
                    )

                with button_col2:
                    st.button(
                        "Xóa nội dung",
                        use_container_width=True,
                        on_click=clear_review,
                        key="clear_single",
                    )

                if analyze_single:
                    review_content = st.session_state.review.strip()
                    if not review_content:
                        st.warning(
                            "Vui lòng nhập nội dung bình luận trước khi phân tích."
                        )
                    else:
                        try:
                            with st.spinner("Đang phân tích bình luận..."):
                                response = api_request(
                                    "POST",
                                    "/analyze",
                                    json={"review": review_content},
                                ).json()

                            st.session_state.single_result = response
                            st.session_state.last_batch = None
                            st.session_state.last_batch_detail = None
                            st.success("Phân tích bình luận thành công.")
                        except RuntimeError as error:
                            st.session_state.single_result = None
                            st.error(str(error))


            elif input_mode == "Tải tệp CSV":
                # Khu vực tải tệp CSV
                uploaded_file = st.file_uploader(
                    "Chọn tệp đánh giá CSV",
                    type=["csv"],
                    accept_multiple_files=False,
                    key="batch_csv_upload",
                    label_visibility="collapsed",
                    help="Chọn tệp CSV có cột Review."
                )

                # Kiểm tra dung lượng tệp
                file_too_large = (
                    uploaded_file is not None
                    and uploaded_file.size > 10 * 1024 * 1024
                )

                # Kiểm tra dung lượng tệp
                file_too_large = (
                    uploaded_file is not None
                    and uploaded_file.size > 10 * 1024 * 1024
                )

                if uploaded_file is not None:

                    if file_too_large:
                        st.error(
                            "Tệp vượt quá dung lượng cho phép. "
                            "Vui lòng chọn tệp CSV không quá 10 MB."
                        )
                    else:

                        st.html(f"""
                        <div class="csv-selected-file">
                            <div class="csv-file-icon">CSV</div>

                            <div class="csv-file-info">
                                <strong>{html.escape(uploaded_file.name)}</strong>
                                <span>{uploaded_file.size / 1024:.1f} KB · Tệp dữ liệu đánh giá</span>
                            </div>

                            <div class="csv-file-status">Sẵn sàng</div>
                        </div>
                        """)



                # Nút thực hiện phân tích
                run_batch = st.button(
                    "Phân tích đánh giá →",
                    use_container_width=True,
                    disabled=uploaded_file is None or file_too_large,
                    key="run_batch",
                )

                if run_batch and uploaded_file is not None:
                    try:
                        with st.spinner(
                            "Đang tải dữ liệu lên và phân tích. Vui lòng chờ..."
                        ):
                            batch_response = api_request(
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

                            batch_id = batch_response.get("batch_id")
                            if not batch_id:
                                raise RuntimeError(
                                    "Backend không trả về batch_id sau khi phân tích CSV."
                                )

                            detail_response = api_request(
                                "GET",
                                f"/batches/{batch_id}",
                            ).json()

                        st.session_state.last_batch = batch_response
                        st.session_state.last_batch_detail = detail_response
                        st.session_state.selected_batch_id = batch_id
                        st.session_state.single_result = None
                        st.success("Phân tích CSV thành công.")



                    except RuntimeError as error:
                        error_message = str(error)

                        error_items = re.findall(
                            r"Dòng\s+(\d+):\s*(.*?)(?=\s*Dòng\s+\d+:|$)",
                            error_message,
                            re.DOTALL
                        )

                        if error_items:
                            grouped_errors = {}

                            for row_number, reason in error_items:
                                reason = reason.strip()

                                if "không được để trống" in reason:
                                    category = "Review bị để trống"

                                elif "vượt quá" in reason:
                                    category = "Review vượt giới hạn ký tự"

                                elif "bị trùng" in reason:
                                    category = "review_id bị trùng"

                                else:
                                    category = reason

                                grouped_errors.setdefault(category, []).append(
                                    row_number
                                )

                            with st.container(border=True):
                                st.error(
                                    f"Không thể phân tích tệp CSV — "
                                    f"{len(error_items)} lỗi đầu vào"
                                )

                                for category, rows in grouped_errors.items():
                                    row_numbers = sorted(set(rows), key=int)

                                    st.markdown(
                                        f"- **{category}:** {len(rows)} lỗi "
                                        f"— Dòng {', '.join(row_numbers)}."
                                    )

                                st.caption(
                                    "Vui lòng sửa dữ liệu và tải lại file. "
                                    "Chưa có bình luận nào được phân tích."
                                )

                        else:
                            st.error(error_message)


                
    # -----------------------------------------------------
    # RIGHT: RESULTS
    # -----------------------------------------------------
    with right_col:
        with st.container(border=True):

            st.markdown("""
            <div class="panel-heading">
                <div class="section-title">Kết quả phân tích</div>
                <div class="section-description">
                    Kết quả phân tích cảm xúc theo từng khía cạnh
                    trong trải nghiệm nhà hàng.
                </div>
            </div>
            """, unsafe_allow_html=True)

            if input_mode == "Nhập bình luận":

                result = st.session_state.single_result

                if result:
                    render_results_table(
                        result.get("results", []),
                        key_prefix="single",
                        show_filter=True,
                    )

                    st.caption(
                        "Độ tin cậy là điểm số của mô hình, "
                        "chưa được hiệu chuẩn thành xác suất."
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
                            st.info(
                                "Chưa nhận diện thấy dấu hiệu cách diễn đạt đặc biệt."
                            )

                        if style_result.get("message"):
                            st.caption(style_result["message"])

                    with st.expander(
                        "Thông tin kỹ thuật của lần phân tích"
                    ):
                        st.write(
                            f"Review ID: {result.get('review_id', '—')}"
                        )
                        st.write(
                            f"Batch ID: {result.get('batch_id', '—')}"
                        )

                else:
                    render_empty_state(
                        "Nhập bình luận ở khung bên trái và chọn "
                        "Phân tích để xem kết quả tại đây."
                    )

            else:

                batch_response = st.session_state.last_batch
                detail_response = st.session_state.get(
                    "last_batch_detail"
                )


                if batch_response and detail_response:

                    batch_info = detail_response.get("batch", {})
                    all_results = detail_response.get("results", [])

                    # Hiển thị 2 chỉ số tổng quan
                    render_batch_summary(batch_info)

                    if all_results:

                        review_ids = list(dict.fromkeys(
                            str(item.get("review_id", ""))
                            for item in all_results
                        ))

                        st.markdown("""
                        <style>
                        /* Hộp chọn bình luận */
                        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                            background-color: #FFFCF7 !important;
                            border: 1px solid #E4D5C4 !important;
                            border-radius: 10px !important;
                            min-height: 44px;
                            box-shadow: none !important;
                        }

                        /* Màu chữ trong hộp chọn */
                        div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
                            color: #552824 !important;
                            font-family: 'Lato', sans-serif !important;
                            font-size: 14px !important;
                        }

                        /* Màu mũi tên */
                        div[data-testid="stSelectbox"] svg {
                            fill: #9A7545 !important;
                        }

                        /* Checkbox */
                        div[data-testid="stCheckbox"] {
                            color: #552824 !important;
                        }

                        div[data-testid="stCheckbox"] input {
                            accent-color: #6A302B !important;
                        }

                        div[data-testid="stCheckbox"] label {
                            color: #552824 !important;
                            font-family: 'Lato', sans-serif !important;
                            font-size: 14px !important;
                        }

                        /* Khoảng cách bộ lọc với bảng */
                        div[data-testid="stCheckbox"] {
                            margin-top: 4px;
                            margin-bottom: 12px;
                        }
                        </style>
                        """, unsafe_allow_html=True)


                        filter_col, checkbox_col = st.columns([1.5, 1])

                        with filter_col:
                            chosen_review = st.selectbox(
                                "Chọn bình luận",
                                options=["Tất cả đánh giá"] + review_ids,
                                key="unified_batch_review_filter",
                                label_visibility="collapsed",
                            )

                        if chosen_review != "Tất cả đánh giá":
                            show_all_aspects = st.checkbox(
                                "Hiển thị tất cả khía cạnh",
                                key="unified_batch_show_all_aspects",
                            )


                        if chosen_review == "Tất cả đánh giá":
                            
                            # TỔNG HỢP TOÀN BỘ BÌNH LUẬN
                            st.markdown(
                                "<div class='section-kicker' style='margin-top:1rem;'>"
                                "TỔNG HỢP CẢM XÚC THEO KHÍA CẠNH"
                                "</div>",
                                unsafe_allow_html=True
                            )

                            summary_df = summarize_batch_results(all_results)

                            if not summary_df.empty:
                                st.markdown(
                                    stats_table_html(
                                        summary_df,
                                        compact=True,
                                        variant="batch"
                                    ),
                                    unsafe_allow_html=True
                                )

                                st.caption(
                                    "Tỷ lệ tích cực được tính trên tổng lượt đề cập "
                                    "(không bao gồm các lượt không đề cập)."
                                )

                        else:

                            # CHI TIẾT MỘT BÌNH LUẬN
                            visible_results = [
                                item for item in all_results
                                if str(item.get("review_id", "")) == chosen_review
                            ]

                            if not show_all_aspects:
                                visible_results = [
                                    item for item in visible_results
                                    if sentiment_label(item.get("Sentiment")) != "Không đề cập"
                                ]

                            st.markdown(
                                "<div class='section-kicker' style='margin-top:1rem;'>"
                                "CHI TIẾT PHÂN TÍCH BÌNH LUẬN"
                                "</div>",
                                unsafe_allow_html=True
                            )

                            render_results_table(
                                visible_results,
                                key_prefix="unified_batch",
                                show_filter=False
                            )

                            st.caption(
                                f"Đang hiển thị {len(visible_results)} "
                                "kết quả khía cạnh."
                            )

                    else:
                        st.info("Batch chưa có kết quả chi tiết để hiển thị.")

                else:
                    render_empty_state(
                        "Tải lên tệp CSV chứa các đánh giá nhà hàng "
                        "và chọn Phân tích đánh giá để xem kết quả tại đây."
                    )



# =========================================================
# 9. DASHBOARD INTEGRATION
# =========================================================
if selected_tab == "Dashboard":
    render_dashboard_panel()
