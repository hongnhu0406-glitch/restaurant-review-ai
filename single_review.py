import streamlit as st
import pandas as pd
import html
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
# 2. DESIGN SYSTEM — LONG TRIỀU INSPIRED
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
.stApp {
    background:radial-gradient(circle at 10% 4%,rgba(177,138,78,.16),transparent 27rem),radial-gradient(circle at 92% 48%,rgba(135,68,59,.055),transparent 30rem),var(--ivory);
}
[data-testid="stHeader"] {background:transparent;}
#MainMenu, footer, .stDeployButton {visibility:hidden;}
.block-container {
    max-width:1500px !important; padding-top:0.7rem !important;
    padding-bottom:2.4rem !important;
}
.topline {
    display:flex; justify-content:space-between; gap:1rem;
    border-top:1px solid var(--gold); border-bottom:1px solid var(--line);
    padding:12px 0; margin-bottom:2.2rem; color:var(--muted);
    font-size:10px; font-weight:700; letter-spacing:2.2px; text-transform:uppercase;
}
.topline .brand-mark {color:var(--burgundy); letter-spacing:3px;}
.hero {
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    width:100%;
    max-width:100%;
    box-sizing:border-box;
    padding:0.7rem 0 1.45rem;
    text-align:center !important;
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
    display:block;
    width:min(780px, 100%);
    max-width:780px;
    margin:1.1rem auto 0 !important;
    padding:0 1rem;
    box-sizing:border-box;
    align-self:center;
    color:var(--ink);
    font-size:15px;
    font-weight:500;
    line-height:1.9;
    text-align:center !important;
}
.ornament {display:flex; align-items:center; justify-content:center; gap:12px; margin:1.6rem auto 0; color:var(--gold);}
.ornament:before,.ornament:after {content:""; width:52px; height:1px; background:var(--gold-light);}
h1,h2,h3 {font-family:'Cormorant Garamond',Georgia,serif !important; color:var(--burgundy) !important; font-weight:500 !important;}
h2 {font-size:2rem !important;} h3 {font-size:1.55rem !important;}
.section-kicker {color:var(--gold);font-size:9px;font-weight:900;letter-spacing:2.8px;text-transform:uppercase;margin-bottom:5px;}
.section-title {color:var(--burgundy);font-family:'Cormorant Garamond',Georgia,serif;font-size:2.15rem;font-weight:600;line-height:1.1;margin:0 0 .35rem;}
.section-description {color:var(--muted);font-size:13px;font-weight:500;line-height:1.75;margin-bottom:1rem;}
/* =====================================================
   MAIN PANELS — target the actual Streamlit bordered card
   Streamlit versions may place the border on the wrapper
   OR on its first inner div, so style both layers.
   ===================================================== */
div[data-testid="stTextArea"] small {
    display: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"],
.stVerticalBlockBorderWrapper,
div[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: linear-gradient(135deg, #FFF8EF 0%, #FBEFE2 55%, #F7E6D7 100%) !important;
    background-color: #F9EEE2 !important;
    border: 1.6px solid #98564B !important;
    border-radius: 19px !important;
    box-shadow:
        0 5px 12px rgba(84, 45, 42, 0.06),
        0 18px 32px rgba(84, 45, 42, 0.15) !important;
    overflow: hidden !important;
}

/* Preserve the card fill through Streamlit's nested layout wrappers */
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
    background: transparent !important;
}

/* Warm ivory background with subtle corner gradients.
   Use background layers only (no fixed pseudo-element overlay) so
   Streamlit widgets remain fully visible and interactive. */
.stApp,
[data-testid="stAppViewContainer"] {
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

.block-container {
    position: relative;
}
.panel-heading {border-bottom:1px solid #D9BFA0;padding-bottom:18px;margin-bottom:20px;}
div[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 1.05rem 1.1rem !important;
}

[data-testid="stWidgetLabel"] p,.stTextArea label,.stCheckbox label {
    color:var(--burgundy) !important;font-family:'Lato',sans-serif !important;
    font-size:13px !important;font-weight:800 !important;
}
.stTextArea textarea {
    background:#FFFEFC !important;border:1px solid #D9C8B5 !important;
    border-radius:2px !important;color:var(--ink) !important;
    font-family:'Lato',sans-serif !important;font-size:15px !important;
    font-weight:500 !important;
    line-height:1.8 !important;padding:14px 16px !important;box-shadow:none !important;
}
.stTextArea textarea:focus {border:1px solid var(--gold) !important;box-shadow:0 0 0 1px var(--gold) !important;}
.stTextArea textarea::placeholder {color:#A99D91 !important;font-style:italic;}
.stButton>button {
    min-height:44px;border-radius:2px !important;border:1px solid var(--burgundy) !important;
    background:var(--burgundy) !important;color:#FFFDF8 !important;
    font-family:'Lato',sans-serif !important;font-size:12px !important;
    font-weight:900 !important;letter-spacing:1.5px !important;text-transform:uppercase;
    transition:all .2s ease;
}
.stButton>button:hover {background:var(--burgundy-deep) !important;border-color:var(--gold) !important;transform:translateY(-1px);}
.stButton>button p,.stButton>button span {color:inherit !important;font-family:'Lato',sans-serif !important;}
[data-testid="stAlert"] {border-radius:2px !important;font-family:'Lato',sans-serif !important;}
.metadata {background:#F2EBDD;border-left:3px solid var(--gold);padding:13px 15px;margin:12px 0;}
.metadata-label {color:var(--muted);font-size:9px;font-weight:900;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:3px;}
.metadata-value {color:var(--burgundy);font-size:14px;font-weight:800;line-height:1.6;overflow-wrap:anywhere;}
.review-content {color:var(--ink);font-size:14px;font-weight:500;line-height:1.9;padding:12px 0 2px;overflow-wrap:anywhere;}
.result-count {display:inline-block;border:1px solid var(--gold-light);color:var(--burgundy);padding:6px 11px;font-size:10px;font-weight:900;letter-spacing:1.1px;text-transform:uppercase;margin:4px 0 12px;}
[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:2px;overflow:hidden;background:#FFFEFC;}
[data-testid="stCaptionContainer"] p,.stCaption {color:var(--muted) !important;font-family:'Lato',sans-serif !important;font-size:12px !important;font-weight:600 !important;}
hr {border-color:var(--line) !important;}
.page-footer {
    border-top:1px solid var(--gold-light);margin-top:2.5rem;padding-top:15px;
    display:flex;justify-content:space-between;gap:12px;color:var(--muted);
    font-size:9px;font-weight:700;letter-spacing:1.7px;text-transform:uppercase;
}
@media(max-width:760px) {
    .block-container {padding:1rem 1rem 2rem !important;}
    .hero {padding:.5rem 0 1.5rem;}
    .hero-title {font-size:3.2rem !important;}
    .page-footer {flex-direction:column;}
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SESSION STATE — giữ nguyên chức năng hiện tại
# =========================================================
if "review" not in st.session_state:
    st.session_state.review = ""
if "result" not in st.session_state:
    st.session_state.result = None
if "batch_counter" not in st.session_state:
    st.session_state.batch_counter = 0
if "review_counter" not in st.session_state:
    st.session_state.review_counter = 0


def clear_review():
    st.session_state.review = ""
    st.session_state.result = None


# =========================================================
# 4. HEADER
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

# =========================================================
# 5. MAIN WORKSPACE
# =========================================================
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

        review = st.text_area(
            "Nội dung đánh giá",
            key="review",
            placeholder="Ví dụ: Đồ ăn ngon, giá hợp lý nhưng phục vụ hơi chậm...",
            height=180,
            max_chars=1000,
            on_change=lambda: None
        )
                
        st.html("""
        <div id="review-live-warning"
            style="display:none; margin:10px 0; padding:12px 15px;
                    border-radius:5px; font-family:'Lato',sans-serif;
                    font-size:13px; line-height:1.6;">
        </div>

        <script>
        (function () {
            const textarea = document.querySelector(
                '[data-testid="stTextArea"] textarea'
            );

            const warning = document.getElementById("review-live-warning");

            if (!textarea || !warning) return;

            function updateWarning() {
                const length = textarea.value.length;

                if (length >= 1000) {
                    warning.style.display = "block";
                    warning.style.background = "#F8E3DF";
                    warning.style.color = "#963F35";
                    warning.style.border = "1px solid #DDA99F";
                    warning.textContent =
                        "Bạn đã đạt giới hạn 1.000 ký tự. Vui lòng rút gọn nội dung.";

                } else if (length >= 900) {
                    warning.style.display = "block";
                    warning.style.background = "#F9F0D2";
                    warning.style.color = "#8A641F";
                    warning.style.border = "1px solid #E6D29B";
                    warning.textContent =
                        "Bình luận sắp đạt giới hạn 1.000 ký tự. Vui lòng cân nhắc rút gọn.";

                } else {
                    warning.style.display = "none";
                    warning.textContent = "";
                }
            }

            textarea.addEventListener("input", updateWarning);
            updateWarning();
        })();
        </script>
        """, unsafe_allow_javascript=True)
        st.caption("Tối đa 1.000 ký tự · Hỗ trợ tiếng Việt")

        button_col1, button_col2 = st.columns(2, gap="small")
        with button_col1:
            analyze_button = st.button("Phân tích  →", use_container_width=True)
        with button_col2:
            st.button("Xóa nội dung", use_container_width=True, on_click=clear_review)

        
if analyze_button:
    
    # Xóa kết quả cũ trước khi xử lý yêu cầu mới
    st.session_state.result = None

    # Loại bỏ khoảng trắng ở đầu và cuối
    review_content = review.strip()

    # Kiểm tra nội dung đầu vào
    if not review_content:
        st.warning(
            "Vui lòng nhập nội dung bình luận trước khi phân tích."
        )

    else:
        # Tạo mã cho lần phân tích
        st.session_state.batch_counter += 1
        st.session_state.review_counter += 1

        # Lưu thông tin bình luận
        st.session_state.result = {
            "batch_id": f"B{st.session_state.batch_counter:03d}",
            "review_id": f"RV{st.session_state.review_counter:04d}",
            "Review": review_content,
        }

    # Hiển thị thông tin bình luận nếu có kết quả
    if st.session_state.result:
        result = st.session_state.result

        st.markdown("---")
        st.markdown("""
        <div class="section-kicker">Submission details</div>
        <div class="section-title" style="font-size:1.55rem">
            Thông tin bình luận
        </div>
        """, unsafe_allow_html=True)

        st.success("Bình luận đã được tiếp nhận!")

        meta1, meta2 = st.columns(2, gap="small")

        with meta1:
            st.markdown(f"""
            <div class="metadata">
                <div class="metadata-label">Review ID</div>
                <div class="metadata-value">{result["review_id"]}</div>
            </div>
            """, unsafe_allow_html=True)

        with meta2:
            st.markdown(f"""
            <div class="metadata">
                <div class="metadata-label">Batch ID</div>
                <div class="metadata-value">{result["batch_id"]}</div>
            </div>
            """, unsafe_allow_html=True)

        safe_review = html.escape(result["Review"])

        st.markdown(f"""
        <div class="metadata-label">Original review</div>
        <div class="review-content">{safe_review}</div>
        """, unsafe_allow_html=True)

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

        if st.session_state.result:
            # Dữ liệu giả lập hiện tại; sẽ thay bằng mô hình AI khi tích hợp.
            aspect_results = [
                {"Aspect":"FOOD#QUALITY","Sentiment":1,"Confidence":0.95},
                {"Aspect":"FOOD#PRICES","Sentiment":3,"Confidence":0.82},
                {"Aspect":"FOOD#STYLE&OPTIONS","Sentiment":0,"Confidence":0.97},
                {"Aspect":"DRINKS#QUALITY","Sentiment":0,"Confidence":0.96},
                {"Aspect":"DRINKS#PRICES","Sentiment":0,"Confidence":0.98},
                {"Aspect":"DRINKS#STYLE&OPTIONS","Sentiment":0,"Confidence":0.94},
                {"Aspect":"RESTAURANT#GENERAL","Sentiment":0,"Confidence":0.96},
                {"Aspect":"RESTAURANT#PRICES","Sentiment":0,"Confidence":0.95},
                {"Aspect":"RESTAURANT#MISCELLANEOUS","Sentiment":0,"Confidence":0.93},
                {"Aspect":"SERVICE#GENERAL","Sentiment":2,"Confidence":0.91},
                {"Aspect":"AMBIENCE#GENERAL","Sentiment":0,"Confidence":0.96},
                {"Aspect":"LOCATION#GENERAL","Sentiment":0,"Confidence":0.97},
            ]
            sentiment_names = {
                0:"Không đề cập", 1:"Tích cực", 2:"Tiêu cực", 3:"Trung lập"
            }
            aspect_names = {
                "FOOD#QUALITY":"Chất lượng món ăn",
                "FOOD#PRICES":"Giá món ăn",
                "FOOD#STYLE&OPTIONS":"Phong cách chế biến món ăn",
                "DRINKS#QUALITY":"Chất lượng đồ uống",
                "DRINKS#PRICES":"Giá đồ uống",
                "DRINKS#STYLE&OPTIONS":"Phong cách chế biến đồ uống",
                "RESTAURANT#GENERAL":"Đánh giá chung",
                "RESTAURANT#PRICES":"Mức giá chung",
                "RESTAURANT#MISCELLANEOUS":"Các yếu tố khác",
                "SERVICE#GENERAL":"Chất lượng phục vụ",
                "AMBIENCE#GENERAL":"Không gian",
                "LOCATION#GENERAL":"Vị trí nhà hàng",
            }

            show_all = st.checkbox("Hiển thị tất cả 12 khía cạnh", value=False)
            displayed_results = (
                aspect_results if show_all
                else [item for item in aspect_results if item["Sentiment"] != 0]
            )
            
            display_data = []

            for item in displayed_results:
                row = {
                    "Khía cạnh": aspect_names[item["Aspect"]],
                    "Cảm xúc": sentiment_names[item["Sentiment"]],
                }

                if item["Sentiment"] == 0:
                    row["Độ tin cậy"] = "—"
                else:
                    confidence = item.get("Confidence")
                    row["Độ tin cậy"] = (
                        f"{float(confidence):.0%}"
                        if confidence is not None else "—"
                    )

                display_data.append(row)


            st.markdown(
                f'<div class="result-count">Showing {len(display_data)} / 12 aspects</div>',
                unsafe_allow_html=True,
            )

            # Chuyển dữ liệu thành DataFrame
            df = pd.DataFrame(display_data)

            # Bảng màu theo từng nhãn cảm xúc
            def sentiment_style(value):
                colors = {
                    "Tích cực": (
                        "background-color: #E4EEDC; color: #45633C;"
                    ),
                    "Tiêu cực": (
                        "background-color: #F3DFDA; color: #8B3D32;"
                    ),
                    "Trung lập": (
                        "background-color: #F8E9C9; color: #8A5A16;"
                    ),
                    "Không đề cập": (
                        "background-color: #EFE5D9; color: #806A58;"
                    ),
                }

                return (
                    colors.get(value, "")
                    + " font-weight: 600; text-align: center;"
                )


            # Định dạng Confidence
            def confidence_style(value):
                if value == "—":
                    return "color: #B6A493; text-align: center;"

                return (
                    "color: #542D2A; "
                    "font-weight: 600; "
                    "text-align: center;"
                )


            # Thiết lập phong cách tổng thể
            styled_df = (
                df.style
                .apply(
                    lambda col: col.map(sentiment_style),
                    subset=["Cảm xúc"]
                )
                .apply(
                    lambda col: col.map(confidence_style),
                    subset=["Độ tin cậy"]
                )
                .set_table_styles([
                    {
                        "selector": "th",
                        "props": [
                            ("background-color", "#EAD7C2"),
                            ("color", "#542D2A"),
                            ("font-weight", "700"),
                            ("border-bottom", "1px solid #D8B98F"),
                            ("padding", "12px 14px"),
                        ],
                    },
                    {
                        "selector": "td",
                        "props": [
                            ("color", "#5B4037"),
                            ("border-bottom", "1px solid #EFE2D4"),
                            ("padding", "10px 14px"),
                        ],
                    },
                    {
                        "selector": "tbody tr:nth-child(even)",
                        "props": [
                            ("background-color", "#FBF5EC"),
                        ],
                    },
                    {
                        "selector": "tbody tr:nth-child(odd)",
                        "props": [
                            ("background-color", "#F7EFE4"),
                        ],
                    },
                    {
                        "selector": "table",
                        "props": [
                            ("border-collapse", "separate"),
                            ("border-spacing", "0"),
                            ("border", "1px solid #E3D0BC"),
                        ],
                    },
                ])
            )

            # Hiển thị bảng
                        
            # Tạo các dòng dữ liệu HTML
            table_rows = ""

            for index, item in enumerate(display_data):
                aspect = html.escape(str(item["Khía cạnh"]))
                sentiment = html.escape(str(item["Cảm xúc"]))
                confidence = html.escape(str(item["Độ tin cậy"]))

                # Màu nhãn cảm xúc
                sentiment_classes = {
                    "Tích cực": "positive",
                    "Tiêu cực": "negative",
                    "Trung lập": "neutral",
                    "Không đề cập": "absent",
                }

                sentiment_class = sentiment_classes.get(
                    item["Cảm xúc"], "absent"
                )

                table_rows += f"""
                <tr>
                    <td class="aspect-cell">{aspect}</td>
                    <td class="sentiment-cell">
                        <span class="sentiment-badge {sentiment_class}">
                            {sentiment}
                        </span>
                    </td>
                    <td class="confidence-cell">{confidence}</td>
                </tr>
                """

            # Tạo bảng HTML
            table_html = f"""
            <style>
            .result-table-wrapper {{
                width: 100%;
                overflow-x: auto;
                border: 1px solid #E3D0BC;
                border-radius: 9px;
                background: #F8F0E5;
            }}

            .result-table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                table-layout: fixed;
                font-family: 'Lato', sans-serif;
                font-size: 13px;
                color: #542D2A;
            }}

            .result-table th {{
                background: #EAD7C2;
                color: #542D2A;
                font-weight: 700;
                text-align: left;
                padding: 13px 12px;
                border-bottom: 1px solid #D8B98F;
            }}

            .result-table td {{
                padding: 11px 12px;
                border-bottom: 1px solid #EDE0D1;
                background: #F8F0E5;
                vertical-align: middle;
                overflow-wrap: anywhere;
            }}

            .result-table tbody tr:nth-child(even) td {{
                background: #F3E8DA;
            }}

            .result-table tbody tr:last-child td {{
                border-bottom: none;
            }}

            .result-table th:nth-child(1),
            .result-table td:nth-child(1) {{
                width: 43%;
            }}

            .result-table th:nth-child(2),
            .result-table td:nth-child(2) {{
                width: 34%;
            }}

            .result-table th:nth-child(3),
            .result-table td:nth-child(3) {{
                width: 23%;
                text-align: center;
            }}

            .sentiment-badge {{
                display: inline-block;
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                white-space: nowrap;
            }}

            .positive {{
                background: #E3ECD9;
                color: #526B43;
            }}

            .negative {{
                background: #F0DDD6;
                color: #914C3D;
            }}

            .neutral {{
                background: #F5E6C8;
                color: #8A641F;
            }}

            .absent {{
                background: #EDE2D5;
                color: #806B59;
            }}

            .confidence-cell {{
                font-weight: 600;
                color: #542D2A;
            }}

            </style>

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
                        {table_rows}
                    </tbody>
                </table>
            </div>
            """

            st.html(table_html)


            st.caption("Confidence thể hiện độ tin cậy của kết quả dự đoán.")
        else:
            st.markdown("""
            <div style="min-height:280px;display:flex;flex-direction:column;
                align-items:center;justify-content:center;text-align:center;
                padding:30px 18px;border:1px dashed #D6B98C;background:rgba(255,250,242,.72);">
                <div style="color:#B69A68;font-family:'Cormorant Garamond',serif;
                    font-size:38px;margin-bottom:8px;">✦</div>
                <div style="color:#542D2A;font-family:'Cormorant Garamond',serif;
                    font-size:25px;margin-bottom:7px;">Your analysis awaits</div>
                <div style="max-width:290px;color:#82766C;font-family:'Lato',sans-serif;
                    font-size:12px;line-height:1.8;">
                    Nhập bình luận ở khung bên trái và chọn
                    <strong>Phân tích</strong> để xem kết quả tại đây.
                </div>
            </div>
            """, unsafe_allow_html=True)

# =========================================================
# 6. FOOTER
# =========================================================
st.markdown("""
<div class="page-footer">
    <span>Restaurant Review AI</span>
    <span>Aspect-Based Sentiment Analysis</span>
    <span>Designed with care · 2026</span>
</div>
""", unsafe_allow_html=True)
