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
st.set_page_config(page_title="🌐 Multilingual Chatbot", page_icon="💬", layout="centered")

ADMIN_EMAILS = {"rlsurendra49@gmail.com"}
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """
You are a helpful multilingual conversational AI assistant.
Always reply in the same language as the user.
"""

# -------------------------
# THEME-AWARE CSS + Google icon for login button
# -------------------------
st.markdown(
    """
    <style>
    /* --------------------------------------------------
       Theme-aware variables (works with prefers-color-scheme
       and Streamlit's [data-theme] attribute)
       -------------------------------------------------- */
    :root {
        --text-on-dark: #ffffff;
        --muted-on-dark: rgba(255,255,255,0.78);
        --info-bg-dark: rgba(255,255,255,0.06);
        --info-border-dark: rgba(255,255,255,0.12);

        --text-on-light: #0f1724;
        --muted-on-light: rgba(15,23,36,0.75);
        --info-bg-light: rgba(15,23,36,0.04);
        --info-border-light: rgba(15,23,36,0.08);

        --underline-gradient: linear-gradient(90deg, #ffb347, #ff5f6d);
    }

    /* prefer light theme */
    @media (prefers-color-scheme: light) {
        :root {
            --text-color: var(--text-on-light);
            --muted-color: var(--muted-on-light);
            --info-bg: var(--info-bg-light);
            --info-border: var(--info-border-light);
        }
    }
    /* prefer dark theme */
    @media (prefers-color-scheme: dark) {
        :root {
            --text-color: var(--text-on-dark);
            --muted-color: var(--muted-on-dark);
            --info-bg: var(--info-bg-dark);
            --info-border: var(--info-border-dark);
        }
    }

    /* Also support Streamlit theme attribute if present */
    :root[data-theme="light"], [data-theme="light"] {
        --text-color: var(--text-on-light);
        --muted-color: var(--muted-on-light);
        --info-bg: var(--info-bg-light);
        --info-border: var(--info-border-light);
    }
    :root[data-theme="dark"], [data-theme="dark"] {
        --text-color: var(--text-on-dark);
        --muted-color: var(--muted-on-dark);
        --info-bg: var(--info-bg-dark);
        --info-border: var(--info-border-dark);
    }

    /* ---------------- Top banner ---------------- */
    .top-banner img {
        width:100%;
        max-width:1100px;
        height:260px;
        object-fit:cover;
        display:block;
        margin: 12px auto;
        border-radius: 12px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.18);
    }
    @media (max-width:900px) {
        .top-banner img { height:140px; }
    }

    /* ------------- Department heading ------------- */
    .dept-text {
        font-size:28px;
        font-weight:800;
        color: var(--text-color);
        margin-top: 18px;
        text-align:center;
    }

    .dept-underline {
        width:160px;
        height:6px;
        border-radius:10px;
        background: var(--underline-gradient);
        margin: 8px auto 16px;
        box-shadow: 0 6px 18px rgba(255,95,109,0.12);
    }

    /* ---------------- Info box ---------------- */
    .info-box {
        max-width:760px;
        width:100%;
        margin: 10px auto 20px;
        padding: 16px 20px;
        text-align:center;
        font-size:18px;
        font-weight:600;
        color: var(--text-color);
        background: var(--info-bg);
        border: 1px solid var(--info-border);
        border-radius:12px;
        backdrop-filter: blur(4px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.08);
    }

    /* ---------------- CTA ---------------- */
    .cta-wrap {
        width:100%;
        display:flex;
        justify-content:center;
        margin-top: 20px;
        margin-bottom: 40px;
    }

    .stButton>button {
        border-radius: 10px !important;
        padding: 12px 26px !important;
        font-weight:700 !important;
        font-size:16px !important;
    }

    /* ---------------- Google icon only for the login button ----------------
       We target the Streamlit widget wrapper by key: Streamlit sets the
       outer div id to the widget key for classic behavior; this has worked
       in prior Streamlit versions. We keep the selector specific so other
       buttons are not affected.
    --------------------------------------------------------------------- */
    /* Container ID = login_with_google_btn (same as the button key) */
    #login_with_google_btn button {
        position: relative;
        padding-left: 52px !important;
    }
    #login_with_google_btn button::before {
        content: "";
        background-image: url('https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg');
        background-repeat: no-repeat;
        background-size: 22px 22px;
        position: absolute;
        left: 16px;
        top: 50%;
        transform: translateY(-50%);
        width: 22px;
        height: 22px;
        border-radius: 3px;
    }

    /* Fallback: if the button wrapper id isn't present, try a specific label match (less reliable) */
    button[title="Login with Google"]::before,
    button[aria-label="Login with Google"]::before {
        content: "";
        background-image: url('https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg');
        background-repeat: no-repeat;
        background-size: 22px 22px;
        position: absolute;
        left: 16px;
        top: 50%;
        transform: translateY(-50%);
        width: 22px;
        height: 22px;
        border-radius: 3px;
    }
    /* Custom Google login button */
.google-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    background: white;
    color: #3c4043;
    padding: 12px 22px;
    border-radius: 10px;
    border: 1px solid #dadce0;
    font-weight: 600;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    width: 100%;
    max-width: 340px;
    margin: 0 auto;
}

.google-btn:hover {
    box-shadow: 0 1px 2px rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15);
    transform: translateY(-1px);
}

.google-icon {
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
    except Exception:
        db = None

# -------------------------
# GEMINI init
# -------------------------
model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_PROMPT)
    except Exception:
        model = None

# -------------------------
# HELPERS
# -------------------------
def safe_detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

def lang_label(code: str) -> str:
    labels = {
        "en":"English","hi":"Hindi","te":"Telugu","ta":"Tamil","kn":"Kannada",
        "ml":"Malayalam","mr":"Marathi","gu":"Gujarati","bn":"Bengali","ur":"Urdu"
    }
    return labels.get(code, code)

def ensure_user_doc(user):
    if db is None:
        return getattr(user, "email", None)
    uid = getattr(user, "email", None) or getattr(user, "sub", None)
    users_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()
    doc = users_ref.get()
    if not doc.exists:
        users_ref.set({"uid": uid, "email": uid, "created_at": now, "last_login_at": now})
    else:
        users_ref.update({"last_login_at": now})
    return uid

def update_usage_stats(uid: str, session_start_ts: float, total_messages: int):
    if db is None:
        return
    usage_ref = db.collection("usage").document(uid)
    now_ts = time.time()
    session_seconds = int(now_ts - session_start_ts)
    usage_ref.set({
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "last_session_seconds": session_seconds,
        "last_session_messages": total_messages,
    }, merge=True)

# safe rerun helper (works in different Streamlit versions)
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        try:
            st.rerun()
        except Exception:
            pass

# -------------------------
# LOGIN PANEL
# -------------------------
def render_login_only():
    # Banner
    st.markdown('<div class="top-banner">', unsafe_allow_html=True)
    try:
        st.image("assets/banner.jpg", use_column_width=True)
    except Exception:
        st.image("https://via.placeholder.com/1100x260.png?text=Banner", use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:center; margin-top:20px;">
            <h2 style="font-weight:800; color:var(--text-color);">Login to Continue</h2>
            <p style="color:var(--muted-color); font-size:15px;">Use your Google account</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Layout: small icon column + large button column centered
    # We use a middle column to center the content, and inside it two nested columns.
    col1, mid_col, col3 = st.columns([1, 2, 1])
    with mid_col:
        c_icon, c_btn = st.columns([0.08, 0.92])
        # show the icon in the small left column (visually appears inside the button area)
        with c_icon:
            st.image("https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg", width=28)
        # the actual Streamlit button is here (this is the real login trigger)
        with c_btn:
            if st.button(" Login with Google", key="login_with_google_btn", use_container_width=True):
                try:
                    st.login("google")
                except Exception:
                    st.error("st.login not available in this runtime. Deploy on Streamlit Cloud to use Google OIDC.")


# -------------------------
# HOME PAGE
# -------------------------
def render_home():
    st.markdown('<div class="top-banner">', unsafe_allow_html=True)
    try:
        st.image("assets/banner.jpg", use_column_width=True)
    except Exception:
        st.image("https://via.placeholder.com/1100x260.png?text=Banner", use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # use columns to guarantee centering
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="dept-text">Department of CSE - AIML</div>', unsafe_allow_html=True)
        st.markdown('<div class="dept-underline"></div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="info-box">Unlock seamless multilingual communication—start now!</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
        clicked = st.button("Get Started →", key="get_started")
        st.markdown('</div>', unsafe_allow_html=True)

    if clicked:
        st.session_state.show_login = True
        safe_rerun()

# -------------------------
# SESSION STATE
# -------------------------
if "show_login" not in st.session_state:
    st.session_state.show_login = False

# -------------------------
# MAIN FLOW
# -------------------------
user_logged_in = getattr(getattr(st, "user", None), "is_logged_in", False)

# If user requested login panel / clicked get started
if st.session_state.get("show_login", False) and not user_logged_in:
    render_login_only()
    st.stop()

# Show home page for not-logged-in users
if not user_logged_in:
    render_home()
    st.stop()

# Logged-in flow
uid = ensure_user_doc(st.user)
st.session_state.uid = uid

# Sidebar
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Email: `{getattr(st.user,'email','')}`")
    if st.button("Logout"):
        try:
            st.logout()
        except Exception:
            pass
        safe_rerun()

# Chat UI
st.title("🌐 Multilingual Chatbot")
st.caption("Type anything in any language. The bot replies in the same language. ✨")

if "chat" not in st.session_state:
    try:
        st.session_state.chat = model.start_chat(history=[]) if model else None
    except Exception:
        st.session_state.chat = None

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    role = msg.get("role", "user")
    with st.chat_message(role):
        st.markdown(msg.get("content", ""))

user_input = st.chat_input("Type your message...")

if user_input:
    lang = safe_detect_language(user_input)
    st.session_state.messages.append({"role":"user", "content": user_input, "lang": lang})
    st.session_state.total_user_messages = st.session_state.get("total_user_messages", 0) + 1

    with st.chat_message("assistant"):
        if st.session_state.chat:
            try:
                response = st.session_state.chat.send_message(user_input)
                bot = response.text
            except Exception as e:
                bot = f"⚠ Model error: {e}"
        else:
            bot = "Model not configured (GEMINI_API_KEY missing or model init failed)."
        st.markdown(bot)

    st.session_state.messages.append({"role":"assistant", "content": bot, "lang": lang})

    if st.session_state.get("session_start_ts") and st.session_state.get("uid"):
        update_usage_stats(st.session_state.uid, st.session_state.session_start_ts, st.session_state.total_user_messages)
