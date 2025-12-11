# app.py
import time
from datetime import datetime, timezone
import streamlit as st
from langdetect import detect
import google.generativeai as genai
import pandas as pd

import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Multilingual Chatbot", page_icon="💬", layout="wide")

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
# STYLE (matches design.pdf look)
# -------------------------
st.markdown(
    """
    <style>
    .home-container { display:flex; gap:0; width:100%; min-height:70vh; box-sizing:border-box; padding:28px; }
    .main-area { flex: 1 1 auto; display:flex; align-items:center; justify-content:center; }
    .banner-area { width: 260px; background: #f7f7f7; display:flex; align-items:center; justify-content:center; padding: 18px; box-sizing:border-box; border-left: 1px solid #e6e6e6; }
    .hero-card { width: 760px; max-width: calc(100% - 60px); border-radius: 14px; padding: 36px 28px; box-sizing: border-box; box-shadow: 0 8px 30px rgba(14,30,37,0.06); background: linear-gradient(180deg, #fff, #fbfbfb); position: relative; display:flex; align-items:center; justify-content:center; }
    .hero-content { width:100%; text-align:center; }
    .hero-title { font-size: 22px; font-weight: 700; margin-bottom: 8px; }
    .hero-desc { color: #5b6368; margin-bottom: 18px; font-size: 16px; }
    .dept-vertical { position: absolute; right: -72px; top: 50%; transform: rotate(-90deg) translateY(-50%); transform-origin: center; font-weight: 600; color: #39424a; letter-spacing: 0.3px; }
    .cta { display:inline-block; padding: 10px 18px; border-radius: 10px; border: 1px solid #cfd6db; text-decoration: none; font-weight:600; background:#ffffff; box-shadow: 0 2px 8px rgba(14,30,37,0.05); }
    .cta:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(14,30,37,0.08); }
    .banner-img { width: 100%; height: auto; border-radius:6px; object-fit:cover; }
    @media (max-width: 900px) {
        .home-container { flex-direction: column; padding:18px; }
        .banner-area { width:100%; order:-1; border-left:none; border-top:1px solid #e6e6e6; padding:18px; }
        .dept-vertical { display:none; }
    }
    /* small button style for streamlit buttons */
    .stButton>button { border-radius: 10px; padding: .45rem 1rem; font-weight:600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# INIT FIRESTORE (optional)
# -------------------------
if not firebase_admin._apps:
    firebase_config = dict(st.secrets.get("firebase", {})) if st.secrets.get("firebase") else {}
    if firebase_config:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)

db = firestore.client() if firebase_admin._apps else None

# -------------------------
# INIT GEMINI (optional)
# -------------------------
model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_PROMPT)

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
        "en":"English","hi":"Hindi","te":"Telugu","ta":"Tamil","kn":"Kannada","ml":"Malayalam",
        "mr":"Marathi","gu":"Gujarati","bn":"Bengali","ur":"Urdu"
    }
    return mapping.get(lang_code, lang_code)

def ensure_user_doc(user):
    if db is None:
        return None
    uid = getattr(user, "sub", None) or getattr(user, "email", None)
    if not uid:
        raise ValueError("Could not determine UID from st.user")
    name = getattr(user, "name", "")
    email = getattr(user, "email", "")
    picture = getattr(user, "picture", "")
    users_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()
    doc = users_ref.get()
    if doc.exists:
        users_ref.update({"name": name, "email": email, "picture": picture, "last_login_at": now})
    else:
        users_ref.set({"uid": uid, "name": name, "email": email, "picture": picture, "created_at": now, "last_login_at": now})
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

def render_admin_dashboard():
    st.title("📊 Admin Dashboard")
    st.markdown("Overview of registered users and their recent usage.")
    if db is None:
        st.warning("Firestore not initialized; admin dashboard is disabled.")
        return
    user_docs = list(db.collection("users").stream())
    users = []
    for doc in user_docs:
        d = doc.to_dict()
        users.append({"uid": doc.id, "name": d.get("name", ""), "email": d.get("email", ""), "created_at": d.get("created_at", ""), "last_login_at": d.get("last_login_at", "")})
    usage_docs = list(db.collection("usage").stream())
    usage_map = {doc.id: doc.to_dict() for doc in usage_docs}
    for u in users:
        u_usage = usage_map.get(u["uid"], {})
        u["last_session_seconds"] = u_usage.get("last_session_seconds", 0)
        u["last_session_messages"] = u_usage.get("last_session_messages", 0)
        u["usage_last_updated"] = u_usage.get("last_updated", "")
    if not users:
        st.info("No users found yet.")
        return
    df = pd.DataFrame(users)
    total_users = len(df)
    total_messages = int(df["last_session_messages"].sum())
    total_time_sec = int(df["last_session_seconds"].sum())
    total_time_min = total_time_sec // 60
    c1, c2, c3 = st.columns(3)
    c1.metric("Total users", total_users)
    c2.metric("Total messages (last sessions)", total_messages)
    c3.metric("Total time (min, last sessions)", total_time_min)
    st.markdown("### Users & usage (last session)")
    st.dataframe(df, use_container_width=True)

# -------------------------
# SESSION STATE
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

if "uid" not in st.session_state:
    st.session_state.uid = None

# -------------------------
# HOME (default view for not-logged-in users)
# -------------------------
def render_home():
    banner_url = st.secrets.get("BANNER_URL") if hasattr(st, "secrets") else None
    uploaded_banner = st.session_state.get("uploaded_banner", None)

    st.markdown('<div class="home-container">', unsafe_allow_html=True)

    # main hero
    st.markdown('<div class="main-area">', unsafe_allow_html=True)
    st.markdown('<div class="hero-card">', unsafe_allow_html=True)
    st.markdown('<div class="hero-content">', unsafe_allow_html=True)

    st.markdown('<div class="hero-title">To use multilingual chatbot</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-desc">Click below to start</div>', unsafe_allow_html=True)

    # Get started toggles the login UI on the same page (no redirect)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Get started →", key="get_started"):
            st.session_state.show_login = True
            st.experimental_rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # hero-content
    st.markdown('<div class="dept-vertical">Department of CSE - AIML</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # hero-card
    st.markdown('</div>', unsafe_allow_html=True)  # main-area

    # right banner
    st.markdown('<div class="banner-area">', unsafe_allow_html=True)
    if banner_url:
        st.markdown(f'<img src="{banner_url}" class="banner-img" />', unsafe_allow_html=True)
    elif uploaded_banner:
        st.image(uploaded_banner, use_column_width=True)
    else:
        st.markdown('<img src="https://via.placeholder.com/220x420.png?text=Banner" class="banner-img" />', unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload banner image (optional)", type=["png","jpg","jpeg","webp"])
        if uploaded is not None:
            st.session_state.uploaded_banner = uploaded
            st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)  # banner-area

    st.markdown('</div>', unsafe_allow_html=True)  # home-container

    # If the user clicked Get started, reveal the login UI right below the hero
    if st.session_state.show_login:
        show_login_panel()

# -------------------------
# LOGIN PANEL (revealed after clicking Get started)
# -------------------------
def show_login_panel():
    google_logo_url = "https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style='text-align:center; margin-top:6px;'>
            <h3 style='font-size:20px; font-weight:600; margin-bottom:6px;'>Continue with Google</h3>
            <p style='color:#6b7280; font-size:13px; margin-bottom:8px;'>Sign in with your Google account to continue</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(" Login with Google", use_container_width=True, key="login_btn"):
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
                background-image:url('{google_logo_url}');
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

# -------------------------
# MAIN APP FLOW
# -------------------------
# If not logged in -> show home (which may reveal login)
if not st.user.is_logged_in:
    render_home()
    st.stop()  # wait until user logs in

# Logged in -> continue to chat/admin
uid = ensure_user_doc(st.user)
st.session_state.uid = uid

user_email = getattr(st.user, "email", "")

# start session timer
if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()
    st.session_state.total_user_messages = 0

# Sidebar
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Name: `{getattr(st.user, 'name', 'N/A')}`")
    st.write(f"Email: `{getattr(st.user, 'email', 'N/A')}`")
    st.write(f"UID: `{uid}`")

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
        if st.session_state.session_start_ts is not None and st.session_state.uid:
            update_usage_stats(st.session_state.uid, st.session_state.session_start_ts, st.session_state.total_user_messages)
        st.logout()
        st.stop()

# Admin navigation
page = "Chatbot"
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

# Initialize chat in session if missing
if "chat" not in st.session_state or st.session_state.chat is None:
    st.session_state.chat = None if model is None else model.start_chat(history=[])

for msg in st.session_state.messages:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        if msg.get("lang") and msg["role"] == "user":
            st.markdown(f"*Detected language:* `{lang_label(msg['lang'])}`")
        st.markdown(msg["content"])

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
                bot_reply = "Model not configured (GEMINI_API_KEY missing)."
                st.error(bot_reply)
            else:
                response = st.session_state.chat.send_message(user_input)
                bot_reply = response.text
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply, "lang": lang})

            if st.session_state.session_start_ts is not None and st.session_state.uid:
                update_usage_stats(st.session_state.uid, st.session_state.session_start_ts, st.session_state.total_user_messages)

        except Exception as e:
            err = f"⚠ Error: {e}"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err, "lang": None})
