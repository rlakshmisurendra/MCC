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
# GLOBAL CSS (HOME + GENERAL)
# -------------------------
st.markdown(
    """
    <style>

    /* ----------- TOP BANNER ----------- */
    .top-banner img {
        width: 100%;
        height: 300px;
        object-fit: cover;
        border-radius: 10px;
        box-shadow: 0px 8px 28px rgba(0,0,0,0.35);
        margin-top: 10px;
    }
    @media (max-width:900px){
        .top-banner img { height: 140px; }
    }

    /* ----------- HOME CENTER BLOCK ----------- */
    .home-center {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;      /* center horizontally */
    justify-content: center;  /* center vertically */
    margin-top: 40px;
    text-align: center;
    padding: 0 20px;
}

    .dept-text {
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        text-shadow: 0 2px 8px rgba(0,0,0,0.4);
        margin-top: 16px;
    }

    /* ----------- GRADIENT UNDERLINE ----------- */
    .dept-underline {
        width: 160px;
        height: 5px;
        margin: 12px auto 20px;
        background: linear-gradient(90deg, #ffb347, #ff5f6d);
        border-radius: 10px;
        box-shadow: 0 4px 10px rgba(255, 95, 109, 0.35);
    }

    /* ----------- INFO BOX ----------- */
    .info-box {
        max-width: 700px;
        margin: 20px auto 10px;
        padding: 14px 22px;
        text-align: center;
        font-size: 18px;
        font-weight: 600;
        color: #ffffff;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 14px;
        backdrop-filter: blur(6px);
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.28);
    }

    /* ----------- CENTER CTA ----------- */
    .cta-wrap {
        width: 100%;
        display: flex;
        justify-content: center;
        margin-top: 18px;
    }

    .stButton>button {
        border-radius: 10px !important;
        padding: 12px 22px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# FIRESTORE INITIALIZATION
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
# GEMINI MODEL INIT
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
# UTILITY FUNCTIONS
# -------------------------
def safe_detect_language(text: str):
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
        return getattr(user, "email", None) or getattr(user, "sub", None)

    uid = getattr(user, "sub", None) or getattr(user, "email", None)
    name = getattr(user, "name", "")
    email = getattr(user, "email", "")
    picture = getattr(user, "picture", "")

    users_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()

    if users_ref.get().exists:
        users_ref.update({
            "name": name, "email": email, "picture": picture,
            "last_login_at": now,
        })
    else:
        users_ref.set({
            "uid": uid, "name": name, "email": email, "picture": picture,
            "created_at": now, "last_login_at": now,
        })
    return uid

# -------------------------
# LOGIN PANEL
# -------------------------
def show_login_panel(autoscroll=True):
    google_logo_url = "https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style='text-align:center; margin-top:10px;'>
            <h3 style='font-size:20px; font-weight:700;'>Continue with Google</h3>
            <p style='color:#b7b7b7; font-size:13px;'>Sign in with your Google account to continue</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button(" Login with Google", key="login_btn", use_container_width=True):
            try:
                st.login("google")
            except:
                st.error("st.login unavailable outside Streamlit Cloud.")


# -------------------------
# SESSION STATE INIT
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
# RENDER HOME PAGE
# -------------------------
def render_home():
    st.markdown('<div class="top-banner">', unsafe_allow_html=True)
    st.image("assets/banner.jpg", use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- CENTERED BLOCK ----------
    st.markdown('<div class="home-center">', unsafe_allow_html=True)

    # Department text
    st.markdown(
        '<div class="dept-text">Department of CSE - AIML</div>',
        unsafe_allow_html=True
    )
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

    # Get started button
    st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
    clicked = st.button("Get Started →", key="home_get_started")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close home-center wrapper

    # Show login panel if clicked
    if clicked:
        st.session_state.show_login = True

    if st.session_state.show_login and not getattr(st.user, "is_logged_in", False):
        show_login_panel()


# -------------------------
# MAIN FLOW
# -------------------------
if not getattr(st.user, "is_logged_in", False):
    render_home()
    st.stop()

# Logged in:
uid = ensure_user_doc(st.user)
st.session_state.uid = uid

if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()

# Sidebar
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Name: `{st.user.name}`")
    st.write(f"Email: `{st.user.email}`")
    st.write(f"UID: `{uid}`")

    if st.button("🚪 Logout"):
        try:
            st.logout()
        except:
            st.error("st.logout unavailable in local mode.")
        st.experimental_rerun()

# Chat UI
st.title("🌐 Multilingual Chatbot")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Type your message...")

if user_input:
    lang = safe_detect_language(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "lang": lang})

    with st.chat_message("assistant"):
        if st.session_state.chat:
            response = st.session_state.chat.send_message(user_input)
            bot_reply = response.text
        else:
            bot_reply = "Model not configured."
        st.markdown(bot_reply)

    st.session_state.messages.append({"role": "assistant", "content": bot_reply})

