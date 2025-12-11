# app.py
import time
from datetime import datetime, timezone
import streamlit as st
from langdetect import detect
import google.generativeai as genai
import pandas as pd

# optional firebase
import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="🌐 Multilingual Chatbot",
                   page_icon="💬",
                   layout="wide",
                   initial_sidebar_state="auto")

ADMIN_EMAILS = {"rlsurendra49@gmail.com"}
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """
You are a helpful multilingual conversational AI assistant.
Always reply in the same language as the user.
"""

# -------------------------
# THEME-AWARE CSS + ANIMATIONS + GLASS UI + NAV + FOOTER
# -------------------------
st.markdown(
    """
    <style>
    :root {
      --txt: var(--text-color);
      --subtxt: var(--secondary-text-color);
      --bg: var(--background-color);
      --bg2: var(--secondary-background-color);
      --primary: var(--primary-color);
    }

    /* Page animations */
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(18px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* NAV BAR (glass) */
    .top-nav {
        position: sticky;
        top: 8px;
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: space-between;
        max-width: 1200px;
        margin: 8px auto;
        padding: 10px 18px;
        border-radius: 12px;
        background: rgba(255,255,255,0.06);
        backdrop-filter: blur(6px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
        animation: fadeInUp 0.5s ease both;
    }

    /* College logo */
    .nav-left { display:flex; align-items:center; gap:12px; }
    .college-logo { width:48px; height:48px; border-radius:8px; object-fit:cover; }

    /* Nav links */
    .nav-links { display:flex; gap:12px; align-items:center; }
    .nav-link {
        padding:8px 14px;
        border-radius:10px;
        font-weight:700;
        cursor:pointer;
        color: var(--txt);
        text-decoration:none;
    }
    .nav-link.active {
        background: linear-gradient(90deg, rgba(255,179,71,0.12), rgba(255,95,109,0.08));
        box-shadow: 0 6px 18px rgba(255,95,109,0.06);
    }

    /* Top hero/banner */
    .hero {
        max-width:1200px;
        margin: 18px auto 6px;
        animation: fadeInUp 0.6s ease both;
    }
    .hero img {
        width:100%;
        max-height:340px;
        object-fit:cover;
        border-radius:14px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.08);
    }

    /* Center container (middle column used too) */
    .center-block { text-align:center; margin-top:14px; animation: fadeInUp 0.6s ease 0.12s both; }

    .dept-text {
        font-size:28px;
        font-weight:800;
        color: var(--txt);
        margin-top: 18px;
    }
    .dept-underline {
        width:160px;
        height:6px;
        border-radius:10px;
        background: linear-gradient(90deg,#ffb347,#ff5f6d);
        margin: 10px auto 16px;
        box-shadow: 0 8px 24px rgba(255,95,109,0.12);
    }

    /* GLASS INFO BOX */
    .info-box {
        max-width:760px;
        margin:12px auto;
        padding:18px 22px;
        font-size:18px;
        font-weight:600;
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
        color: var(--txt);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius:12px;
        backdrop-filter: blur(6px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.06);
    }

    /* CTA */
    .cta-wrap { display:flex; justify-content:center; margin-top:18px; margin-bottom:34px; }
    .stButton>button { border-radius: 10px !important; padding:12px 26px !important; font-weight:700 !important; font-size:16px !important; transition: transform .12s ease, box-shadow .12s ease; }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,0,0,0.12); }

    /* Google login icon for login-only view */
    #login_with_google_btn button { position: relative; padding-left:48px !important; }
    #login_with_google_btn button::before {
        content: "";
        background-image: url('https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg');
        background-size:22px 22px;
        position:absolute;
        left:14px;
        top:50%;
        transform:translateY(-50%);
        width:22px;height:22px;
    }

    /* Footer */
    .app-footer {
        margin-top:40px;
        padding:18px 10px;
        text-align:center;
        color: var(--subtxt);
        font-size:14px;
    }
    .app-footer a { color: var(--txt); text-decoration:none; font-weight:600; }

    /* Small responsive tweaks */
    @media (max-width:880px) {
        .dept-text { font-size:22px; }
        .hero img { max-height:180px; border-radius:10px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# FIRESTORE init (optional)
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
# GEMINI init (defensive)
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
def safe_detect_language(text):
    try:
        return detect(text)
    except Exception:
        return "unknown"

def lang_label(code):
    mapping = {
        "en":"English","hi":"Hindi","te":"Telugu","ta":"Tamil","kn":"Kannada",
        "ml":"Malayalam","mr":"Marathi","gu":"Gujarati","bn":"Bengali","ur":"Urdu"
    }
    return mapping.get(code, code)

def ensure_user_doc(user):
    if db is None:
        return getattr(user, "email", None)
    uid = getattr(user, "email", None)
    users_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()
    doc = users_ref.get()
    if doc.exists:
        users_ref.update({"last_login_at": now})
    else:
        users_ref.set({"uid": uid, "email": uid, "created_at": now, "last_login_at": now})
    return uid

def update_usage_stats(uid, start_ts, count):
    if db is None:
        return
    usage_ref = db.collection("usage").document(uid)
    usage_ref.set({
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "last_session_seconds": int(time.time() - start_ts),
        "last_session_messages": count,
    }, merge=True)

# -------------------------
# RENDERING HELPERS
# -------------------------
def render_navbar(current_page="Home"):
    # navbar uses columns for layout; shows college logo and links as buttons
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        # logo left
        try:
            st.image("assets/college_logo.png", width=52, output_format="auto")
        except Exception:
            # fallback small placeholder
            st.markdown("<div style='width:52px;height:52px;border-radius:8px;background:#ddd'></div>", unsafe_allow_html=True)
    with col2:
        # horizontal nav (we implement as inline buttons that set state)
        nav_cols = st.columns([1,1,1,4])
        with nav_cols[0]:
            if st.button("Home", key="nav_home"):
                st.session_state.page = "Home"
                st.rerun()
        with nav_cols[1]:
            if st.button("Chatbot", key="nav_chat"):
                st.session_state.page = "Chatbot"
                st.rerun()
        with nav_cols[2]:
            # show Admin only if user email in ADMIN_EMAILS and logged in
            if getattr(getattr(st, "user", None), "is_logged_in", False) and getattr(st.user, "email", "") in ADMIN_EMAILS:
                if st.button("Admin", key="nav_admin"):
                    st.session_state.page = "Admin"
                    st.rerun()
        # filler to push items left
    with col3:
        # blank/right side (could place theme toggle etc.)
        st.write("")

def render_hero_banner():
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    try:
        st.image("assets/banner.jpg", use_column_width=True)
    except Exception:
        st.image("https://via.placeholder.com/1200x340.png?text=Banner", use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_home_page():
    render_hero_banner()
    # centered content in middle column
    left, mid, right = st.columns([1,2,1])
    with mid:
        st.markdown('<div class="center-block">', unsafe_allow_html=True)
        st.markdown('<div class="dept-text">Department of CSE - AIML</div>', unsafe_allow_html=True)
        st.markdown('<div class="dept-underline"></div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Unlock seamless multilingual communication—start now!</div>', unsafe_allow_html=True)
        st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
        clicked = st.button("Get Started →", key="get_started")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    if clicked:
        st.session_state.show_login = True
        st.rerun()

def render_login_only():
    # Show only banner + center login panel
    left, mid, right = st.columns([1,2,1])
    with mid:
        st.markdown('<div class="hero">', unsafe_allow_html=True)
        try:
            st.image("assets/banner.jpg", use_column_width=True)
        except Exception:
            st.image("https://via.placeholder.com/1200x340.png?text=Banner', 'use_column_width=True")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-panel">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Continue with Google</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Sign in with your Google account to continue</div>', unsafe_allow_html=True)
        # Google-login button with icon
        if st.button(" Login with Google", key="login_with_google_btn", use_container_width=True):
            try:
                st.login("google")
            except Exception:
                st.error("st.login only works on Streamlit Cloud.")
        st.markdown('</div>', unsafe_allow_html=True)
        # back button to return to full landing (useful)
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        if st.button("Back to Home", key="back_to_home"):
            st.session_state.show_login = False
            st.rerun()

def render_admin_dashboard():
    st.title("📊 Admin Dashboard")
    st.markdown("Overview of users (requires Firestore configured).")
    if db is None:
        st.warning("Firestore not configured; admin dashboard disabled.")
        return
    # fetch users (simple)
    docs = list(db.collection("users").stream())
    rows = []
    for d in docs:
        data = d.to_dict()
        rows.append({
            "uid": d.id,
            "name": data.get("name",""),
            "email": data.get("email",""),
            "created_at": data.get("created_at",""),
            "last_login_at": data.get("last_login_at","")
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("No users found.")

# -------------------------
# SESSION STATE init
# -------------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"
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
# RENDER PAGE (NAV + CONTENT)
# -------------------------
render_navbar(current_page=st.session_state.page)

# If user clicked Get Started -> show login-only view (no other home content)
user_logged_in = getattr(getattr(st, "user", None), "is_logged_in", False)
if st.session_state.show_login and not user_logged_in:
    render_login_only()
    # footer
    st.markdown('<div class="app-footer">Built for Final Year Project • Department of CSE - AIML</div>', unsafe_allow_html=True)
    st.stop()

# If page routing set to Home show full home
if st.session_state.page == "Home" and not user_logged_in:
    render_home_page()
    st.markdown('<div class="app-footer">Built for Final Year Project • Department of CSE - AIML</div>', unsafe_allow_html=True)
    st.stop()

# If page is Admin and logged-in & admin -> show admin
if st.session_state.page == "Admin":
    if user_logged_in and getattr(st.user, "email", "") in ADMIN_EMAILS:
        render_admin_dashboard()
    else:
        st.error("Admin access restricted.")
    st.markdown('<div class="app-footer">Built for Final Year Project • Department of CSE - AIML</div>', unsafe_allow_html=True)
    st.stop()

# Else show Chatbot (user must be logged in)
if not user_logged_in:
    # default fallback: show home if not logged in
    render_home_page()
    st.markdown('<div class="app-footer">Built for Final Year Project • Department of CSE - AIML</div>', unsafe_allow_html=True)
    st.stop()

# -------------------------
# USER LOGGED IN: ensure user doc + sidebar + chat
# -------------------------
uid = ensure_user_doc(st.user)
st.session_state.uid = uid
if st.session_state.session_start_ts is None:
    st.session_state.session_start_ts = time.time()

# Sidebar user info + actions
with st.sidebar:
    st.subheader("👤 User")
    st.write(f"Name: `{getattr(st.user,'name','N/A')}`")
    st.write(f"Email: `{getattr(st.user,'email','N/A')}`")
    st.write(f"UID: `{uid}`")

    elapsed = int(time.time() - st.session_state.session_start_ts)
    st.write(f"Session time: {elapsed//60} min {elapsed%60} sec")
    st.write(f"Messages: {st.session_state.total_user_messages}")

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.session_state.chat = None if model is None else model.start_chat(history=[])
        st.session_state.total_user_messages = 0
        st.experimental_rerun()

    if st.button("🚪 Logout"):
        # update stats then logout
        update_usage_stats(uid, st.session_state.session_start_ts, st.session_state.total_user_messages)
        try:
            st.logout()
        except Exception:
            pass
        st.experimental_rerun()

# Admin quick nav in sidebar if admin
if getattr(st.user, "email", "") in ADMIN_EMAILS:
    st.sidebar.markdown("---")
    if st.sidebar.button("Go to Admin"):
        st.session_state.page = "Admin"
        st.experimental_rerun()

# -------------------------
# CHAT UI (logged-in)
# -------------------------
st.title("🌐 Multilingual Chatbot")
st.caption("Type anything in any language. The bot will reply in the same language. ✨")

if st.session_state.chat is None and model is not None:
    st.session_state.chat = model.start_chat(history=[])

# show history
for msg in st.session_state.messages:
    role = msg.get("role", "user")
    with st.chat_message(role):
        st.markdown(msg.get("content", ""))

# input
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
                st.error("Model not configured (GEMINI_API_KEY missing).")
                bot_reply = "Model not configured."
            else:
                with st.spinner("Thinking..."):
                    resp = st.session_state.chat.send_message(user_input)
                    bot_reply = resp.text
                st.markdown(bot_reply)
        except Exception as e:
            bot_reply = f"⚠ Error: {e}"
            st.error(bot_reply)

    st.session_state.messages.append({"role": "assistant", "content": bot_reply, "lang": lang})
    # optionally persist stats
    if st.session_state.session_start_ts is not None and uid:
        update_usage_stats(uid, st.session_state.session_start_ts, st.session_state.total_user_messages)

# footer
st.markdown('<div class="app-footer">Built for Final Year Project • Department of CSE - AIML • <a href="#">Contact</a></div>', unsafe_allow_html=True)
