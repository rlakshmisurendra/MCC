import time
from datetime import datetime, timezone
import json

import streamlit as st
from langdetect import detect
import google.generativeai as genai
import pandas as pd

import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------------------------
# CONFIG
# -------------------------------------------

st.set_page_config(
    page_title="Multilingual Chatbot",
    page_icon="💬",
    layout="centered"
)

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

# -------------------------------------------
# STYLE (Same buttons & theme across app)
# -------------------------------------------
st.markdown("""
<style>
.stButton > button {
    background-color: #ffffff;
    color: #3c4043;
    border-radius: 20px;
    border: 1px solid #dadce0;
    padding: 0.45rem 1.2rem;
    font-weight: 500;
    font-size: 0.95rem;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    box-shadow: 0 1px 2px rgba(60,64,67,.3);
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------
# Initialize Firebase
# -------------------------------------------

if not firebase_admin._apps:
    firebase_config = dict(st.secrets.get("firebase", {}))
    if firebase_config:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)

db = firestore.client() if firebase_admin._apps else None

# -------------------------------------------
# Initialize Gemini
# -------------------------------------------

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
    )
else:
    st.error("❗ Missing GEMINI_API_KEY in secrets.toml")
    st.stop()

# -------------------------------------------
# Helper functions
# -------------------------------------------

def safe_detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"


def lang_label(code: str) -> str:
    mapping = {
        "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil",
        "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "gu": "Gujarati",
        "bn": "Bengali", "ur": "Urdu"
    }
    return mapping.get(code, code)


def ensure_user_doc(user):
    if db is None:
        return None

    uid = getattr(user, "sub", None) or getattr(user, "email", None)
    if not uid:
        raise ValueError("Could not determine UID")

    name = getattr(user, "name", "")
    email = getattr(user, "email", "")
    picture = getattr(user, "picture", "")

    doc_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()

    if doc_ref.get().exists:
        doc_ref.update({
            "name": name,
            "email": email,
            "picture": picture,
            "last_login_at": now
        })
    else:
        doc_ref.set({
            "uid": uid,
            "name": name,
            "email": email,
            "picture": picture,
            "created_at": now,
            "last_login_at": now
        })

    return uid


def update_usage(uid, start_ts, msg_count):
    if db is None:
        return
    usage_ref = db.collection("usage").document(uid)
    session_seconds = int(time.time() - start_ts)

    usage_ref.set({
        "last_session_seconds": session_seconds,
        "last_session_messages": msg_count,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }, merge=True)


def render_admin():
    st.title("📊 Admin Dashboard")
    if db is None:
        st.error("Firestore not configured")
        return

    users = [doc.to_dict() | {"uid": doc.id} for doc in db.collection("users").stream()]
    usage = {doc.id: doc.to_dict() for doc in db.collection("usage").stream()}

    for u in users:
        u.update(usage.get(u["uid"], {}))

    df = pd.DataFrame(users)
    st.dataframe(df, use_container_width=True)

# -------------------------------------------
# Session State
# -------------------------------------------

if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_start_ts" not in st.session_state:
    st.session_state.session_start_ts = None

if "uid" not in st.session_state:
    st.session_state.uid = None

if "total_msgs" not in st.session_state:
    st.session_state.total_msgs = 0

chat = st.session_state.chat

# -------------------------------------------
# LOGIN PAGE (Root page = app.py)
# -------------------------------------------

st.title("🌐 Multilingual Chatbot")
st.caption("Secure Login → then Chat")

# User not logged in → show Google Login button
if not st.user.is_logged_in:

    google_logo = "https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"

    st.markdown(
        f"""
        <div style='text-align:center; margin-top:40px;'>
            <h2>Please Login</h2>
            <p>Continue with Google</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(" Login with Google", use_container_width=True):
        st.login("google")

    st.markdown(
        f"""
        <style>
        .stButton button {{
            position: relative;
            padding-left:45px !important;
        }}
        .stButton button::before {{
            content: "";
            background-image:url('{google_logo}');
            background-size:20px 20px;
            position:absolute;
            left:15px;
            top:50%;
            transform:translateY(-50%);
            width:20px;
            height:20px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.stop()

# -------------------------------------------
# If Logged in → Load user
# -------------------------------------------

uid = ensure_user_doc(st.user)
st.session_state.uid = uid

# Start timer
if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()
    st.session_state.total_msgs = 0

user_email = getattr(st.user, "email", "")

# Admin Navigation
page = "Chatbot"
if user_email in ADMIN_EMAILS:
    with st.sidebar:
        st.write("Navigation")
        page = st.radio("", ["Chatbot", "Admin Dashboard"])

# -------------------------------------------
# SIDEBAR (User Info)
# -------------------------------------------

with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Name: {st.user.name}")
    st.write(f"Email: {st.user.email}")
    st.write(f"UID: {uid}")

    elapsed = int(time.time() - st.session_state.session_start_ts)
    st.write(f"Session time: {elapsed//60}m {elapsed%60}s")
    st.write(f"Messages: {st.session_state.total_msgs}")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.session_state.chat = model.start_chat(history=[])
        st.session_state.total_msgs = 0

    if st.button("🚪 Logout"):
        update_usage(uid, st.session_state.session_start_ts, st.session_state.total_msgs)
        st.logout()
        st.stop()

# -------------------------------------------
# PAGE ROUTING
# -------------------------------------------

if page == "Admin Dashboard":
    render_admin()
    st.stop()

# -------------------------------------------
# CHAT UI
# -------------------------------------------

st.header("💬 Start Chatting")

# Show history
for msg in st.session_state.messages:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        if msg["role"] == "user" and msg.get("lang"):
            st.markdown(f"*Detected:* `{lang_label(msg['lang'])}`")
        st.markdown(msg["content"])

# Input
user_input = st.chat_input("Type your message...")

if user_input:
    lang = safe_detect_language(user_input)

    # Save message
    st.session_state.messages.append({"role": "user", "content": user_input, "lang": lang})
    st.session_state.total_msgs += 1

    # Display user bubble
    with st.chat_message("user"):
        st.markdown(f"*Detected:* `{lang_label(lang)}`")
        st.markdown(user_input)

    # Get bot reply
    with st.chat_message("assistant"):
        try:
            response = chat.send_message(user_input)
            reply = response.text
        except Exception as e:
            reply = f"⚠ Error: {e}"

        st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply, "lang": lang})

        update_usage(uid, st.session_state.session_start_ts, st.session_state.total_msgs)
