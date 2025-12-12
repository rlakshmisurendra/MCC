# app.py
import time
from datetime import datetime, timezone
import json

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

# Put your admin e-mails here
ADMIN_EMAILS = {"rlsurendra49@gmail.com"}

# Use st.secrets safely to avoid KeyError locally
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
# CSS (merge of both styles used previously)
# -------------------------
st.markdown("""
<style>
/* --- Google-like button styling for ALL st.button (from original) --- */
.stButton > button {
    background-color: #ffffff;
    color: #3c4043;
    border-radius: 20px;
    border: 1px solid #dadce0;
    padding: 0.45rem 1.2rem;
    font-weight: 500;
    font-size: 0.95rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    transition: all 0.15s ease-in-out;
}
.stButton > button:hover {
    box-shadow: 0 1px 2px rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15);
    transform: translateY(-1px);
}
/* Round avatar fallback */
.avatar-circle {
    width: 40px;
    height: 40px;
    border-radius: 999px;
    background: linear-gradient(135deg, #4285F4, #DB4437, #F4B400, #0F9D58);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 20px;
    font-weight: 600;
}
/* Small pill for name + email */
.profile-pill {
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    border: 1px solid #dadce0;
    background-color: #fafafa;
    font-size: 0.8rem;
}

/* --- Theme aware UI (from refined layout) --- */
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
@media (prefers-color-scheme: light) {
    :root {
        --text-color: var(--text-on-light);
        --muted-color: var(--muted-on-light);
        --info-bg: var(--info-bg-light);
        --info-border: var(--info-border-light);
    }
}
@media (prefers-color-scheme: dark) {
    :root {
        --text-color: var(--text-on-dark);
        --muted-color: var(--muted-on-dark);
        --info-bg: var(--info-bg-dark);
        --info-border: var(--info-border-dark);
    }
}
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

/* Top banner */
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

/* Department heading */
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

/* Info box */
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

/* CTA */
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

/* Google login button icon */
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
.google-icon { width: 22px; height: 22px; }
</style>
""", unsafe_allow_html=True)

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

def lang_label(lang_code: str) -> str:
    mapping = {
        "en": "English",
        "hi": "Hindi",
        "te": "Telugu",
        "ta": "Tamil",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "gu": "Gujarati",
        "bn": "Bengali",
        "ur": "Urdu",
    }
    if lang_code in mapping:
        return f"{mapping[lang_code]} ({lang_code})"
    if lang_code == "unknown":
        return "Unknown"
    return lang_code

def ensure_user_doc(user):
    """
    Store user details in Firestore on first login or update on later logins.
    If Firestore not configured, return an identifying fallback (email or sub).
    """
    if db is None:
        return getattr(user, "email", None) or getattr(user, "sub", None)

    # Google OIDC usually has "sub" as unique subject ID
    uid = (
        getattr(user, "sub", None)
        or getattr(user, "email", None)  # fallback
    )

    if not uid:
        # Helpful debug if something is unexpectedly shaped
        try:
            st.write("DEBUG st.user:", user.to_dict())
        except Exception:
            st.write("DEBUG st.user (no to_dict available)")
        raise ValueError("Could not determine UID from st.user")

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
    """Store usage stats: session time + message count."""
    if db is None:
        return

    usage_ref = db.collection("usage").document(uid)

    now_ts = time.time()
    session_seconds = int(now_ts - session_start_ts)

    usage_ref.set(
        {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "last_session_seconds": session_seconds,
            "last_session_messages": total_messages,
        },
        merge=True,
    )

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
# ADMIN DASHBOARD
# -------------------------
def render_admin_dashboard():
    """Show a simple admin dashboard with users + usage stats."""
    st.title("📊 Admin Dashboard")
    st.markdown("Overview of registered users and their recent usage.")

    if db is None:
        st.info("Firestore not configured — no user data available.")
        return

    # Fetch all users
    user_docs = list(db.collection("users").stream())
    users = []
    for doc in user_docs:
        d = doc.to_dict()
        users.append({
            "uid": doc.id,
            "name": d.get("name", ""),
            "email": d.get("email", ""),
            "created_at": d.get("created_at", ""),
            "last_login_at": d.get("last_login_at", ""),
        })

    # Fetch usage
    usage_docs = list(db.collection("usage").stream())
    usage_map = {doc.id: doc.to_dict() for doc in usage_docs}

    # Merge usage into users
    for u in users:
        u_usage = usage_map.get(u["uid"], {})
        u["last_session_seconds"] = u_usage.get("last_session_seconds", 0)
        u["last_session_messages"] = u_usage.get("last_session_messages", 0)
        u["usage_last_updated"] = u_usage.get("last_updated", "")

    if not users:
        st.info("No users found yet.")
        return

    df = pd.DataFrame(users)

    # High-level stats
    total_users = len(df)
    total_messages = int(df["last_session_messages"].sum()) if "last_session_messages" in df else 0
    total_time_sec = int(df["last_session_seconds"].sum()) if "last_session_seconds" in df else 0
    total_time_min = total_time_sec // 60

    c1, c2, c3 = st.columns(3)
    c1.metric("Total users", total_users)
    c2.metric("Total messages (last sessions)", total_messages)
    c3.metric("Total time (min, last sessions)", total_time_min)

    st.markdown("### Users & usage (last session)")
    st.dataframe(df, use_container_width=True)

    # Optional: export CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Export CSV", data=csv, file_name="users_usage.csv", mime="text/csv")

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

    col1, mid_col, col3 = st.columns([1, 2, 1])
    with mid_col:
        c_icon, c_btn = st.columns([0.08, 0.92])
        with c_icon:
            st.image("https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg", width=28)
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
# SESSION STATE defaults
# -------------------------
if "show_login" not in st.session_state:
    st.session_state.show_login = False

if "session_start_ts" not in st.session_state:
    st.session_state.session_start_ts = None

if "total_user_messages" not in st.session_state:
    st.session_state.total_user_messages = 0

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
user_email = getattr(st.user, "email", "")

# Start session timer if first time this session
if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()
    st.session_state.total_user_messages = 0

# Sidebar
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Name: `{getattr(st.user, 'name', 'N/A')}`")
    st.write(f"Email: `{user_email or 'N/A'}`")
    st.write(f"UID: `{uid}`")

    if st.session_state.session_start_ts is not None:
        elapsed = int(time.time() - st.session_state.session_start_ts)
        mins = elapsed // 60
        secs = elapsed % 60
        st.write(f"Session time: **{mins} min {secs} sec**")
        st.write(f"Messages sent: **{st.session_state.total_user_messages}**")

    if user_email in ADMIN_EMAILS:
        st.markdown("### Navigation")
        page = st.radio("Go to", ["Chatbot", "Admin dashboard"])
    else:
        page = "Chatbot"

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        try:
            st.session_state.chat = model.start_chat(history=[]) if model else None
        except Exception:
            st.session_state.chat = None
        st.session_state.total_user_messages = 0
        st.success("Chat history cleared!")

    if st.button("🚪 Logout"):
        if st.session_state.session_start_ts is not None and st.session_state.uid:
            update_usage_stats(
                st.session_state.uid,
                st.session_state.session_start_ts,
                st.session_state.total_user_messages,
            )
        try:
            st.logout()
        except Exception:
            pass
        safe_rerun()

# Route pages
if user_email in ADMIN_EMAILS and page == "Admin dashboard":
    render_admin_dashboard()
    st.stop()

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
        if msg.get("lang") and role == "user":
            st.markdown(f"*Detected language:* `{lang_label(msg['lang'])}`")
        st.markdown(msg.get("content", ""))

user_input = st.chat_input("Type your message here...")

if user_input:
    lang = safe_detect_language(user_input)

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "lang": lang}
    )
    st.session_state.total_user_messages = st.session_state.get("total_user_messages", 0) + 1

    with st.chat_message("user"):
        st.markdown(f"*Detected language:* `{lang_label(lang)}`")
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            if st.session_state.chat:
                response = st.session_state.chat.send_message(user_input)
                bot_reply = response.text
            else:
                bot_reply = "Model not configured (GEMINI_API_KEY missing or model init failed)."
            st.markdown(bot_reply)

            st.session_state.messages.append(
                {"role": "assistant", "content": bot_reply, "lang": lang}
            )

            if st.session_state.session_start_ts is not None and st.session_state.uid:
                update_usage_stats(
                    st.session_state.uid,
                    st.session_state.session_start_ts,
                    st.session_state.total_user_messages,
                )

        except Exception as e:
            err = f"⚠ Error: {e}"
            st.error(err)
            st.session_state.messages.append(
                {"role": "assistant", "content": err, "lang": None}
            )
