import time
from datetime import datetime, timezone
import json

import streamlit as st
from langdetect import detect
import google.generativeai as genai
import pandas as pd

import firebase_admin
from firebase_admin import credentials, firestore

# Put your admin e-mail(s) here
ADMIN_EMAILS = {
    "rlsurendra49@gmail.com",
}

# ================== BASIC CONFIG ==================

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

st.set_page_config(
    page_title="🌐 Multilingual Chatbot",
    page_icon="💬",
    layout="centered",
)

st.markdown("""
<style>
/* Google-like button styling for ALL st.button by default */
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

/* Home hero styles */
.home-hero {
    text-align: center;
    padding: 36px 12px;
}
.hero-title {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 8px;
}
.hero-sub {
    color: #6b7280;
    margin-bottom: 18px;
}
.hero-card {
    border-radius: 12px;
    padding: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fbfbfb 100%);
    box-shadow: 0 6px 20px rgba(14,30,37,0.06);
    max-width: 880px;
    margin: 0 auto 24px;
}
.banner-image {
    border-radius: 10px;
    max-width: 100%;
    height: auto;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ------------- Home page before login --------------
def show_home_page():
    st.markdown("<div class='home-hero'>", unsafe_allow_html=True)
    st.markdown("<div class='hero-card'>", unsafe_allow_html=True)

    # Banner: priority order
    # 1) st.secrets['BANNER_URL']
    # 2) session_state uploaded image
    banner_url = st.secrets.get("BANNER_URL")
    uploaded_banner = st.session_state.get("uploaded_banner", None)

    if banner_url:
        st.image(banner_url, use_column_width=True, caption="")
    elif uploaded_banner:
        st.image(uploaded_banner, use_column_width=True, caption="")
    else:
        # show placeholder and allow upload
        st.image(
            "https://via.placeholder.com/1200x350.png?text=Your+Banner+Here+%28set+BANNER_URL+in+secrets%29",
            use_column_width=True,
        )
        st.write("You can set `st.secrets['BANNER_URL']` to display your design banner here or upload below.")

    st.markdown("<h1 class='hero-title'>🌐 Multilingual Chatbot</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-sub'>Type anything in any language. The bot will reply in the same language. ✨</p>", unsafe_allow_html=True)

    # small feature list (style it to match the PDF vibes)
    st.markdown("""
    - Detects language automatically (Hindi, Telugu, Tamil, Kannada, Malayalam, Marathi, Gujarati, Bengali, Urdu and more)
    - Replies in the same language as the user
    - Google OIDC sign-in for secure access
    """)
    st.markdown("---")

    # Upload banner file fallback if secrets not provided
    if not banner_url:
        uploaded = st.file_uploader("Upload banner image (optional) — will display above", type=["png","jpg","jpeg","webp"])
        if uploaded is not None:
            # store bytes in session state so on rerun it's available
            st.session_state.uploaded_banner = uploaded
            st.experimental_rerun()

    # Get started button -> show login flow when clicked
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Get started →", key="get_started_btn"):
            # flip a flag so we render the login box below on same session
            st.session_state.show_login = True
            st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================== INIT FIRESTORE ==================

if not firebase_admin._apps:
    # st.secrets["firebase"] is a TOML table → behaves like a dict
    firebase_config = dict(st.secrets.get("firebase", {}))
    if firebase_config:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    else:
        # If firebase credentials are missing we still allow the app to start
        # but show a warning (you can adjust as needed)
        st.warning("Firebase credentials not set in st.secrets['firebase'] — Firestore features will be disabled.")

db = firestore.client() if firebase_admin._apps else None

# ================== INIT GEMINI ==================

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
    )
else:
    model = None

# ================== HELPERS ==================

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
    """
    if db is None:
        return None

    # Google OIDC usually has "sub" as unique subject ID
    uid = (
        getattr(user, "sub", None)
        or getattr(user, "email", None)  # fallback
    )

    if not uid:
        st.write("DEBUG st.user:", user.to_dict())
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


def render_admin_dashboard():
    """Show a simple admin dashboard with users + usage stats."""
    st.title("📊 Admin Dashboard")

    st.markdown("Overview of registered users and their recent usage.")

    if db is None:
        st.warning("Firestore not initialized; admin dashboard is disabled.")
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
    total_messages = int(df["last_session_messages"].sum())
    total_time_sec = int(df["last_session_seconds"].sum())
    total_time_min = total_time_sec // 60

    c1, c2, c3 = st.columns(3)
    c1.metric("Total users", total_users)
    c2.metric("Total messages (last sessions)", total_messages)
    c3.metric("Total time (min, last sessions)", total_time_min)

    st.markdown("### Users & usage (last session)")
    st.dataframe(df, use_container_width=True)


# ================== SESSION STATE ==================

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

if "show_login" not in st.session_state:
    st.session_state.show_login = False

chat = st.session_state.chat

# ================== AUTH WITH OIDC GOOGLE ==================

# If user not logged in -> show home page first
if not st.user.is_logged_in:
    show_home_page()

    # if user clicked Get started, show the login panel beneath the hero
    if st.session_state.show_login:
        google_logo_url = "https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"

        st.markdown(
            """
            <div style='text-align:center; margin-top:18px;'>
                <h3 style='font-size:22px; font-weight:600; margin-bottom:4px;'>Continue with Google</h3>
                <p style='color:#6b7280; font-size:13px; margin-bottom:12px;'>Sign in with your Google account to continue</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # clicking this redirects to the OIDC provider
            if st.button(
                label=" Login with Google",
                use_container_width=True,
                help="Sign in using your Google account",
                key="login_with_google_btn",
            ):
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
                """, unsafe_allow_html=True
            )

        # stop here for unauthenticated users
        st.stop()
    else:
        # user hasn't clicked get started -> stop (they're on homepage)
        st.stop()

# If logged in, we have st.user filled
uid = ensure_user_doc(st.user)
st.session_state.uid = uid

user_email = getattr(st.user, "email", "")

# Default page
page = "Chatbot"

# If current user is admin, allow switching to dashboard
if user_email in ADMIN_EMAILS:
    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio("Go to", ["Chatbot", "Admin dashboard"])
else:
    page = "Chatbot"

# Start session timer if first time this session
if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()
    st.session_state.total_user_messages = 0

# ================== SIDEBAR ==================

with st.sidebar:
    if page == "Chatbot":
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
            if st.session_state.session_start_ts is not None and st.session_state.uid:
                update_usage_stats(
                    st.session_state.uid,
                    st.session_state.session_start_ts,
                    st.session_state.total_user_messages,
                )
            st.logout()
            st.stop()

# ================== MAIN AREA: ROUTING ==================
if page == "Admin dashboard":
    render_admin_dashboard()
else:
    # ---- original chatbot UI ----
    st.title("🌐 Multilingual Chatbot")
    st.caption("Type anything in any language. The bot will reply in the same language. ✨")

    for msg in st.session_state.messages:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            if msg.get("lang") and msg["role"] == "user":
                st.markdown(f"*Detected language:* `{lang_label(msg['lang'])}`")
            st.markdown(msg["content"])

    user_input = st.chat_input("Type your message here...")

    if user_input:
        lang = safe_detect_language(user_input)

        st.session_state.messages.append(
            {"role": "user", "content": user_input, "lang": lang}
        )
        st.session_state.total_user_messages += 1

        with st.chat_message("user"):
            st.markdown(f"*Detected language:* `{lang_label(lang)}`")
            st.markdown(user_input)

        with st.chat_message("assistant"):
            try:
                if chat is None:
                    st.error("Model not configured (GEMINI_API_KEY missing).")
                    bot_reply = "Model not configured. Please set GEMINI_API_KEY in st.secrets."
                else:
                    response = chat.send_message(user_input)
                    bot_reply = response.text
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
