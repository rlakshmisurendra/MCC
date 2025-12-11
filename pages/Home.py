# pages/Home.py
import streamlit as st

st.set_page_config(page_title="Home — Multilingual Chatbot", page_icon="💬", layout="wide")

# ---------------- Styles (matches your design PDF) ----------------
st.markdown(
    """
    <style>
    /* layout */
    .home-container { display:flex; gap:0; width:100%; height:100vh; box-sizing:border-box; }
    .main-area { flex: 1 1 auto; display:flex; align-items:center; justify-content:center; padding: 48px; background: #ffffff; }
    .banner-area { width: 240px; background: #f7f7f7; display:flex; align-items:center; justify-content:center; padding: 12px; box-sizing:border-box; border-left: 1px solid #e6e6e6; }
    .hero-card { width: 760px; max-width: calc(100% - 80px); border-radius: 14px; padding: 36px 28px; box-sizing: border-box; box-shadow: 0 8px 30px rgba(14,30,37,0.06); background: linear-gradient(180deg, #fff, #fbfbfb); position: relative; display:flex; align-items:center; justify-content:center; }
    .hero-content { width:100%; text-align:center; }
    .hero-title { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
    .hero-desc { color: #5b6368; margin-bottom: 18px; font-size: 16px; }
    .dept-vertical { position: absolute; right: -66px; top: 50%; transform: rotate(-90deg) translateY(-50%); transform-origin: center; font-weight: 600; color: #39424a; letter-spacing: 0.3px; }
    .cta { display:inline-block; padding: 10px 18px; border-radius: 10px; border: 1px solid #cfd6db; text-decoration: none; font-weight:600; background:#ffffff; box-shadow: 0 2px 8px rgba(14,30,37,0.05); }
    .cta:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(14,30,37,0.08); }
    .banner-img { width: 100%; height: auto; border-radius:6px; object-fit:cover; }
    @media (max-width: 900px) {
        .home-container { flex-direction: column; height:auto; }
        .banner-area { width:100%; order:-1; border-left:none; border-top:1px solid #e6e6e6; padding:18px; }
        .hero-card { width: auto; margin-top: 18px; }
        .dept-vertical { display:none; }
    }
    /* style for st buttons */
    .stButton>button { border-radius: 10px; padding: .45rem 1rem; font-weight:600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Content ----------------
banner_url = None
if hasattr(st, "secrets"):
    banner_url = st.secrets.get("BANNER_URL")

# Use banner_url if present, otherwise show a placeholder image.
display_banner = banner_url or "https://via.placeholder.com/220x420.png?text=Banner"

st.markdown('<div class="home-container">', unsafe_allow_html=True)

# Left / main area (hero)
st.markdown('<div class="main-area">', unsafe_allow_html=True)
st.markdown('<div class="hero-card">', unsafe_allow_html=True)
st.markdown('<div class="hero-content">', unsafe_allow_html=True)

# Title & description (matching your PDF wording)
st.markdown('<div class="hero-title">To use multilingual chatbot</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-desc">Click below to start</div>', unsafe_allow_html=True)

# Get started — navigates to root app where app.py's login lives
st.markdown(
    '<div style="text-align:center; margin-top:12px;">'
    '<a class="cta" href="/">Get started →</a>'
    '</div>',
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)  # .hero-content

# Vertical department label like in the PDF
st.markdown('<div class="dept-vertical">Department of CSE - AIML</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # .hero-card
st.markdown('</div>', unsafe_allow_html=True)  # .main-area

# Right-side banner area (no uploader)
st.markdown('<div class="banner-area">', unsafe_allow_html=True)
st.markdown(f'<img src="{display_banner}" class="banner-img" />', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # .banner-area

st.markdown('</div>', unsafe_allow_html=True)  # .home-container

# small footer hint
st.markdown(
    """
    <div style="text-align:center; margin-top:12px; color:#6b7280; font-size:13px;">
        Click <strong>Get started →</strong> to go to the login page.
    </div>
    """,
    unsafe_allow_html=True,
)
