# pages/Home.py
import streamlit as st

st.set_page_config(page_title="Home — Multilingual Chatbot", page_icon="💬", layout="wide")

# ---------------- Styles (matches the sketch in design.pdf page 1) ----------------
st.markdown(
    """
    <style>
    /* reset */
    .home-container { display:flex; gap:0; width:100%; height:100vh; box-sizing:border-box; }

    /* Left main area: center hero card */
    .main-area {
        flex: 1 1 auto;
        display:flex;
        align-items:center;
        justify-content:center;
        padding: 48px;
        background: #ffffff;
    }

    /* Right banner area (vertical strip) */
    .banner-area {
        width: 220px;               /* adjust as needed to match sketch */
        background: #f7f7f7;
        display:flex;
        align-items:center;
        justify-content:center;
        padding: 12px;
        box-sizing:border-box;
        border-left: 1px solid #e6e6e6;
    }

    /* The hero card (center) with rounded border like the sketch */
    .hero-card {
        width: 760px;
        max-width: calc(100% - 80px);
        border-radius: 14px;
        padding: 36px 28px;
        box-sizing: border-box;
        box-shadow: 0 8px 30px rgba(14,30,37,0.06);
        background: linear-gradient(180deg, #fff, #fbfbfb);
        position: relative;
        display:flex;
        align-items:center;
        justify-content:center;
    }

    /* Inner text area (vertical layout like sketch) */
    .hero-content {
        width: 100%;
        text-align:center;
    }

    .hero-title {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .hero-desc {
        color: #5b6368;
        margin-bottom: 18px;
        font-size: 16px;
    }

    /* department vertical text on the card's right edge */
    .dept-vertical {
        position: absolute;
        right: -60px;
        top: 50%;
        transform: rotate(-90deg) translateY(-50%);
        transform-origin: center;
        font-weight: 600;
        color: #39424a;
        letter-spacing: 0.3px;
    }

    /* Get started button */
    .cta {
        display:inline-block;
        padding: 10px 18px;
        border-radius: 10px;
        border: 1px solid #cfd6db;
        text-decoration: none;
        font-weight:600;
        background:#ffffff;
        box-shadow: 0 2px 8px rgba(14,30,37,0.05);
    }
    .cta:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(14,30,37,0.08); }

    /* Right banner image styling */
    .banner-img {
        width: 100%;
        height: auto;
        border-radius:6px;
        object-fit:cover;
    }

    /* Small screen adjustments */
    @media (max-width: 900px) {
        .home-container { flex-direction: column; height:auto; }
        .banner-area { width:100%; order:-1; border-left:none; border-top:1px solid #e6e6e6; padding:18px; }
        .hero-card { width: auto; margin-top: 18px; }
        .dept-vertical { display:none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Layout ----------------
banner_url = st.secrets.get("BANNER_URL") if hasattr(st, "secrets") else None
uploaded_banner = st.session_state.get("uploaded_banner", None)

st.markdown('<div class="home-container">', unsafe_allow_html=True)

# Main content area (left)
st.markdown('<div class="main-area">', unsafe_allow_html=True)

# Hero card
st.markdown('<div class="hero-card">', unsafe_allow_html=True)
st.markdown('<div class="hero-content">', unsafe_allow_html=True)

# Title and description replicate the handwritten layout text from the PDF
st.markdown('<div class="hero-title">To use multilingual chatbot</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-desc">Click below to start</div>', unsafe_allow_html=True)

# CTA navigates to root (where your login is)
# Use an anchor to "/" - this works on Streamlit Cloud or local; it opens the main/root page.
st.markdown(
    f'<a href="/" class="cta">Get started →</a>',
    unsafe_allow_html=True,
)

st.markdown('</div>', unsafe_allow_html=True)  # close hero-content

# Department vertical label exactly placed like the sketch (right of the card)
st.markdown('<div class="dept-vertical">Department of CSE - AIML</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # close hero-card
st.markdown('</div>', unsafe_allow_html=True)  # close main-area


# Right banner area (vertical strip)
st.markdown('<div class="banner-area">', unsafe_allow_html=True)

# Display banner from secrets or uploaded file; if none, show placeholder and uploader
if banner_url:
    # use the URL from secrets (string)
    st.markdown(f'<img src="{banner_url}" class="banner-img" />', unsafe_allow_html=True)
elif uploaded_banner:
    # uploaded_banner is an UploadedFile object -> use st.image
    st.image(uploaded_banner, use_column_width=True)
else:
    # placeholder + uploader
    st.markdown(
        '<img src="https://via.placeholder.com/200x400.png?text=Banner" class="banner-img" />',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("Upload banner image (optional)", type=["png","jpg","jpeg","webp"])
    if uploaded is not None:
        st.session_state["uploaded_banner"] = uploaded
        st.experimental_rerun()

st.markdown('</div>', unsafe_allow_html=True)  # close banner-area
st.markdown('</div>', unsafe_allow_html=True)  # close home-container

# Small instruction (non-intrusive)
st.markdown(
    """
    <div style="text-align:center; margin-top:12px; color:#6b7280; font-size:13px;">
        Click <strong>Get started →</strong> to go to the login page.
    </div>
    """,
    unsafe_allow_html=True,
)
