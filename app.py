# app.py
import time
from datetime import datetime, timezone
import streamlit as st
from langdetect import detect
import google.generativeai as genai
import pandas as pd

# Firebase imports (optional)
import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="🌐 Multilingual Chatbot", page_icon="💬", layout="wide")

ADMIN_EMAILS = {"rlsurendra49@gmail.com"}
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """
You are a helpful multilingual conversational AI assistant.
Always reply in the same language as the user.
"""

# -------------------------
# GLOBAL THEME-AWARE CSS
# -------------------------
st.markdown(
    """
    <style>

    /* Detect light/dark theme using CSS variables */
    :root, [data-theme="light"] {
        --text-color: #222;
        --subtext-color: #444;
        --box-bg: rgba(0,0,0,0.05);
        --box-border: rgba(0,0,0,0.15);
    }

    [data-theme="dark"] {
        --text-color: #ffffff;
        --subtext-color: #cccccc;
        --box-bg: rgba(255,255,255,0.08);
        --box-border: rgba(255,255,255,0.18);
    }

    /* Top banner */
    .top-banner img {
        width:100%;
        height:300px;
        object-fit:cover;
        border-radius:14px;
        margin: 14px auto;
        display:block;
        max-width:1200px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.35);
    }

    /* Centered text */
    .dept-text {
        font-size:28px;
        font-weight:800;
        color: var(--text-color);
        margin-top: 18px;
        text-align:center;
    }

    .dept-underline {
        width:160px;
        height:5px;
        border-radius:10px;
        background: linear-gradient(90deg, #ffb347, #ff5f6d);
        margin: 8px auto 16px;
    }

    /* Info box */
    .info-box {
        max-width:760px;
        width:100%;
        margin: 10px auto 20px;
        padding: 16px 20px;
        text-align:center;
        font-size:18px;
        font-weight:600;
        background: var(--box-bg);
        border: 1px solid var(--box-border);
        border-radius:12px;
        backdrop-filter: blur(4px);
    }

    /* Center CTA */
    .cta-wrap {
        width:100%;
        display:flex;
        justify-content:center;
        margin-top: 20px;
        margin-bottom: 40px;
    }

    /* Main buttons */
    .stButton>button {
        border-radius: 10px !important;
        padding: 12px 26px !important;
        font-weight:700 !important;
        font-size:16px !important;
    }

    /* GOOGLE LOGIN BUTTON ICON */
    #login_with_google_btn button {
        position: relative;
        padding-left: 48px !important;
    }

    #login_with_google_btn button::before {
        content: "";
        background-image: url('https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg');
        background-size: 22px 22px;
        position: absolute;
        left: 14px;
        top: 50%;
        transform: translateY(-50%);
        width: 22px;
        height: 22px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# FIRESTORE initialization
# -------------------------
db = None
firebase_config = st.secrets.get("firebase")
if firebase_config:
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(dict(firebase_config))
            firebase_admin.initialize_app(cred)
        db = firestore.client()
    except:
        db = None

# -------------------------
# GEMINI init
# -------------------------
model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT
        )
    except:
        model = None

# -------------------------
# HELPERS
# -------------------------
def safe_detect_language(text: str):
    try:
        return detect(text)
    except:
        return "unknown"

def lang_label(code):
    labels = {
        "en":"English","hi":"Hindi","te":"Telugu","ta":"Tamil","kn":"Kannada",
        "ml":"Malayalam","mr":"Marathi","gu":"Gujarati","bn":"Bengali","ur":"Urdu"
    }
    return labels.get(code, code)

def ensure_user_doc(user):
    if db is None:
        return getattr(user, "email", None)

    uid = getattr(user, "email", None)
    users_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()

    doc = users_ref.get()
    if not doc.exists:
        users_ref.set({
            "uid": uid,
            "email": uid,
            "created_at": now,
            "last_login_at": now,
        })
    else:
        users_ref.update({"last_login_at": now})

    return uid

# -------------------------
# LOGIN PANEL (full-screen mode)
# -------------------------
def render_login_only():
    st.markdown('<div class="top-banner">', unsafe_allow_html=True)
    st.image("assets/banner.jpg", use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:center; margin-top:20px;">
            <h2 style="color:var(--text-color); font-weight:800;">Login to Continue</h2>
            <p style="color:var(--subtext-color); font-size:15px;">Use your Google account</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button(" Login with Google", key="login_with_google_btn", use_container_width=True):
            try:
                st.login("google")
            except:
                st.error("Google login works only on Streamlit Cloud.")

# -------------------------
# HOME PAGE
# -------------------------
def render_home():
    # Banner
    st.markdown('<div class="top-banner">', unsafe_allow_html=True)
    st.image("assets/banner.jpg", use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Centered layout
    left, mid, right = st.columns([1,2,1])

    with mid:
        st.markdown('<div class="dept-text">Department of CSE - AIML</div>', unsafe_allow_html=True)
        st.markdown('<div class="dept-underline"></div>', unsafe_allow_html=True)

        st.markdown(
            """
            <div class="info-box">
                Unlock seamless multilingual communication—start now!
            </div>
            """, unsafe_allow_html=True,
        )

        st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)

        clicked = st.button("Get Started →", key="get_started_center")

        st.markdown('</div>', unsafe_allow_html=True)

    if clicked:
        st.session_state.show_login = True
        st.rerun()

# -------------------------
# SESSION STATE
# -------------------------
if "show_login" not in st.session_state:
    st.session_state.show_login = False

# -------------------------
# MAIN FLOW
# -------------------------
user_logged_in = getattr(getattr(st, "user", None), "is_logged_in", False)

# SHOW LOGIN ONLY (no home content)
if st.session_state.show_login and not user_logged_in:
    render_login_only()
    st.stop()

# SHOW HOME PAGE
if not user_logged_in:
    render_home()
    st.stop()

# USER LOGGED IN → Continue
uid = ensure_user_doc(st.user)

# Sidebar
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Email: `{getattr(st.user,'email','')}`")

    if st.button("Logout"):
        try:
            st.logout()
        except:
            pass
        st.rerun()

# -------------------------
# CHATBOT UI
# -------------------------
st.title("🌐 Multilingual Chatbot")
st.caption("Type anything in any language. The bot replies in the same language. ✨")

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Type your message...")

if user_input:
    lang = safe_detect_language(user_input)
    st.session_state.messages.append({"role":"user", "content": user_input})

    with st.chat_message("assistant"):
        response = st.session_state.chat.send_message(user_input)
        bot = response.text
        st.write(bot)

    st.session_state.messages.append({"role":"assistant", "content": bot})
