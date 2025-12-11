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
# GLOBAL CSS (theme-aware + centered)
# -------------------------
st.markdown(
    """
    <style>
    /* Use Streamlit theme variables where possible so colors adapt to light/dark themes */
    :root {
      --app-text: var(--text-color, #111827);
      --app-secondary-bg: var(--secondary-background-color, rgba(0,0,0,0.05));
      --app-border: rgba(0,0,0,0.06);
    }

    /* Top banner: placed in middle column to guarantee centering */
    .top-banner img {
        width:100%;
        height:300px;
        object-fit:cover;
        border-radius:10px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.10);
        margin: 14px auto;
        display:block;
        max-width:1200px;
    }
    @media (max-width:900px){
        .top-banner img { height:140px; }
    }

    /* Department title (inherits theme text color) */
    .dept-text {
        font-size:26px;
        font-weight:800;
        color: var(--app-text);
        margin-top: 18px;
        margin-bottom: 6px;
        text-align:center;
    }

    /* Gradient underline (visual accent) */
    .dept-underline {
        width:160px;
        height:6px;
        border-radius:10px;
        background: linear-gradient(90deg, #ffb347, #ff5f6d);
        box-shadow: 0 6px 18px rgba(255,95,109,0.12);
        margin: 12px auto 18px;
    }

    /* Info box: uses secondary background so it adapts to light/dark */
    .info-box {
        max-width:760px;
        width:100%;
        margin: 12px auto;
        padding: 16px 20px;
        text-align:center;
        font-size:18px;
        font-weight:600;
        color: var(--app-text);
        background: var(--app-secondary-bg);
        border: 1px solid var(--app-border);
        border-radius:12px;
        backdrop-filter: blur(4px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.06);
    }

    /* CTA wrapper (when inside middle column it will be centered) */
    .cta-wrap {
        width:100%;
        display:flex;
        justify-content:center;
        margin-top: 20px;
        margin-bottom: 30px;
    }

    /* Make Streamlit default button look nice and theme-friendly */
    .stButton>button {
        border-radius: 10px !important;
        padding: 12px 26px !important;
        font-weight:700 !important;
        font-size:16px !important;
        color: var(--text-color) !important;
        background: var(--primary-color) !important;
        border: 1px solid rgba(0,0,0,0.08) !important;
    }

    /* Login panel adjustments */
    .login-panel { max-width:720px; margin: 20px auto; text-align:center; }
    .login-title { font-size:20px; font-weight:700; margin-bottom:6px; color: var(--app-text); }
    .login-sub { color: var(--secondary-text-color, #6b7280); margin-bottom:12px; }

    /* Ensure central column content has no left offset */
    .stApp > div[data-testid="stHorizontalBlock"] {
        /* no-op; kept as placeholder if needed */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# FIRESTORE initialization (optional)
# -------------------------
db = None
firebase_config = st.secrets.get("firebase")
if firebase_config:
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(dict(firebase_config))
            firebase_admin.initialize_app(cred)
        db = firestore.client()
    except Exception as e:
        st.warning(f"Firestore init failed: {e}")
        db = None

# -------------------------
# GEMINI init (defensive)
# -------------------------
model = None
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_PROMPT)
except Exception as e:
    st.warning(f"Generative model init warning: {e}")
    model = None

# -------------------------
# HELPERS
# -------------------------
def safe_detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

def lang_label(lang_code: str) -> str:
    mapping = {
        "en":"English","hi":"Hindi","te":"Telugu","ta":"Tamil","kn":"Kannada",
        "ml":"Malayalam","mr":"Marathi","gu":"Gujarati","bn":"Bengali","ur":"Urdu"
    }
    return mapping.get(lang_code, lang_code)

def ensure_user_doc(user):
    if db is None:
        return getattr(user, "email", None) or getattr(user, "sub", None)
    uid = getattr(user, "sub", None) or getattr(user, "email", None)
    name = getattr(user, "name", "")
    email = getattr(user, "email", "")
    picture = getattr(user, "picture", "")
    users_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()
    doc = users_ref.get()
    if doc.exists:
        users_ref.update({
            "name": name,
            "email": email,
            "picture": picture,
            "last_login_at": now,
        })
    else:
        users_ref.set({
            "uid": uid,
            "name": name,
            "email": email,
            "picture": picture,
            "created_at": now,
            "last_login_at": now,
        })
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

# -------------------------
# LOGIN-ONLY VIEW (banner + centered login)
# -------------------------
def render_login_only():
    # Banner in middle column for perfect centering & consistent max width
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="top-banner">', unsafe_allow_html=True)
        try:
            st.image("assets/banner.jpg", use_column_width=True)
        except Exception:
            st.image("https://via.placeholder.com/1200x300.png?text=Banner", use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="login-panel">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Continue with Google</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Sign in with your Google account to continue</div>', unsafe_allow_html=True)

        if st.button(" Login with Google", key="login_btn_center", use_container_width=True):
            try:
                st.login("google")
            except Exception:
                st.error("st.login not available in this runtime. Deploy on Streamlit Cloud to use Google OIDC.")

        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# FULL HOME (banner + dept + info + CTA) - centered
# -------------------------
def render_full_home():
    # Use columns to guarantee central alignment
    left, mid, right = st.columns([1, 2, 1])
    with mid:
        # Banner
        st.markdown('<div class="top-banner">', unsafe_allow_html=True)
        try:
            st.image("assets/banner.jpg", use_column_width=True)
        except Exception:
            st.image("https://via.placeholder.com/1200x300.png?text=Banner", use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Department title / underline
        st.markdown('<div class="dept-text">Department of CSE - AIML</div>', unsafe_allow_html=True)
        st.markdown('<div class="dept-underline"></div>', unsafe_allow_html=True)

        # Info box
        st.markdown(
            """
            <div class="info-box">
                Unlock seamless multilingual communication—start now!
            </div>
            """,
            unsafe_allow_html=True
        )

        # CTA
        st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
        if st.button("Get Started →", key="home_get_started_center"):
            st.session_state.show_login = True
            try:
                st.experimental_rerun()
            except Exception:
                pass
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# SESSION STATE initialization
# -------------------------
if "show_login" not in st.session_state:
    st.session_state.show_login = False
if "chat" not in st.session_state:
    st.session_state.chat = None if model is None else model.start_chat(history=[])
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_start_ts" not in st.session_state:
    st.session_state.session_start_ts = None
if "total_user_messages" not in st.session_state:
    st.session_state.total_user_messages = 0

# -------------------------
# MAIN FLOW
# -------------------------
user_logged_in = getattr(getattr(st, "user", None), "is_logged_in", False)

# If user clicked Get Started and isn't logged in -> show login-only view
if st.session_state.get("show_login", False) and not user_logged_in:
    render_login_only()
    st.stop()

# If not logged in show full home
if not user_logged_in:
    render_full_home()
    st.stop()

# Logged in: standard app
uid = ensure_user_doc(st.user)
st.session_state.uid = uid
if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()

# Sidebar
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Name: `{getattr(st.user, 'name', 'N/A')}`")
    st.write(f"Email: `{getattr(st.user, 'email', 'N/A')}`")
    st.write(f"UID: `{uid}`")
    if st.session_state.session_start_ts is not None:
        elapsed = int(time.time() - st.session_state.session_start_ts)
        mins = elapsed // 60
        secs = elapsed % 60
        st.write(f"Session time: **{mins} min {secs} sec**")
        st.write(f"Messages sent: **{st.session_state.total_user_messages}**")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.session_state.chat = None if model is None else model.start_chat(history=[])
        st.session_state.total_user_messages = 0
        st.success("Chat history cleared!")

    if st.button("🚪 Logout"):
        if st.session_state.session_start_ts is not None and getattr(st, "user", None):
            update_usage_stats(uid, st.session_state.session_start_ts, st.session_state.total_user_messages)
        try:
            st.logout()
        except Exception:
            st.warning("st.logout not available in this runtime.")
        try:
            st.experimental_rerun()
        except Exception:
            pass

# Admin routing
page = "Chatbot"
user_email = getattr(st.user, "email", "")
if user_email in ADMIN_EMAILS:
    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio("Go to", ["Chatbot", "Admin dashboard"])

if page == "Admin dashboard":
    render_admin_dashboard()
    st.stop()

# Chat UI
st.title("🌐 Multilingual Chatbot")
st.caption("Type anything in any language. The bot will reply in the same language. ✨")

if st.session_state.chat is None and model is not None:
    st.session_state.chat = model.start_chat(history=[])

for msg in st.session_state.messages:
    role = msg.get("role", "user")
    with st.chat_message(role):
        st.markdown(msg.get("content", ""))

user_input = st.chat_input("Type your message here...")

if user_input:
    lang = safe_detect_language(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "lang": lang})
    st.session_state.total_user_messages += 1

    with st.chat_message("user"):
        st.markdown(f"*Detected language:* `{lang_label(lang)}`")
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            if st.session_state.chat is None:
                bot_reply = "Model not configured (GEMINI_API_KEY missing or model init failed)."
                st.error(bot_reply)
            else:
                with st.spinner("Thinking..."):
                    response = st.session_state.chat.send_message(user_input)
                    bot_reply = response.text
                st.markdown(bot_reply)

            st.session_state.messages.append({"role": "assistant", "content": bot_reply, "lang": lang})

            if st.session_state.session_start_ts is not None and getattr(st, "user", None):
                update_usage_stats(uid, st.session_state.session_start_ts, st.session_state.total_user_messages)

        except Exception as e:
            err = f"⚠ Error: {e}"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err, "lang": None})
