import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard_stats import (ASPECT_NAMES, SENTIMENT_NAMES, aspect_table, overall,
                             strengths_weaknesses, validate)
from adapter import (API_BASE_URL, BackendError, compare_with_backend, completed_batches, fetch_batches,
                     fetch_dashboard, fetch_export, parse_dashboard, status_counts)

st.set_page_config(page_title="Restaurant Review AI - Dashboard", page_icon="🍽️", layout="wide",
                   initial_sidebar_state="collapsed")
# 1. DESIGN SYSTEM
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Lato:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root {--ivory:#F5F0E7;--paper:#FFFEFC;--burgundy:#552824;--burgundy-deep:#351B19;--wine:#87443B;--gold:#B18A4E;
 --gold-light:#D4BE96;--ink:#2F2925;--muted:#6F6258;--line:#DCCFBD;--sage:#68765D;--rose:#A65D50;--sand:#D4BE96;}
html, body, [class*="css"], .stApp {font-family:'Lato',sans-serif !important;color:var(--ink);font-weight:400;}
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
  background-attachment:scroll !important;}
[data-testid="stHeader"] {background:transparent;}
#MainMenu, footer, .stDeployButton {visibility:hidden;}
.block-container {max-width:1500px !important;padding-top:.7rem !important;padding-bottom:2.4rem !important;position:relative;}
/* ---------- Header ---------- */
.topline {display:flex;justify-content:space-between;gap:1rem;border-top:1px solid var(--gold);
 border-bottom:1px solid var(--line);padding:12px 0;margin-bottom:2.2rem;color:var(--muted);
 font-size:10px;font-weight:700;letter-spacing:2.2px;text-transform:uppercase;}
.topline .brand-mark {color:var(--burgundy);letter-spacing:3px;}
.hero {display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;
 box-sizing:border-box;padding:.7rem 0 1.45rem;text-align:center !important;}
.eyebrow {color:var(--gold);font-size:10px;font-weight:900;letter-spacing:4px;text-transform:uppercase;margin-bottom:1rem;}
.hero-title {color:var(--burgundy) !important;font-family:'Cormorant Garamond',Georgia,serif !important;
 font-size:clamp(3rem,5.2vw,4.7rem) !important;font-weight:600 !important;letter-spacing:-1.5px !important;
 line-height:.94 !important;margin:0 !important;}
.hero-title em {color:var(--gold);font-weight:700;}
.hero-subtitle {display:block;width:min(780px,100%);max-width:780px;margin:1.1rem auto 0 !important;padding:0 1rem;
 box-sizing:border-box;color:var(--ink);font-size:15px;font-weight:500;line-height:1.9;text-align:center !important;}
.ornament {display:flex;align-items:center;justify-content:center;gap:12px;margin:1.6rem auto 0;color:var(--gold);}
.ornament:before,.ornament:after {content:"";width:52px;height:1px;background:var(--gold-light);}
/* ---------- Panels (giống trang chính) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stVerticalBlockBorderWrapper"] > div {
  background:linear-gradient(135deg,#FFF8EF 0%,#FBEFE2 55%,#F7E6D7 100%) !important;background-color:#F9EEE2 !important;
  border:1.6px solid #98564B !important;border-radius:19px !important;
  box-shadow:0 5px 12px rgba(84,45,42,.06),0 18px 32px rgba(84,45,42,.15) !important;overflow:hidden !important;}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {background:transparent !important;}
div[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1.05rem 1.1rem !important;}
.panel-heading {border-bottom:1px solid #D9BFA0;padding-bottom:18px;margin-bottom:20px;}
.section-kicker {color:var(--gold);font-size:9px;font-weight:900;letter-spacing:2.8px;text-transform:uppercase;margin-bottom:5px;}
.section-title {color:var(--burgundy);font-family:'Cormorant Garamond',Georgia,serif;font-size:2.15rem;font-weight:600;line-height:1.1;margin:0 0 .35rem;}
.section-description {color:var(--muted);font-size:13px;font-weight:500;line-height:1.75;}
[data-testid="stWidgetLabel"] p {color:var(--burgundy) !important;font-family:'Lato',sans-serif !important;font-size:13px !important;font-weight:800 !important;}
[data-testid="stAlert"] {border-radius:2px !important;font-family:'Lato',sans-serif !important;}
[data-testid="stCaptionContainer"] p {color:var(--muted) !important;font-family:'Lato',sans-serif !important;font-size:12px !important;font-weight:600 !important;}
/* ---------- Font cho ô chọn / ô số / checkbox / danh sách thả xuống ---------- */
.stSelectbox *, .stNumberInput *, .stCheckbox *, .stMultiSelect *, [data-baseweb="popover"] *, [data-baseweb="menu"] * {
 font-family:'Lato',sans-serif !important;}
.stSelectbox [data-baseweb="select"] div, .stNumberInput input, .stMultiSelect [data-baseweb="select"] div {
 font-size:14px !important;font-weight:500 !important;}
.stCheckbox label p {font-size:13px !important;font-weight:800 !important;}
/* ---------- Buttons (giống trang chính) ---------- */
.stButton>button, .stDownloadButton>button {min-height:44px;border-radius:2px !important;border:1px solid var(--burgundy) !important;
 background:var(--burgundy) !important;color:#FFFDF8 !important;font-family:'Lato',sans-serif !important;font-size:12px !important;
 font-weight:900 !important;letter-spacing:1.5px !important;text-transform:uppercase;transition:all .2s ease;}
.stButton>button:hover, .stDownloadButton>button:hover {background:var(--burgundy-deep) !important;border-color:var(--gold) !important;transform:translateY(-1px);}
.stButton>button p, .stButton>button span, .stDownloadButton>button p {color:inherit !important;font-family:'Lato',sans-serif !important;}
/* ---------- Thanh chuyển dọc (st.radio) ---------- */
.stRadio [role="radiogroup"] {gap:4px;}
.stRadio label {padding:10px 12px;border-radius:6px;border-left:3px solid transparent;cursor:pointer;width:100%;}
.stRadio label > div:first-child {display:none;}
.stRadio label p {font-family:'Lato',sans-serif !important;font-size:14px !important;font-weight:700 !important;color:var(--muted) !important;}
.stRadio label:has(input:checked) {background:#F2EBDD;border-left-color:var(--gold);}
.stRadio label:has(input:checked) p {color:var(--burgundy) !important;}
.stRadio label:hover {background:#F6EAD9;}
[data-testid="stButtonGroup"] button p {font-family:'Lato',sans-serif !important;font-size:13px !important;font-weight:700 !important;}
/* ---------- Tabs ---------- */
button[data-baseweb="tab"] {font-family:'Lato',sans-serif !important;font-weight:700 !important;color:var(--muted) !important;}
button[data-baseweb="tab"][aria-selected="true"] {color:var(--burgundy) !important;}
div[data-baseweb="tab-highlight"] {background:var(--gold) !important;height:3px !important;}
/* ---------- Insight band ---------- */
.insight {display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:4px 0 18px;}
.insight-item {display:flex;gap:14px;align-items:center;background:#FFFEFC;border:1px solid var(--line);
 border-radius:14px;padding:14px 18px;}
.insight-icon {flex:0 0 42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;
 font-size:19px;font-weight:700;}
.insight-item.good .insight-icon {background:#E3ECD9;color:#526B43;}
.insight-item.bad .insight-icon {background:#F0DDD6;color:#914C3D;}
.insight-text {font-size:13px;color:var(--muted);line-height:1.5;}
.insight-text b {display:block;color:var(--burgundy);font-family:'Cormorant Garamond',serif;font-size:1.35rem;font-weight:700;}
/* ---------- KPI ---------- */
.kpi {background:#FFFEFC;border:1px solid var(--line);border-top:3px solid var(--gold);border-radius:12px;
 padding:16px 18px;height:100%;}
.kpi-label {color:var(--muted);font-size:12px;font-weight:700;margin-bottom:6px;}
.kpi-value {color:var(--burgundy);font-family:'Cormorant Garamond',Georgia,serif;font-size:2.6rem;font-weight:700;line-height:1;}
.kpi-note {color:#8A7D72;font-size:12px;font-weight:500;margin-top:8px;line-height:1.4;}
/* ---------- Rank list ---------- */
.rank-title {font-size:13px;font-weight:900;margin:0 0 10px;display:flex;align-items:center;gap:8px;}
.rank-title.good {color:var(--sage);} .rank-title.bad {color:var(--rose);}
.rank-card {background:#FFFEFC;border:1px solid var(--line);border-left:4px solid var(--sage);border-radius:10px;
 padding:11px 14px;margin-bottom:9px;}
.rank-card.bad {border-left-color:var(--rose);}
.rank-name {color:var(--burgundy);font-weight:800;font-size:14px;}
.rank-meta {display:flex;align-items:center;gap:10px;margin-top:7px;font-size:12px;color:var(--muted);font-weight:600;}
.rank-bar {flex:1;height:6px;background:#EADFCF;border-radius:4px;overflow:hidden;}
.rank-bar span {display:block;height:100%;background:var(--sage);} .rank-card.bad .rank-bar span {background:var(--rose);}
/* ---------- Tables ---------- */
.tbl-wrap {width:100%;overflow-x:auto;border:1px solid #E3D0BC;border-radius:9px;background:#FFFEFC;}
.tbl {width:100%;border-collapse:separate;border-spacing:0;font-family:'Lato',sans-serif;font-size:13px;color:#4A342E;}
.tbl th {background:#EAD7C2;color:var(--burgundy);font-weight:800;text-align:left;padding:12px 14px;
 border-bottom:1px solid #D8B98F;white-space:nowrap;position:sticky;top:0;}
.tbl td {padding:11px 14px;border-bottom:1px solid #F0E4D6;background:#FFFEFC;vertical-align:middle;}
.tbl tbody tr:nth-child(even) td {background:#FBF5EC;}
.tbl tbody tr:hover td {background:#F6EAD9;}
.tbl tbody tr:last-child td {border-bottom:none;}
.tbl .num {text-align:center;font-weight:700;font-variant-numeric:tabular-nums;}
.tbl .pos-n {color:#526B43;} .tbl .neg-n {color:#914C3D;} .tbl .neu-n {color:#8A641F;} .tbl .dim {color:#B0A294;font-weight:500;}
.badge {display:inline-block;padding:5px 10px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap;}
.badge.pos {background:#E3ECD9;color:#526B43;} .badge.neg {background:#F0DDD6;color:#914C3D;}
.badge.neu {background:#F5E6C8;color:#8A641F;}
.mix {display:flex;width:150px;height:9px;border-radius:5px;overflow:hidden;background:#EADFCF;}
.mix i {display:block;height:100%;}
.mix .p {background:#68765D;} .mix .n {background:#A65D50;} .mix .u {background:#D4BE96;}
.mix-wrap {display:flex;align-items:center;gap:10px;} .mix-wrap span {font-weight:700;min-width:44px;}
/* ---------- Review cards ---------- */
.rv {background:#FFFEFC;border:1px solid var(--line);border-left:4px solid var(--sage);border-radius:10px;
 padding:13px 16px;margin-bottom:10px;}
.rv.neg {border-left-color:var(--rose);} .rv.neu {border-left-color:var(--sand);}
.rv-head {display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:7px;}
.rv-id {color:var(--muted);font-size:12px;font-weight:700;}
.rv-conf {color:var(--muted);font-size:12px;font-weight:600;margin-left:8px;}
.rv-body {color:var(--ink);font-size:14px;line-height:1.9;font-weight:500;overflow-wrap:anywhere;}
.note {color:var(--muted);font-size:12px;font-weight:600;line-height:1.7;margin:10px 0 0;}
.page-footer {border-top:1px solid var(--gold-light);margin-top:2.5rem;padding-top:15px;display:flex;justify-content:space-between;
 gap:12px;color:var(--muted);font-size:9px;font-weight:700;letter-spacing:1.7px;text-transform:uppercase;}
@media(max-width:760px) {.block-container {padding:1rem 1rem 2rem !important;} .hero {padding:.5rem 0 1.5rem;}
 .hero-title {font-size:3.2rem !important;} .insight {grid-template-columns:1fr;} .page-footer {flex-direction:column;}}
</style>
""", unsafe_allow_html=True)

COLORS = {"Tích cực": "#68765D", "Tiêu cực": "#A65D50", "Trung lập": "#D4BE96"}
BADGE = {"Tích cực": "pos", "Tiêu cực": "neg", "Trung lập": "neu"}


def style_fig(fig, height):
    fig.update_layout(height=height, margin=dict(t=30, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Lato, sans-serif", color="#2F2925", size=12),
                      legend=dict(orientation="h", y=1.08, x=0), hoverlabel=dict(font_family="Lato"))
    fig.update_xaxes(gridcolor="#EAD9C6", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True)
    return fig


KICKERS = {
    "Biểu đồ cảm xúc": "Sentiment charts",
    "Chọn lần phân tích": "Data source",
    "Cơ cấu cảm xúc": "Overall sentiment",
    "Cảm xúc theo từng khía cạnh": "Aspect-based sentiment",
    "Bảng thống kê chi tiết": "Statistics",
    "Xem bình luận theo khía cạnh": "Reviews",
}


def heading(title, desc=""):
    k = f'<div class="section-kicker">{KICKERS[title]}</div>' if title in KICKERS else ""
    d = f'<div class="section-description">{desc}</div>' if desc else ""
    st.markdown(f'<div class="panel-heading">{k}<div class="section-title">{title}</div>{d}</div>',
                unsafe_allow_html=True)


def kpi(col, label, value, note=""):
    col.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>'
                 f'<div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)


def pct(v):
    return "—" if pd.isna(v) else f"{v:.1f}%"


def width(v):
    return 0 if pd.isna(v) else max(0, min(100, float(v)))


@st.cache_data(ttl=30, show_spinner=False)
def load_batches():
    return fetch_batches()


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard(batch_id):
    return fetch_dashboard(batch_id)


@st.cache_data(ttl=300, show_spinner=False)
def load_export(batch_id):
    return fetch_export(batch_id)


def reload_data():
    st.cache_data.clear()
    st.rerun()


def stats_table_html(data, compact=False):
    """Bảng thống kê khía cạnh. compact=True: bản gọn để đặt trong tab."""
    rows = ""
    for _, r in data.sort_values("Lượt đề cập", ascending=False).iterrows():
        mix = ('<span class="dim">—</span>' if r["Lượt đề cập"] == 0 else
               '<div class="mix-wrap"><div class="mix">'
               f'<i class="p" style="width:{width(r["% Tích cực"])}%"></i>'
               f'<i class="n" style="width:{width(r["% Tiêu cực"])}%"></i>'
               f'<i class="u" style="width:{width(r["% Trung lập"])}%"></i></div>'
               f'<span>{pct(r["% Tích cực"])}</span></div>')
        rows += (f'<tr><td><b>{html.escape(r["Khía cạnh"])}</b></td>'
                 f'<td class="num pos-n">{int(r["Tích cực"])}</td><td class="num neg-n">{int(r["Tiêu cực"])}</td>'
                 f'<td class="num neu-n">{int(r["Trung lập"])}</td><td class="num">{int(r["Lượt đề cập"])}</td>')
        if not compact:
            rows += f'<td class="num dim">{int(r["Không đề cập"])}</td>'
        rows += f'<td>{mix}</td>'
        if not compact:
            rows += f'<td class="num">{pct(r["% Tiêu cực"])}</td><td class="num">{pct(r["% Trung lập"])}</td>'
        rows += '</tr>'
    head = ('<th>Khía cạnh</th><th>Tích cực</th><th>Tiêu cực</th><th>Trung lập</th><th>Lượt đề cập</th>'
            + ('' if compact else '<th>Không đề cập</th>') + '<th>Tỷ lệ tích cực</th>'
            + ('' if compact else '<th>% Tiêu cực</th><th>% Trung lập</th>'))
    return f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'

# 2. HEADER
st.markdown("""
<div class="topline"><span class="brand-mark">Restaurant Review AI</span><span>Bảng thống kê</span></div>
<section class="hero">
  <div class="eyebrow">Understand every dining experience</div>
  <h1 class="hero-title">Khách hàng nói gì về <em>nhà hàng</em></h1>
  <p class="hero-subtitle">Cảm xúc của khách theo từng khía cạnh: món ăn, giá cả, phục vụ, không gian.
  Từ đó biết nên phát huy điều gì và cải thiện điều gì.</p>
  <div class="ornament">✦</div>
</section>
""", unsafe_allow_html=True)
# 3. DỮ LIỆU VÀ BỘ LỌC
with st.container(border=True):
    heading("Chọn lần phân tích", "Dữ liệu lấy trực tiếp từ backend. Chỉ hiển thị các batch đã hoàn tất (Completed).")
    try:
        with st.spinner("Đang tải danh sách batch từ backend..."):
            all_batches = load_batches()
    except BackendError as e:
        st.error(str(e))
        st.caption(f"Địa chỉ API đang dùng: {API_BASE_URL}")
        if st.button("Thử kết nối lại"):
            reload_data()
        st.stop()

    bt = completed_batches(all_batches)
    counts = status_counts(all_batches)
    if bt.empty:
        st.warning("Chưa có batch nào ở trạng thái Completed. Hãy phân tích một bình luận hoặc tải file CSV ở trang chính.")
        if st.button("Tải lại danh sách"):
            reload_data()
        st.stop()

    batches = list(bt["batch_id"])
    labels = {r.batch_id: f"{r.batch_id} · {r.created_at} · {r.total_reviews} bình luận" for r in bt.itertuples()}
    f1c, f2c, f3c, f4c = st.columns([2, 1.2, 1.2, .8], gap="large")
    batch = f1c.selectbox("Lần phân tích (batch)", batches, format_func=lambda b: labels.get(b, b))
    min_m = f2c.number_input("Số lượt đề cập tối thiểu để xếp hạng", 1, 100, 10)
    show_empty = f3c.checkbox("Hiện cả khía cạnh chưa được đề cập", value=False)
    f4c.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if f4c.button("Tải lại dữ liệu", use_container_width=True):
        reload_data()

    note = []
    if counts.get("Processing"):
        note.append(f"{counts['Processing']} batch đang xử lý")
    if counts.get("Failed"):
        note.append(f"{counts['Failed']} batch thất bại")
    if note:
        st.caption(" · ".join(note) + " (không đưa vào thống kê).")

    try:
        with st.spinner("Đang tải thống kê của batch..."):
            binfo, raw, backend_stats = parse_dashboard(load_dashboard(batch))
    except BackendError as e:
        st.error(str(e))
        st.stop()

    errs = validate(raw)
    if errs:  # dữ liệu sai định dạng: không hiển thị số liệu hay biểu đồ
        st.error("Dữ liệu không hợp lệ, không thể hiển thị Dashboard:")
        for e in errs:
            st.write("- " + e)
        st.stop()
    raw["Sentiment"] = pd.to_numeric(raw["Sentiment"]).astype(int)

df = raw[raw["batch_id"] == batch]
if df.empty:  # batch có trong danh sách nhưng file kết quả chưa có
    have = ", ".join(dict.fromkeys(raw["batch_id"]))
    st.warning(f"Chưa có dữ liệu kết quả của batch {batch}. File kết quả hiện chỉ chứa: {have}.")
    st.stop()

tbl, ov = aspect_table(df), overall(df)
shown = tbl if show_empty else tbl[tbl["Lượt đề cập"] > 0]
diff = compare_with_backend(tbl, ov, backend_stats)
if diff:
    st.warning("Số liệu dashboard lệch với thống kê của backend, cần kiểm tra lại: " + "; ".join(diff[:5]))

top, low = strengths_weaknesses(tbl, int(min_m))

# 4. ĐIỂM NỔI BẬT + KPI
st.write("")
if not top.empty and not low.empty:
    t, l = top.iloc[0], low.iloc[0]
    st.markdown(f"""
    <div class="insight">
      <div class="insight-item good"><div class="insight-icon">↑</div>
        <div class="insight-text">Được khen nhiều nhất<b>{html.escape(t["Khía cạnh"])}</b>{t["% Tích cực"]}% tích cực trên {int(t["Lượt đề cập"])} lượt</div></div>
      <div class="insight-item bad"><div class="insight-icon">↓</div>
        <div class="insight-text">Cần chú ý nhất<b>{html.escape(l["Khía cạnh"])}</b>chỉ {l["% Tích cực"]}% tích cực trên {int(l["Lượt đề cập"])} lượt</div></div>
    </div>""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4, gap="medium")
kpi(k1, "Tổng số bình luận", f"{ov['reviews']:,}", "Số review_id khác nhau")
kpi(k2, "Lượt đề cập khía cạnh", f"{ov['mentions']:,}", "Một bình luận có thể nhắc nhiều khía cạnh")
kpi(k3, "Tỷ lệ tích cực chung", f"{ov['pos_rate']}%" if ov["pos_rate"] is not None else "—", "Không tính “Không đề cập”")
kpi(k4, "Khía cạnh được nhắc tới", f"{int((tbl['Lượt đề cập'] > 0).sum())}/12", "Trên tổng 12 khía cạnh")
st.write("")

# 5. BIỂU ĐỒ CẢM XÚC (thanh chuyển dọc bên trái)
order = shown.sort_values("Lượt đề cập")
ment = order[order["Lượt đề cập"] > 0]
NOTE = ('<div class="note">Tỷ lệ cảm xúc = số lượt cảm xúc đó ÷ số lượt đề cập của khía cạnh. '
        'Nhãn “Không đề cập” không tính vào tỷ lệ.</div>')


def fig_pie():
    fig = go.Figure(go.Pie(labels=list(COLORS), values=[ov["pos"], ov["neg"], ov["neu"]], hole=.66, sort=False,
                           marker=dict(colors=list(COLORS.values()), line=dict(color="#FBF1E4", width=3)),
                           textinfo="percent", textfont=dict(size=13, color="#FFFFFF"),
                           outsidetextfont=dict(size=13, color="#552824"),
                           hovertemplate="%{label}: %{value} lượt (%{percent})<extra></extra>"))
    fig.add_annotation(text=f"<b style='font-size:30px;color:#552824'>{ov['mentions']:,}</b><br>lượt đề cập",
                       showarrow=False, font=dict(size=12, color="#6F6258"))
    return style_fig(fig, 360).update_layout(margin=dict(t=70, b=40, l=10, r=10),
                                             legend=dict(orientation="h", y=1.14, x=.5, xanchor="center"))


def nice_step(mx):
    """Bước chia trục số nguyên cho đẹp: 1, 2, 5, 10, 20, 50..."""
    raw = max(1, -(-int(mx) // 6))
    for step in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000):
        if step >= raw:
            return step
    return raw


def fig_counts():
    fig = go.Figure([go.Bar(name=k, y=order["Khía cạnh"], x=order[k], orientation="h", marker_color=v,
                            hovertemplate="%{y}<br>" + k + ": %{x} lượt<extra></extra>") for k, v in COLORS.items()])
    mx = int(order[list(COLORS)].sum(axis=1).max()) if len(order) else 1
    fig.update_layout(barmode="stack", xaxis_title="Số lượt đề cập", bargap=.35)
    fig = style_fig(fig, max(340, 40 * len(order) + 100))
    return fig.update_xaxes(dtick=nice_step(mx), tickformat="d", rangemode="tozero")


def fig_percent():
    fig = go.Figure([go.Bar(name=k, y=ment["Khía cạnh"], x=ment[f"% {k}"], orientation="h", marker_color=v,
                            text=ment[f"% {k}"].round(0).astype(int).astype(str) + "%", textposition="inside",
                            textfont=dict(color="#FFFFFF" if k != "Trung lập" else "#5B4A2A"),
                            hovertemplate="%{y}<br>" + k + ": %{x:.1f}%<extra></extra>")
                     for k, v in COLORS.items()])
    fig.update_layout(barmode="stack", xaxis=dict(range=[0, 100], title="% trên số lượt đề cập"), bargap=.35)
    fig = style_fig(fig, max(340, 40 * len(ment) + 100))
    fig.update_layout(margin=dict(t=30, b=10, l=10, r=30))
    ticks = [0, 20, 40, 60, 80, 100]
    return fig.update_xaxes(tickmode="array", tickvals=ticks, ticktext=[f"{t}%" for t in ticks])


def view_overview():  # hai biểu đồ cạnh nhau
    c1, c2 = st.columns([1, 1.3], gap="medium")
    c1.plotly_chart(fig_pie(), width="stretch")
    with c2:
        _, sw = st.columns([.6, 1.4])
        mode = sw.segmented_control("Kiểu hiển thị", ["Số lượt đề cập", "Phần trăm"], default="Số lượt đề cập",
                                    key="overview_bar_mode", label_visibility="collapsed") or "Số lượt đề cập"
        st.plotly_chart(fig_counts() if mode == "Số lượt đề cập" else fig_percent(), width="stretch")

def view_pie():
    st.plotly_chart(fig_pie(), width="stretch")


def view_counts():
    st.plotly_chart(fig_counts(), width="stretch")


def view_percent():
    st.plotly_chart(fig_percent(), width="stretch")
    st.markdown(NOTE, unsafe_allow_html=True)


def view_table():
    st.html(stats_table_html(shown, compact=True))


# Muốn thêm biểu đồ mới: viết một hàm view_xxx() rồi thêm một dòng vào đây.
VIEWS = {
    "Tổng quan": view_overview,
    "Bảng thống kê chi tiết": view_table,
}


st.write("")
with st.container(border=True):
    heading("Biểu đồ cảm xúc", "Chọn kiểu hiển thị ở danh sách bên trái")

    nav, divider, body = st.columns([1, 0.035, 5], gap="medium")

    choice = nav.radio(
        "Kiểu hiển thị",
        list(VIEWS),
        label_visibility="collapsed"
    )

    with divider:
        st.markdown("""
        <div style="
            width: 1px;
            height: 340px;
            margin: 8px auto;
            background: linear-gradient(
                to bottom,
                transparent,
                #B18A4E 15%,
                #DCCFBD 50%,
                #B18A4E 85%,
                transparent
            );
        "></div>
        """, unsafe_allow_html=True)

    with body:
        VIEWS[choice]()
# 8. XEM BÌNH LUẬN
st.write("")
with st.container(border=True):
    heading("Xem bình luận theo khía cạnh", "Lọc theo khía cạnh và cảm xúc")
    x1, x2 = st.columns(2, gap="large")
    asp = x1.selectbox("Khía cạnh", list(ASPECT_NAMES), format_func=lambda k: ASPECT_NAMES[k])
    sel = x2.multiselect("Cảm xúc", ["Tích cực", "Tiêu cực", "Trung lập"], default=["Tiêu cực"])
    codes = [k for k, v in SENTIMENT_NAMES.items() if v in sel]
    rv = df[(df["Aspect"] == asp) & (df["Sentiment"].isin(codes))]
    if rv.empty:
        st.info("Không có bình luận nào khớp bộ lọc này.")
    else:
        cards = ""
        for r in rv.head(50).itertuples():
            name = SENTIMENT_NAMES[r.Sentiment]
            conf = f"{float(r.Confidence):.0%}" if hasattr(r, "Confidence") and pd.notna(r.Confidence) else "—"
            cards += (f'<div class="rv {BADGE[name]}"><div class="rv-head"><span class="rv-id">{html.escape(str(r.review_id))}</span>'
                      f'<span><span class="badge {BADGE[name]}">{name}</span><span class="rv-conf">Tin cậy {conf}</span></span></div>'
                      f'<div class="rv-body">{html.escape(str(r.Review))}</div></div>')
        st.html(cards)
        st.caption(f"Hiển thị {min(50, len(rv))} / {len(rv)} bình luận.")

st.markdown("""
<div class="page-footer"><span>Restaurant Review AI</span><span>Aspect-Based Sentiment Analysis</span>
<span>Designed with care · 2026</span></div>
""", unsafe_allow_html=True)