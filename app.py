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

Rules:
1. Detect the user's language.
2. Always reply in the SAME language used by the user.
3. Be clear, concise and friendly.
4. If user mixes languages, reply in the dominant language.
"""

# -------------------------
# THEME-AWARE GLOBAL CSS
# -------------------------
st.markdown(
    """
    <style>

    :root {
        --txt: var(--text-color);
        --bg: var(--background-color);
        --bg2: var(--secondary-background-color);
        --primary: var(--primary-color);
        --txt2: var(--secondary-text-color);
    }

    /* Banner */
    .top-banner img {
        width:100%;
        height:260px;
        object-fit:cover;
        border-radius:12px;
        margin: 18px auto;
        display:block;
        max-width:1200px;
        box-shadow: 0 6px 28px rgba(0,0,0,0.10);
    }
    @media (max-width:900px){
        .top-banner img { height:140px; }
    }

    /* Heading */
    .dept-text {
        font-size:28px;
        font-weight:800;
        color: var(--txt);
        text-align:center;
        margin-top:20px;
    }

    /* Underline */
    .dept-underline {
        width:180px;
        height:6px;
        border-radius:10px;
        background: linear-gradient(90deg, #ffb347, #ff5f6d);
        margin: 10px auto 25px;
        box-shadow: 0 0 16px rgba(255,95,109,0.22);
    }

    /* Info box */
    .info-box {
        max-width:700px;
        width:100%;
        margin: 12px auto;
        padding: 18px 22px;
        font-size:18px;
        font-weight:600;
        text-align:center;
        background: var(--bg2);
        color: var(--txt);
        border: 1px solid rgba(120,120,120,0.12);
        border-radius:12px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    }

    /* CTA wrapper */
    .cta-wrap {
        width:100%;
        display:flex;
        justify-content:center;
        margin-top:22px;
        margin-bottom:34px;
    }

    /* Buttons theme-aware */
    .stButton > button {
        background: var(--primary) !important;
        color: var(--txt) !important;
        border-radius: 10px !important;
        padding: 12px 30px !important;
        font-weight: 700 !important;
        border: none !important;
        transition: .2s;
    }
    .stButton > button:hover {
        opacity: 0.96;
        transform: translateY(-2px);
    }

    /* Login panel */
    .login-panel { text-align:center; margin-top:18px; }
    .login-title { font-size:22px; font-weight:700; color: var(--txt); }
    .login-sub { font-size:14px; color: var(--txt2); }

    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# FIRESTORE INIT
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
# GEMINI INIT
# -------------------------
model = None
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_PROMPT)
except:
    model = None

# -------------------------
# HELPERS
# -------------------------
def safe_detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

def lang_label(lang):
    mapping = {
        "en":"English","hi":"Hindi","te":"Telugu","ta":"Tamil","kn":"Kannada",
        "ml":"Malayalam","mr":"Marathi","gu":"Gujarati","bn":"Bengali","ur":"Urdu"
    }
    return mapping.get(lang, lang)

def ensure_user_doc(user):
    if db is None:
        return getattr(user, "email", None)

    uid = getattr(user, "sub", None) or getattr(user, "email", None)
    data = {
        "name": getattr(user, "name", ""),
        "email": getattr(user, "email", ""),
        "picture": getattr(user, "picture", ""),
        "last_login_at": datetime.now(timezone.utc).isoformat(),
    }
    users_ref = db.collection("users").document(uid)
    if users_ref.get().exists:
        users_ref.update(data)
    else:
        data["created_at"] = data["last_login_at"]
        users_ref.set(data)
    return uid

def update_usage_stats(uid, start_ts, msg_count):
    if db is None:
        return
    usage_ref = db.collection("usage").document(uid)
    usage_ref.set({
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "last_session_seconds": int(time.time() - start_ts),
        "last_session_messages": msg_count,
    }, merge=True)

# -------------------------
# LOGIN SCREEN (banner + google)
# -------------------------
def render_login_only():
    left, mid, right = st.columns([1,2,1])
    with mid:
        st.markdown('<div class="top-banner">', unsafe_allow_html=True)
        st.image("assets/banner.jpg", use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="login-panel">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Continue with Google</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Sign in with your Google account to continue</div>', unsafe_allow_html=True)

        if st.button(" Login with Google", use_container_width=True):
            try:
                st.login("google")
            except:
                st.error("Google login only works on Streamlit Cloud.")
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# FULL HOME SCREEN
# -------------------------
def render_full_home():
    left, mid, right = st.columns([1,2,1])
    with mid:
        st.markdown('<div class="top-banner">', unsafe_allow_html=True)
        st.image("assets/banner.jpg", use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="dept-text">Department of CSE - AIML</div>', unsafe_allow_html=True)
        st.markdown('<div class="dept-underline"></div>', unsafe_allow_html=True)

        st.markdown(
            """
            <div class="info-box">
                Unlock seamless multilingual communication—start now!
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
        clicked = st.button("Get Started →")
        st.markdown('</div>', unsafe_allow_html=True)

        if clicked:
            st.session_state.show_login = True
            st.rerun()

# -------------------------
# SESSION STATE
# -------------------------
if "show_login" not in st.session_state:
    st.session_state.show_login = False
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[]) if model else None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_start_ts" not in st.session_state:
    st.session_state.session_start_ts = None
if "total_user_messages" not in st.session_state:
    st.session_state.total_user_messages = 0

# -------------------------
# MAIN FLOW CONTROL
# -------------------------
user_logged_in = getattr(getattr(st, "user", None), "is_logged_in", False)

# If user clicked Get Started but not logged in → show login view
if st.session_state.show_login and not user_logged_in:
    render_login_only()
    st.stop()

# If not logged in → show home
if not user_logged_in:
    render_full_home()
    st.stop()

# -------------------------
# LOGGED-IN FLOW
# -------------------------
uid = ensure_user_doc(st.user)
st.session_state.uid = uid

if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()

# Sidebar user details
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Name: `{st.user.name}`")
    st.write(f"Email: `{st.user.email}`")
    st.write(f"UID: `{uid}`")

    elapsed = int(time.time() - st.session_state.session_start_ts)
    st.write(f"Session time: {elapsed//60} min {elapsed%60} sec")
    st.write(f"Messages: {st.session_state.total_user_messages}")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.session_state.chat = model.start_chat(history=[]) if model else None
        st.session_state.total_user_messages = 0
        st.rerun()

    if st.button("🚪 Logout"):
        update_usage_stats(uid, st.session_state.session_start_ts, st.session_state.total_user_messages)
        st.logout()
        st.rerun()

# Admin navigation
page = "Chatbot"
if st.user.email in ADMIN_EMAILS:
    with st.sidebar:
        page = st.radio("Navigation", ["Chatbot", "Admin dashboard"])

if page == "Admin dashboard":
    st.title("📊 Admin Dashboard")
    st.write("Admin panel will be implemented here.")
    st.stop()

# -------------------------
# CHAT UI
# -------------------------
st.title("🌐 Multilingual Chatbot")
st.caption("Type anything in any language. I will reply in the same language ✨")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Type here…")

if user_input:
    lang = safe_detect_language(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "lang": lang})
    st.session_state.total_user_messages += 1

    with st.chat_message("user"):
        st.markdown(f"*Detected language:* `{lang_label(lang)}`")
        st.markdown(user_input)

    with st.chat_message("assistant"):
        reply = st.session_state.chat.send_message(user_input).text
        st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply, "lang": lang})

    st.rerun()
