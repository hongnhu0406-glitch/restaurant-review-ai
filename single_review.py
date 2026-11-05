import html
import requests
import pandas as pd
import streamlit as st

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
# Chạy FastAPI tại http://127.0.0.1:8000 trước khi chạy Streamlit.
API_BASE_URL = "http://127.0.0.1:8000"
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
    st.caption("Confidence thể hiện độ tin cậy của kết quả dự đoán.")


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
    max-width:1500px !important; padding-top:.7rem !important;
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
    padding:.7rem 0 1.45rem; text-align:center !important;
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
.hero-title em {color:var(--gold);font-weight:400;}
.hero-subtitle {
    display:block; width:min(780px,100%); max-width:780px;
    margin:1.1rem auto 0 !important; padding:0 1rem; box-sizing:border-box;
    align-self:center; color:var(--ink); font-size:15px; font-weight:500;
    line-height:1.9; text-align:center !important;
}
.ornament {display:flex;align-items:center;justify-content:center;gap:12px;margin:1.6rem auto 0;color:var(--gold);}
.ornament:before,.ornament:after {content:"";width:52px;height:1px;background:var(--gold-light);}
h1,h2,h3 {font-family:'Cormorant Garamond',Georgia,serif !important;color:var(--burgundy) !important;font-weight:500 !important;}
h2 {font-size:2rem !important;} h3 {font-size:1.55rem !important;}
.section-kicker {color:var(--gold);font-size:9px;font-weight:900;letter-spacing:2.8px;text-transform:uppercase;margin-bottom:5px;}
.section-title {color:var(--burgundy);font-family:'Cormorant Garamond',Georgia,serif;font-size:2.15rem;font-weight:600;line-height:1.1;margin:0 0 .35rem;}
.section-description {color:var(--muted);font-size:13px;font-weight:500;line-height:1.75;margin-bottom:1rem;}
div[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"],
.stVerticalBlockBorderWrapper,
div[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background:linear-gradient(135deg,#FFF8EF 0%,#FBEFE2 55%,#F7E6D7 100%) !important;
    background-color:#F9EEE2 !important; border:1.6px solid #98564B !important;
    border-radius:19px !important;
    box-shadow:0 5px 12px rgba(84,45,42,.06),0 18px 32px rgba(84,45,42,.15) !important;
    overflow:hidden !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {background:transparent !important;}
div[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1.05rem 1.1rem !important;}
div[data-testid="stTextArea"] small {display:none !important;}
[data-testid="stWidgetLabel"] p,.stTextArea label,.stCheckbox label {
    color:var(--burgundy) !important;font-family:'Lato',sans-serif !important;
    font-size:13px !important;font-weight:800 !important;
}
.stTextArea textarea,.stTextInput input {
    background:#FFFEFC !important;border:1px solid #D9C8B5 !important;
    border-radius:2px !important;color:var(--ink) !important;
    font-family:'Lato',sans-serif !important;font-size:15px !important;
    font-weight:500 !important;line-height:1.8 !important;padding:14px 16px !important;
    box-shadow:none !important;
}
.stTextArea textarea:focus,.stTextInput input:focus {border:1px solid var(--gold) !important;box-shadow:0 0 0 1px var(--gold) !important;}
.stTextArea textarea::placeholder {color:#A99D91 !important;font-style:italic;}
.stButton>button,.stDownloadButton>button {
    min-height:44px;border-radius:2px !important;border:1px solid var(--burgundy) !important;
    background:var(--burgundy) !important;color:#FFFDF8 !important;
    font-family:'Lato',sans-serif !important;font-size:12px !important;
    font-weight:900 !important;letter-spacing:1.5px !important;text-transform:uppercase;
    transition:all .2s ease;
}
.stButton>button:hover,.stDownloadButton>button:hover {background:var(--burgundy-deep) !important;border-color:var(--gold) !important;transform:translateY(-1px);}
.stButton>button p,.stButton>button span,.stDownloadButton>button p {color:inherit !important;font-family:'Lato',sans-serif !important;}
[data-testid="stAlert"] {border-radius:2px !important;font-family:'Lato',sans-serif !important;}
.metadata {background:#F2EBDD;border-left:3px solid var(--gold);padding:13px 15px;margin:12px 0;}
.metadata-label {color:var(--muted);font-size:9px;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:3px;}
.metadata-value {color:var(--burgundy);font-size:14px;font-weight:800;line-height:1.6;overflow-wrap:anywhere;}
.review-content {color:var(--ink);font-size:14px;font-weight:500;line-height:1.9;padding:12px 0 2px;overflow-wrap:anywhere;}
.result-count {display:inline-block;border:1px solid var(--gold-light);color:var(--burgundy);padding:6px 11px;font-size:10px;font-weight:900;letter-spacing:1.1px;text-transform:uppercase;margin:4px 0 12px;}
.result-table-wrapper {width:100%;overflow-x:auto;border:1px solid #E3D0BC;border-radius:9px;background:#F8F0E5;}
.result-table {width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;font-family:'Lato',sans-serif;font-size:13px;color:#542D2A;}
.result-table th {background:#EAD7C2;color:#542D2A;font-weight:700;text-align:left;padding:13px 12px;border-bottom:1px solid #D8B98F;}
.result-table td {padding:11px 12px;border-bottom:1px solid #EDE0D1;background:#F8F0E5;vertical-align:middle;overflow-wrap:anywhere;}
.result-table tbody tr:nth-child(even) td {background:#F3E8DA;}
.result-table tbody tr:last-child td {border-bottom:none;}
.result-table th:nth-child(1),.result-table td:nth-child(1) {width:43%;}
.result-table th:nth-child(2),.result-table td:nth-child(2) {width:34%;}
.result-table th:nth-child(3),.result-table td:nth-child(3) {width:23%;text-align:center;}
.sentiment-badge {display:inline-block;padding:5px 10px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap;}
.positive {background:#E3ECD9;color:#526B43;}
.negative {background:#F0DDD6;color:#914C3D;}
.neutral {background:#F5E6C8;color:#8A641F;}
.absent {background:#EDE2D5;color:#806B59;}
.confidence-cell {font-weight:600;color:#542D2A;}
[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:2px;overflow:hidden;background:#FFFEFC;}
[data-testid="stCaptionContainer"] p,.stCaption {color:var(--muted) !important;font-family:'Lato',sans-serif !important;font-size:12px !important;font-weight:600 !important;}
hr {border-color:var(--line) !important;}
.page-footer {border-top:1px solid var(--gold-light);margin-top:2.5rem;padding-top:15px;display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:9px;font-weight:700;letter-spacing:1.7px;text-transform:uppercase;}
@media(max-width:760px) {.block-container{padding:1rem 1rem 2rem !important;}.hero{padding:.5rem 0 1.5rem;}.hero-title{font-size:3.2rem !important;}.page-footer{flex-direction:column;}}
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
    <div class="eyebrow">Understand every dining experience</div>
    <h1 class="hero-title">Restaurant Review <em>AI</em></h1>
    <p class="hero-subtitle">
        Khám phá cảm xúc ẩn sau từng đánh giá nhà hàng.
        Phân tích các khía cạnh trải nghiệm — từ chất lượng món ăn,
        giá cả đến dịch vụ và không gian.
    </p>
    <div class="ornament">✦</div>
</section>
""", unsafe_allow_html=True)

# Kiểm tra kết nối Backend
try:
    health = api_request("GET", "/health").json()
    st.caption("● Backend đang kết nối" if health.get("status") == "healthy"
               else "● Backend chưa xác nhận trạng thái")
except RuntimeError:
    st.warning("Backend chưa chạy. Hãy khởi động FastAPI trước khi phân tích.")

# Các tab chỉ bổ sung luồng thao tác; giữ nguyên hệ thống màu sắc và card hiện tại.
tab_single, tab_batch, tab_history = st.tabs([
    "Phân tích bình luận", "Phân tích hàng loạt", "Lịch sử phân tích"
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
                <div class="section-kicker">01 / Review submission</div>
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
            st.caption("Tối đa 1.000 ký tự · Hỗ trợ tiếng Việt")

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
                <div class="section-kicker">02 / Aspect-based sentiment</div>
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
            else:
                st.markdown("""
                <div style="min-height:280px;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;text-align:center;
                    padding:30px 18px;border:1px dashed #D6B98C;background:rgba(255,250,242,.72);">
                    <div style="color:#B69A68;font-family:'Cormorant Garamond',serif;font-size:38px;margin-bottom:8px;">✦</div>
                    <div style="color:#542D2A;font-family:'Cormorant Garamond',serif;font-size:25px;margin-bottom:7px;">Your analysis awaits</div>
                    <div style="max-width:290px;color:#82766C;font-family:'Lato',sans-serif;font-size:12px;line-height:1.8;">
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
            <div class="section-kicker">03 / Batch submission</div>
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
                    st.success("Đã gửi tệp và nhận phản hồi từ Backend.")
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
        st.caption(f"Trạng thái: {batch_response.get('status', '—')}")
        if batch_response.get("batch_id"):
            st.info("Muốn xem toàn bộ kết quả theo từng khía cạnh, mở tab Lịch sử phân tích và chọn Batch này.")


# =========================================================
# 9. BATCH HISTORY + DETAIL + CSV EXPORT
# =========================================================
with tab_history:
    st.markdown("""
    <div class="section-kicker">04 / Analysis records</div>
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
        except RuntimeError as error:
            st.session_state.batch_history = None
            st.error(str(error))

    batches = st.session_state.get("batch_history")
    if isinstance(batches, list):
        if not batches:
            st.info("Chưa có Batch nào trong lịch sử.")
        else:
            history_rows = []
            for batch in batches:
                history_rows.append({
                    "Batch ID": batch.get("batch_id", ""),
                    "Trạng thái": batch.get("status", ""),
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
                    st.caption(f"Trạng thái: {batch_info.get('status', '—')}")

                    if batch_info.get("error_message"):
                        st.error(str(batch_info["error_message"]))

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
        st.info("Không tải được lịch sử. Kiểm tra Backend rồi nhấn Làm mới lịch sử.")


# =========================================================
# 10. FOOTER
# =========================================================
st.markdown("""
<div class="page-footer">
    <span>Restaurant Review AI</span>
    <span>Aspect-Based Sentiment Analysis</span>
    <span>Designed with care · 2026</span>
</div>
""", unsafe_allow_html=True)
