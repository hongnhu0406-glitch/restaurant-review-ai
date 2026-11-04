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
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Lato:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
:root {--ivory:#F5F0E7;--burgundy:#552824;--burgundy-deep:#351B19;--wine:#87443B;--gold:#B18A4E;
 --gold-light:#D4BE96;--ink:#2F2925;--muted:#6F6258;--line:#E3D0BC;--sage:#68765D;--rose:#A65D50;--sand:#D4BE96;}
html, body, [class*="css"], .stApp {font-family:'Lato',sans-serif !important;color:var(--ink);}
.stApp, [data-testid="stAppViewContainer"] {
  background:radial-gradient(ellipse at 10% 0%, rgba(222,177,125,.24), transparent 36rem),
             radial-gradient(ellipse at 95% 55%, rgba(204,151,105,.12), transparent 32rem), #F8F1E8 !important;}
[data-testid="stHeader"] {background:transparent;}
#MainMenu, footer, .stDeployButton {visibility:hidden;}
.block-container {max-width:1400px !important;padding-top:.8rem !important;padding-bottom:2.4rem !important;}
/* ---------- Header ---------- */
.topline {display:flex;justify-content:space-between;border-top:2px solid var(--gold);
 border-bottom:1px solid var(--line);padding:11px 0;margin-bottom:1.6rem;color:var(--muted);
 font-size:11px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;}
.topline .brand-mark {color:var(--burgundy);letter-spacing:2.4px;}
.hero {text-align:center;padding:.2rem 0 1.4rem;}
.hero-title {color:var(--burgundy);font-family:'Cormorant Garamond',Georgia,serif;
 font-size:clamp(2.6rem,4.6vw,4rem);font-weight:600;letter-spacing:-1px;line-height:1;margin:0;}
.hero-title em {color:var(--gold);font-weight:500;}
.hero-subtitle {max-width:700px;margin:.9rem auto 0;color:var(--muted);font-size:15px;font-weight:500;line-height:1.8;}
.ornament {display:flex;align-items:center;justify-content:center;gap:12px;margin:1.2rem auto 0;color:var(--gold);}
.ornament:before,.ornament:after {content:"";width:60px;height:1px;background:var(--gold-light);}
/* ---------- Panels ---------- */
div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stVerticalBlockBorderWrapper"] > div {
  background:linear-gradient(135deg,#FFF9F1 0%,#FCF1E5 60%,#F8E9DA 100%) !important;
  border:1px solid #D9B9A4 !important;border-radius:16px !important;
  box-shadow:0 2px 6px rgba(84,45,42,.05),0 14px 30px rgba(84,45,42,.10) !important;overflow:hidden !important;}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {background:transparent !important;}
div[data-testid="stVerticalBlockBorderWrapper"] > div {padding:1.15rem 1.3rem !important;}
.panel-heading {display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap;
 border-bottom:1px solid #E2C9AE;padding-bottom:12px;margin-bottom:16px;}
.section-title {color:var(--burgundy);font-family:'Cormorant Garamond',Georgia,serif;font-size:1.85rem;font-weight:600;line-height:1.1;margin:0;}
.section-description {color:var(--muted);font-size:13px;font-weight:500;line-height:1.6;}
[data-testid="stWidgetLabel"] p {color:var(--burgundy) !important;font-size:13px !important;font-weight:700 !important;}
[data-testid="stAlert"] {border-radius:8px !important;}
/* ---------- Tabs ---------- */
button[data-baseweb="tab"] {font-family:'Lato',sans-serif !important;font-weight:700 !important;color:var(--muted) !important;}
button[data-baseweb="tab"][aria-selected="true"] {color:var(--burgundy) !important;}
div[data-baseweb="tab-highlight"] {background:var(--gold) !important;height:3px !important;}
/* ---------- Download ---------- */
.stDownloadButton>button {min-height:42px;border-radius:8px !important;border:1px solid var(--burgundy) !important;
 background:var(--burgundy) !important;color:#FFFDF8 !important;font-size:13px !important;font-weight:700 !important;}
.stDownloadButton>button:hover {background:var(--burgundy-deep) !important;border-color:var(--gold) !important;}
.stDownloadButton>button p {color:inherit !important;}
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
.tbl-wrap {width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:#FFFEFC;}
.tbl {width:100%;border-collapse:separate;border-spacing:0;font-size:13px;color:#4A342E;}
.tbl th {background:#EFDFCB;color:var(--burgundy);font-weight:800;text-align:left;padding:12px 14px;
 border-bottom:1px solid #D8B98F;white-space:nowrap;position:sticky;top:0;}
.tbl td {padding:11px 14px;border-bottom:1px solid #F0E4D6;background:#FFFEFC;vertical-align:middle;}
.tbl tbody tr:nth-child(even) td {background:#FBF5EC;}
.tbl tbody tr:hover td {background:#F6EAD9;}
.tbl tbody tr:last-child td {border-bottom:none;}
.tbl .num {text-align:center;font-weight:700;font-variant-numeric:tabular-nums;}
.tbl .pos-n {color:#526B43;} .tbl .neg-n {color:#914C3D;} .tbl .neu-n {color:#8A641F;} .tbl .dim {color:#B0A294;font-weight:500;}
.badge {display:inline-block;padding:4px 11px;border-radius:20px;font-size:12px;font-weight:700;white-space:nowrap;}
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
.rv-body {color:var(--ink);font-size:14px;line-height:1.75;font-weight:500;overflow-wrap:anywhere;}
.note {color:var(--muted);font-size:12px;font-weight:500;line-height:1.7;margin:10px 0 0;}
.page-footer {border-top:1px solid var(--gold-light);margin-top:2.5rem;padding-top:15px;display:flex;justify-content:space-between;
 gap:12px;color:var(--muted);font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;}
@media(max-width:760px) {.block-container {padding:1rem 1rem 2rem !important;} .insight {grid-template-columns:1fr;}
 .page-footer {flex-direction:column;}}
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


def heading(title, desc=""):
    d = f'<div class="section-description">{desc}</div>' if desc else ""
    st.markdown(f'<div class="panel-heading"><div class="section-title">{title}</div>{d}</div>',
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

# 2. HEADER
st.markdown("""
<div class="topline"><span class="brand-mark">Restaurant Review AI</span><span>Bảng thống kê</span></div>
<section class="hero">
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
    st.warning("Số liệu dashboard lệch với thống kê của backend, cần kiểm tra lại với backend: " + "; ".join(diff[:5]))

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

# 5. TỔNG QUAN
left, right = st.columns([1, 1.35], gap="large")
with left:
    with st.container(border=True):
        heading("Cơ cấu cảm xúc", "Tỷ trọng trên toàn bộ lượt đề cập")
        pie = go.Figure(go.Pie(labels=list(COLORS), values=[ov["pos"], ov["neg"], ov["neu"]], hole=.66, sort=False,
                               marker=dict(colors=list(COLORS.values()), line=dict(color="#FBF1E4", width=3)),
                               textinfo="percent", textfont=dict(size=13, color="#FFFFFF"),
                               hovertemplate="%{label}: %{value} lượt (%{percent})<extra></extra>"))
        pie.add_annotation(text=f"<b style='font-size:30px;color:#552824'>{ov['mentions']:,}</b><br>lượt đề cập",
                           showarrow=False, font=dict(size=12, color="#6F6258"))
        st.plotly_chart(style_fig(pie, 330), width="stretch")
with right:
    with st.container(border=True):
        heading("Nên phát huy và cần cải thiện", f"Chỉ xếp hạng khía cạnh có từ {int(min_m)} lượt đề cập")
        if top.empty:
            st.info(f"Chưa có khía cạnh nào đạt tối thiểu {int(min_m)} lượt đề cập để xếp hạng.")
        else:
            a, b = st.columns(2, gap="medium")
            a.markdown('<div class="rank-title good">▲ Nên phát huy</div>', unsafe_allow_html=True)
            b.markdown('<div class="rank-title bad">▼ Cần cải thiện</div>', unsafe_allow_html=True)
            for col, data, cls in ((a, top, ""), (b, low, "bad")):
                for _, r in data.iterrows():
                    col.markdown(
                        f'<div class="rank-card {cls}"><div class="rank-name">{html.escape(r["Khía cạnh"])}</div>'
                        f'<div class="rank-meta"><div class="rank-bar"><span style="width:{width(r["% Tích cực"])}%"></span></div>'
                        f'<span>{r["% Tích cực"]}% tích cực</span><span>{int(r["Lượt đề cập"])} lượt</span></div></div>',
                        unsafe_allow_html=True)

# 6. BIỂU ĐỒ 12 KHÍA CẠNH
st.write("")
with st.container(border=True):
    heading("Cảm xúc theo từng khía cạnh", "Chuyển tab để xem số lượng hoặc tỷ lệ phần trăm")
    order = shown.sort_values("Lượt đề cập")
    tab_a, tab_b = st.tabs(["Số lượt đề cập", "Tỷ lệ phần trăm"])
    with tab_a:
        f1 = go.Figure([go.Bar(name=k, y=order["Khía cạnh"], x=order[k], orientation="h", marker_color=v,
                               hovertemplate="%{y}<br>" + k + ": %{x} lượt<extra></extra>") for k, v in COLORS.items()])
        f1.update_layout(barmode="stack", xaxis_title="Số lượt đề cập", bargap=.35)
        st.plotly_chart(style_fig(f1, max(340, 40 * len(order) + 100)), width="stretch")
    with tab_b:
        ment = order[order["Lượt đề cập"] > 0]
        f2 = go.Figure([go.Bar(name=k, y=ment["Khía cạnh"], x=ment[f"% {k}"], orientation="h", marker_color=v,
                               text=ment[f"% {k}"].round(0).astype(int).astype(str) + "%", textposition="inside",
                               textfont=dict(color="#FFFFFF" if k != "Trung lập" else "#5B4A2A"),
                               hovertemplate="%{y}<br>" + k + ": %{x:.1f}%<extra></extra>")
                        for k, v in COLORS.items()])
        f2.update_layout(barmode="stack", xaxis=dict(range=[0, 100], title="% trên số lượt đề cập"), bargap=.35)
        st.plotly_chart(style_fig(f2, max(340, 40 * len(ment) + 100)), width="stretch")
    st.markdown('<div class="note">Tỷ lệ cảm xúc = số lượt cảm xúc đó ÷ số lượt đề cập của khía cạnh. '
                'Nhãn “Không đề cập” không tính vào tỷ lệ.</div>', unsafe_allow_html=True)

# 7. BẢNG THỐNG KÊ
st.write("")
with st.container(border=True):
    heading("Bảng thống kê chi tiết", "Thanh màu thể hiện tỷ lệ tích cực, tiêu cực, trung lập")
    rows = ""
    for _, r in shown.sort_values("Lượt đề cập", ascending=False).iterrows():
        mix = ('<span class="dim">—</span>' if r["Lượt đề cập"] == 0 else
               '<div class="mix-wrap"><div class="mix">'
               f'<i class="p" style="width:{width(r["% Tích cực"])}%"></i>'
               f'<i class="n" style="width:{width(r["% Tiêu cực"])}%"></i>'
               f'<i class="u" style="width:{width(r["% Trung lập"])}%"></i></div>'
               f'<span>{pct(r["% Tích cực"])}</span></div>')
        rows += (f'<tr><td><b>{html.escape(r["Khía cạnh"])}</b></td>'
                 f'<td class="num pos-n">{int(r["Tích cực"])}</td><td class="num neg-n">{int(r["Tiêu cực"])}</td>'
                 f'<td class="num neu-n">{int(r["Trung lập"])}</td><td class="num">{int(r["Lượt đề cập"])}</td>'
                 f'<td class="num dim">{int(r["Không đề cập"])}</td><td>{mix}</td>'
                 f'<td class="num">{pct(r["% Tiêu cực"])}</td><td class="num">{pct(r["% Trung lập"])}</td></tr>')
    st.html('<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Khía cạnh</th><th>Tích cực</th><th>Tiêu cực</th>'
            '<th>Trung lập</th><th>Lượt đề cập</th><th>Không đề cập</th><th>Tỷ lệ tích cực</th><th>% Tiêu cực</th>'
            f'<th>% Trung lập</th></tr></thead><tbody>{rows}</tbody></table></div>')
    st.write("")
    d1, d2, _ = st.columns([1, 1, 2], gap="small")
    d1.download_button("Tải bảng thống kê (CSV)", shown.reset_index(drop=True).to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"thong_ke_{batch}.csv", mime="text/csv", use_container_width=True)
    try:
        d2.download_button("Tải kết quả chi tiết (CSV)", load_export(batch),
                           file_name=f"{batch}_results.csv", mime="text/csv", use_container_width=True)
    except BackendError as e:
        d2.caption(f"Không xuất được kết quả chi tiết: {e}")

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